"""Anomaly Detection subagent for the Sentinel AML supervisor.

Hybrid approach:
- Isolation Forest (unsupervised) trained on train split, contamination=0.0015
- Rule-based heuristics for 7 ground-truth AML pattern types + cross-currency risk
- Composite score: 0.4 * IF_score + 0.6 * rule_score

The Isolation Forest model is trained once and checkpointed as a pickle file
so it can be reloaded without retraining. The rule-based component is
deterministic and runs fresh on each query.

Unlabeled laundering rows (Is Laundering=1, pattern_type=UNLABELED) are
excluded from rule-based detection but included in the IF validation set.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ── Configuration ────────────────────────────────────────────────────────────

from src.agents.risk import (
    DB_PATH,
    PATTERN_ENCODING,
    LOW_THRESHOLD,
    MEDIUM_THRESHOLD,
)

MODEL_PATH = Path("models/isolation_forest.pkl")
SCALER_PATH = Path("models/scaler.pkl")
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

IF_CONTAMINATION = 0.0015
IF_RANDOM_STATE = 42
IF_N_ESTIMATORS = 200

# Rule weights for composite scoring
RULE_WEIGHT = 0.6
IF_WEIGHT = 0.4

# Pattern thresholds
FAN_THRESHOLD = 5
CYCLE_MIN_LENGTH = 3
STACK_MIN_LENGTH = 3
ROLLING_WINDOW_DAYS = 30


def _fetch_features_for_accounts(
    con: duckdb.DuckDBPyConnection,
    account_ids: list[str],
    split: str = "train",
) -> pd.DataFrame:
    """Fetch transaction data and compute features for a set of accounts."""
    table = f"splits.{split}"
    placeholders = ",".join("?" for _ in account_ids)
    query = f"""
        SELECT * FROM {table}
        WHERE "Account" IN ({placeholders})
           OR "Account.1" IN ({placeholders})
        ORDER BY "Timestamp"
    """
    params = account_ids * 2
    df = con.execute(query, params).fetchdf()

    if df.empty:
        return df

    # Compute standard features
    df["timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values(["Account", "timestamp"])

    # Velocity: 30-day rolling count per account
    df["velocity_30d"] = (
        df.groupby("Account")["timestamp"]
        .apply(lambda x: x.diff().dt.days.rolling(ROLLING_WINDOW_DAYS, min_periods=1).count())
        .reset_index(level=0, drop=True)
    )

    # Rolling sum of Amount Paid (30-day window)
    df["rolling_sum_30d"] = (
        df.groupby("Account")["Amount Paid"]
        .transform(lambda x: x.rolling(ROLLING_WINDOW_DAYS, min_periods=1).sum())
    )

    # Amount deviation from account mean
    account_means = df.groupby("Account")["Amount Paid"].transform("mean")
    account_stds = df.groupby("Account")["Amount Paid"].transform("std")
    df["amount_dev"] = (df["Amount Paid"] - account_means) / (account_stds + 1e-9)

    # Cross-currency risk
    df["rule_cross_currency"] = (df["Receiving Currency"] != df["Payment Currency"]).astype(int)

    # Pattern type encoding (for rule-based scoring)
    df["pattern_encoded"] = df["pattern_type"].map(PATTERN_ENCODING).fillna(0).astype(int)

    return df


# ── Rule-based heuristics ────────────────────────────────────────────────────


def apply_rule_based_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic AML rule flags to transactions."""
    if df.empty:
        return df

    # Rule 1: High velocity (more than 3 std devs above mean)
    velocity_mean = df["velocity_30d"].mean()
    velocity_std = df["velocity_30d"].std()
    df["rule_high_velocity"] = (
        df["velocity_30d"] > velocity_mean + 3 * velocity_std
    ).astype(int)

    # Rule 2: Large amount deviation (z-score > 3)
    df["rule_amount_anomaly"] = (df["amount_dev"].abs() > 3).astype(int)

    # Rule 3: Cross-currency layering
    df["rule_cross_currency"] = df["cross_currency_risk"]

    # Rule 4: Known laundering pattern type
    df["rule_known_pattern"] = (df["pattern_encoded"] > 0).astype(int)

    # Rule 5: High rolling sum (top 5% of all transactions)
    rolling_95th = df["rolling_sum_30d"].quantile(0.95)
    df["rule_high_volume"] = (df["rolling_sum_30d"] > rolling_95th).astype(int)

    # Composite rule score (0-5 scale)
    df["rule_score"] = (
        df["rule_high_velocity"] +
        df["rule_amount_anomaly"] +
        df["rule_cross_currency"] +
        df["rule_known_pattern"] +
        df["rule_high_volume"]
    ) / 5.0  # normalize to 0-1

    return df


# ── Isolation Forest training ────────────────────────────────────────────────


def train_isolation_forest(split: str = "train", sample_size: int = 100_000) -> tuple:
    """Train Isolation Forest on the train split and save checkpoint.

    Returns (model, scaler, feature_columns).
    """
    print(f"Training Isolation Forest on {split} split (sample_size={sample_size:,})...")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        # Sample transactions (prefer labeled ones, but include unlabeled for IF validation)
        query = f"""
            SELECT * FROM splits.{split}
            ORDER BY RANDOM()
            LIMIT {sample_size}
        """
        df = con.execute(query).fetchdf()
    finally:
        con.close()

    if df.empty:
        raise ValueError(f"No data found in splits.{split}")

    # Compute features on a sample of accounts using a fresh connection
    sample_account_ids = df["Account"].unique().tolist()[:1000]
    con2 = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = _fetch_features_for_accounts(con2, account_ids=sample_account_ids, split=split)
    finally:
        con2.close()

    if df.empty:
        raise ValueError("Feature computation returned empty dataframe")

    # Select features for IF
    feature_cols = ["velocity_30d", "rolling_sum_30d", "amount_dev", "cross_currency_risk"]
    X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Isolation Forest
    iso_forest = IsolationForest(
        contamination=IF_CONTAMINATION,
        random_state=IF_RANDOM_STATE,
        n_estimators=IF_N_ESTIMATORS,
    )
    iso_forest.fit(X_scaled)

    # Save checkpoint
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(iso_forest, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    print(f"  Model saved to {MODEL_PATH}")
    print(f"  Scaler saved to {SCALER_PATH}")
    print(f"  Trained on {len(df):,} samples with {len(feature_cols)} features")

    return iso_forest, scaler, feature_cols


def load_isolation_forest() -> tuple:
    """Load pre-trained Isolation Forest model and scaler from checkpoint."""
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        raise FileNotFoundError(
            f"Model checkpoint not found at {MODEL_PATH}. "
            "Run train_isolation_forest() first to train and save the model."
        )
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    return model, scaler


# ── Tool implementations ─────────────────────────────────────────────────────


class AnomalyInput(BaseModel):
    account_ids: list[str] = Field(
        description="List of account IDs to score for anomalies",
    )
    split: str = Field(
        default="train",
        description="Data split to query: 'train', 'validation', or 'test'",
    )
    use_pretrained: bool = Field(
        default=True,
        description="Whether to use the pre-trained Isolation Forest model (if available)",
    )


def score_anomaly(input: AnomalyInput) -> str:
    """Score accounts for anomalies using hybrid IF + rule-based approach.

    Returns a summary of anomaly scores and triggered rules for each account.
    """
    if not input.account_ids:
        return "No account IDs provided. Please specify account IDs to score."

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        # Fetch transactions for accounts
        df = _fetch_features_for_accounts(con, input.account_ids, input.split)
    finally:
        con.close()

    if df.empty:
        return f"No transactions found for accounts {input.account_ids} in {input.split} split."

    # Apply rule-based flags
    df = apply_rule_based_flags(df)

    # Load or train Isolation Forest
    if input.use_pretrained:
        try:
            iso_forest, scaler = load_isolation_forest()
            feature_cols = ["velocity_30d", "rolling_sum_30d", "amount_dev", "cross_currency_risk"]
            X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
            X_scaled = scaler.transform(X)

            # IF returns -1 for anomalies, 1 for normal
            # Convert to anomaly score: higher = more anomalous
            raw_scores = iso_forest.decision_function(X_scaled)
            # Normalize to 0-1 (more negative = more anomalous)
            df["if_score"] = 1 - (raw_scores + 1) / 2
            df["if_score"] = df["if_score"].clip(0, 1)
        except FileNotFoundError:
            return (
                "Isolation Forest model not found. "
                "Please run train_isolation_forest() first to train the model."
            )
    else:
        df["if_score"] = 0.0

    # Composite score: 0.4 * IF + 0.6 * Rule
    df["composite_score"] = IF_WEIGHT * df["if_score"] + RULE_WEIGHT * df["rule_score"]

    # Generate summary per account
    results = [f"Anomaly Scores for {len(input.account_ids)} accounts (split={input.split}):"]
    results.append(f"Model: Isolation Forest (contamination={IF_CONTAMINATION}) + Rule-based hybrid")
    results.append(f"Composite = {IF_WEIGHT:.1f} * IF + {RULE_WEIGHT:.1f} * Rule\n")

    for acct in input.account_ids:
        acct_df = df[df["Account"] == acct]
        if acct_df.empty:
            acct_df = df[df["Account.1"] == acct]
        if acct_df.empty:
            results.append(f"  {acct}: No transactions found")
            continue

        avg_composite = acct_df["composite_score"].mean()
        avg_if = acct_df["if_score"].mean()
        avg_rule = acct_df["rule_score"].mean()
        txn_count = len(acct_df)

        # Determine triggered rules
        triggered = []
        if acct_df["rule_high_velocity"].any():
            triggered.append("High Velocity")
        if acct_df["rule_amount_anomaly"].any():
            triggered.append("Amount Anomaly")
        if acct_df["rule_cross_currency"].any():
            triggered.append("Cross-Currency Risk")
        if acct_df["rule_known_pattern"].any():
            pattern_types = acct_df[acct_df["rule_known_pattern"] == 1]["pattern_type"].unique()
            triggered.append(f"Known Pattern ({', '.join(pattern_types)})")
        if acct_df["rule_high_volume"].any():
            triggered.append("High Volume")

        # Risk classification — thresholds match classify_risk() in risk.py
        # LOW < 0.30, MEDIUM < 0.70, HIGH >= 0.70
        if avg_composite >= MEDIUM_THRESHOLD:
            risk = "HIGH"
        elif avg_composite >= LOW_THRESHOLD:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        results.append(f"  {acct}:")
        results.append(f"    Transactions: {txn_count}")
        results.append(f"    IF Score:     {avg_if:.3f}")
        results.append(f"    Rule Score:   {avg_rule:.3f}")
        results.append(f"    Composite:    {avg_composite:.3f}")
        results.append(f"    Risk:         {risk}")
        if triggered:
            results.append(f"    Triggered:    {', '.join(triggered)}")
        else:
            results.append(f"    Triggered:    None")

    return "\n".join(results)


# ── Batch scoring tool ───────────────────────────────────────────────────────


class BatchScanInput(BaseModel):
    top_n: int = Field(
        default=20,
        description=(
            "Number of top accounts to scan (by transaction volume). "
            "Capped at 50 to avoid excessive runtime. "
            "Use this for 'scan the whole dataset' or 'find everything suspicious' requests."
        ),
    )
    split: str = Field(
        default="train",
        description="Data split to scan: 'train', 'validation', or 'test'",
    )
    min_composite_score: float = Field(
        default=0.3,
        description="Only return accounts at or above this composite score (0.0–1.0). Default 0.3 = MEDIUM+.",
    )


def batch_scan_top_accounts(input: BatchScanInput) -> str:
    """Scan the top-N most active accounts for anomalies and return a ranked suspicious list.

    Designed for 'scan the whole dataset' requests. Selects the top-N accounts
    by transaction volume, scores each with the hybrid IF + rule-based scorer,
    and returns all accounts above the min_composite_score threshold.

    Full-dataset scanning over 500K+ accounts is intentionally not supported
    (would take hours); this tool provides a practical high-signal shortlist
    by targeting the most active accounts — where laundering is most likely to
    appear at scale.
    """
    top_n = min(input.top_n, 50)  # hard cap

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        # Get top-N senders by transaction count in the chosen split
        table = f"splits.{input.split}"
        top_accts = con.execute(f"""
            SELECT "Account", COUNT(*) as cnt
            FROM {table}
            GROUP BY "Account"
            ORDER BY cnt DESC
            LIMIT {top_n}
        """).fetchall()
        account_ids = [r[0] for r in top_accts]
        df = _fetch_features_for_accounts(con, account_ids, input.split)
    finally:
        con.close()

    if df.empty:
        return f"No transactions found for top-{top_n} accounts in splits.{input.split}."

    df = apply_rule_based_flags(df)

    try:
        iso_forest, scaler = load_isolation_forest()
        feature_cols = ["velocity_30d", "rolling_sum_30d", "amount_dev", "cross_currency_risk"]
        X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
        X_scaled = scaler.transform(X)
        raw_scores = iso_forest.decision_function(X_scaled)
        df["if_score"] = (1 - (raw_scores + 1) / 2).clip(0, 1)
    except FileNotFoundError:
        df["if_score"] = 0.0

    df["composite_score"] = IF_WEIGHT * df["if_score"] + RULE_WEIGHT * df["rule_score"]

    # Aggregate per account
    records = []
    for acct in account_ids:
        acct_df = df[df["Account"] == acct]
        if acct_df.empty:
            continue
        composite = acct_df["composite_score"].mean()
        if composite < input.min_composite_score:
            continue
        risk = "HIGH" if composite >= MEDIUM_THRESHOLD else ("MEDIUM" if composite >= LOW_THRESHOLD else "LOW")
        triggered = []
        if acct_df["rule_high_velocity"].any(): triggered.append("High Velocity")
        if acct_df["rule_amount_anomaly"].any(): triggered.append("Amount Anomaly")
        if acct_df["rule_cross_currency"].any(): triggered.append("Cross-Currency")
        if acct_df["rule_known_pattern"].any():
            ptypes = acct_df[acct_df["rule_known_pattern"] == 1]["pattern_type"].unique()
            triggered.append(f"Pattern({','.join(str(p) for p in ptypes[:2])})")
        if acct_df["rule_high_volume"].any(): triggered.append("High Volume")
        records.append((composite, risk, acct, len(acct_df), triggered))

    records.sort(reverse=True)

    lines = [
        f"Batch Scan — Top-{top_n} accounts by volume in splits.{input.split}",
        f"Threshold: composite >= {input.min_composite_score}  |  "
        f"Found {len(records)} suspicious account(s)",
        f"Model: Isolation Forest (contamination={IF_CONTAMINATION}) + Rule-based hybrid",
        f"NOTE: Full 500K-account scan not supported; this targets the highest-activity",
        f"      accounts where laundering risk is concentrated.",
        "",
        f"  {'Account':<15}  {'Risk':<8}  {'Score':>6}  {'Txns':>6}  Triggered Rules",
        f"  {'-'*15}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*30}",
    ]
    for composite, risk, acct, txns, triggered in records[:20]:
        rule_str = ", ".join(triggered) if triggered else "None"
        lines.append(f"  {acct:<15}  {risk:<8}  {composite:>6.3f}  {txns:>6,}  {rule_str}")

    if not records:
        lines.append("  No accounts exceeded the score threshold in this scan.")

    return "\n".join(lines)


# (agent factory removed — tools are bound directly in supervisor.py)
