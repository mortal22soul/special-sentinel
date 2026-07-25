"""Feature Engineering subagent for the Sentinel AML supervisor.

Computes transaction-level features from the DuckDB database:

Standard features (all rows):
- velocity:       number of transactions in the past 30 days for the same account
- rolling_sum_30: sum of Amount Paid in the past 30 days for the same account
- amount_dev:     z-score deviation of Amount Paid from the account's mean

AML pattern features (labeled rows only):
- fan_out_flag:   one account sends to >=5 unique receivers in a short window
- fan_in_flag:    one account receives from >=5 unique senders
- cycle_flag:     networkx detects a directed cycle in the account subgraph
- stack_flag:     same intermediate account appears in chains of length >=3
- scatter_gather_flag: many senders converge to one, then fan out again
- gather_scatter_flag: many receivers converge from one, then scatter again
- bipartite_flag: two sets of accounts with only cross-set edges
- cross_currency_risk: Receiving Currency != Payment Currency

Graph patterns (CYCLE, SCATTER-GATHER) are detected using networkx on
filtered subgraphs — NOT via recursive DuckDB CTEs — per the implementation
plan.
"""

from __future__ import annotations

import os
from collections import Counter

import duckdb
import networkx as nx
import pandas as pd
from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────────────

from src.agents.risk import DB_PATH
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

# Pattern detection thresholds
FAN_THRESHOLD = 5          # >=5 unique counterparties = fan in/out
CYCLE_MIN_LENGTH = 3       # minimum cycle length to flag
STACK_MIN_LENGTH = 3       # minimum chain length for stack detection
WINDOW_DAYS = 30           # rolling window for velocity features


# ── Helper functions ─────────────────────────────────────────────────────────


def _fetch_transactions_for_accounts(
    con: duckdb.DuckDBPyConnection,
    account_ids: list[str],
    split: str = "train",
) -> pd.DataFrame:
    """Fetch transaction rows for a set of accounts from a split table."""
    table = f"splits.{split}"
    placeholders = ",".join("?" for _ in account_ids)
    query = f"""
        SELECT * FROM {table}
        WHERE "Account" IN ({placeholders})
           OR "Account.1" IN ({placeholders})
    """
    params = account_ids + account_ids
    return con.execute(query, params).fetchdf()


def _build_directed_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Build a directed multigraph from transaction rows."""
    G = nx.DiGraph()
    for _, row in df.iterrows():
        src = row["Account"]
        dst = row["Account.1"]
        if G.has_edge(src, dst):
            G[src][dst]["weight"] += 1
        else:
            G.add_edge(src, dst, weight=1)
    return G


def detect_cycle(G: nx.DiGraph) -> bool:
    """Detect if the graph contains a cycle of length >= CYCLE_MIN_LENGTH."""
    try:
        cycle = nx.find_cycle(G, orientation="original")
        return len(cycle) >= CYCLE_MIN_LENGTH
    except nx.exception.NetworkXNoCycle:
        return False


def detect_fan_out(df: pd.DataFrame, account: str, threshold: int = FAN_THRESHOLD) -> bool:
    """Check if an account sends to >=threshold unique receivers in a window."""
    outbound = df[df["Account"] == account]
    unique_receivers = outbound["Account.1"].nunique()
    return unique_receivers >= threshold


def detect_fan_in(df: pd.DataFrame, account: str, threshold: int = FAN_THRESHOLD) -> bool:
    """Check if an account receives from >=threshold unique senders."""
    inbound = df[df["Account.1"] == account]
    unique_senders = inbound["Account"].nunique()
    return unique_senders >= threshold


def detect_stack(df: pd.DataFrame, account: str, min_length: int = STACK_MIN_LENGTH) -> bool:
    """Detect if an account repeatedly funnels through the same receiver.

    A stack (layering) pattern involves funds passing through the same
    intermediate account. With the simple sender→receiver data model,
    we approximate this by checking whether an account sends to the same
    receiver >= min_length times — indicating a consistent relay channel.
    """
    outbound = df[df["Account"] == account]
    if len(outbound) < min_length:
        return False
    # Count occurrences of each receiver; a stack shows repeated use
    # of the same relay account.
    from collections import Counter
    counts = Counter(outbound["Account.1"].tolist())
    return any(c >= min_length for c in counts.values())


def detect_scatter_gather(G: nx.DiGraph) -> bool:
    """Detect scatter-gather: many -> one -> many pattern."""
    for node in G.nodes():
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        if in_deg >= FAN_THRESHOLD and out_deg >= FAN_THRESHOLD:
            return True
    return False


def detect_gather_scatter(G: nx.DiGraph) -> bool:
    """Detect gather-scatter: many senders converge to hub, then hub fans out."""
    # Simplified: a node with high in-degree followed by nodes with high out-degree
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    high_in = [n for n, d in in_degrees.items() if d >= FAN_THRESHOLD]
    for node in high_in:
        # Check if this hub's out-neighbors have high out-degree (scatter)
        for _, neighbor in G.out_edges(node):
            if out_degrees.get(neighbor, 0) >= FAN_THRESHOLD:
                return True
    return False


def detect_bipartite(G: nx.DiGraph) -> bool:
    """Detect bipartite structure: two disjoint sets with only cross-set edges."""
    try:
        from networkx.algorithms.bipartite import is_bipartite
        return is_bipartite(G)
    except Exception:
        return False


# ── Tool implementations ─────────────────────────────────────────────────────


class FeatureInput(BaseModel):
    split: str = Field(
        default="train",
        description="Data split to compute features on: 'train', 'validation', or 'test'",
    )
    account_ids: list[str] = Field(
        default_factory=list,
        description="Specific account IDs to compute features for (empty = all labeled accounts)",
    )
    include_graph: bool = Field(
        default=True,
        description="Whether to run networkx graph-based pattern detection (slower but more accurate)",
    )


def cross_currency_flag(df: pd.DataFrame | pd.Series, account_col: str = "Account") -> bool | pd.Series:
    """Return True if the transaction uses different currencies, False otherwise.
    Accepts a DataFrame (returns a Series of bools) or a single-row Series (returns bool).
    """
    result = df["Receiving Currency"] != df["Payment Currency"]
    if isinstance(df, pd.Series):
        return bool(result)
    return result


def compute_features(input: FeatureInput) -> str:
    """Compute transaction-level features for AML pattern detection.

    Returns a summary of feature statistics for the requested split.
    """
    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        # Fetch all labeled transactions from the split
        table = f"splits.{input.split}"
        df = con.execute(f"""
            SELECT * FROM {table}
            WHERE pattern_type != 'UNLABELED'
        """).fetchdf()
    finally:
        con.close()

    if df.empty:
        return "No labeled transactions found in the requested split."

    total = len(df)
    results = [f"Features computed on {total:,} labeled rows from splits.{input.split}:"]

    # --- Standard features ---
    df["timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values(["Account", "timestamp"])

    # Velocity: transactions in past 30 days per account
    df["velocity_30d"] = (
        df.groupby("Account")["timestamp"]
        .apply(lambda x: x.diff().dt.days.lt(30).cumsum())
        .reset_index(level=0, drop=True)
    )

    # Rolling sum of Amount Paid (30-day window per account)
    df["rolling_sum_30d"] = (
        df.groupby("Account")["Amount Paid"]
        .transform(lambda x: x.rolling(30, min_periods=1).sum())
    )

    # Amount deviation from account mean
    account_means = df.groupby("Account")["Amount Paid"].transform("mean")
    account_stds = df.groupby("Account")["Amount Paid"].transform("std")
    df["amount_dev"] = (df["Amount Paid"] - account_means) / (account_stds + 1e-9)

    results.append(f"\nStandard Features:")
    results.append(f"  Mean velocity (30d): {df['velocity_30d'].mean():.1f} txns/account")
    results.append(f"  Mean rolling sum (30d): ${df['rolling_sum_30d'].mean():,.2f}")
    results.append(f"  Mean amount deviation: {df['amount_dev'].mean():.2f}")

    # --- Cross-currency risk (rule_cross_currency matches anomaly.py naming) ---
    df["rule_cross_currency"] = (df["Receiving Currency"] != df["Payment Currency"]).astype(int)
    cc_count = df["rule_cross_currency"].sum()
    results.append(f"\nCross-Currency Risk:")
    results.append(f"  Flagged rows: {cc_count:,} ({cc_count/total:.1%})")

    # --- Pattern distribution ---
    pattern_counts = df["pattern_type"].value_counts()
    results.append(f"\nPattern Type Distribution:")
    for ptype, count in pattern_counts.items():
        results.append(f"  {ptype}: {count:,} ({count/total:.1%})")

    # --- Graph-based detection (optional, expensive) ---
    if input.include_graph:
        results.append(f"\nGraph Pattern Detection (networkx):")
        unique_accounts = pd.concat([df["Account"], df["Account.1"]]).unique()
        # Sample if too many accounts (networkx is slow on large graphs)
        sample_size = min(len(unique_accounts), 500)
        sample_accounts = unique_accounts[:sample_size]

        sample_df = df[
            df["Account"].isin(sample_accounts) | df["Account.1"].isin(sample_accounts)
        ]
        G = _build_directed_graph(sample_df)

        results.append(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        cycle_flag = detect_cycle(G)
        scatter_gather = detect_scatter_gather(G)
        gather_scatter = detect_gather_scatter(G)
        bipartite = detect_bipartite(G)

        results.append(f"  CYCLE detected:            {cycle_flag}")
        results.append(f"  SCATTER-GATHER detected:   {scatter_gather}")
        results.append(f"  GATHER-SCATTER detected:   {gather_scatter}")
        results.append(f"  BIPARTITE detected:        {bipartite}")

        # Fan in/out on sampled accounts
        fan_out_count = sum(1 for acct in sample_accounts if detect_fan_out(sample_df, acct))
        fan_in_count = sum(1 for acct in sample_accounts if detect_fan_in(sample_df, acct))
        stack_count = sum(1 for acct in sample_accounts if detect_stack(sample_df, acct))
        results.append(f"  FAN-OUT accounts:          {fan_out_count}")
        results.append(f"  FAN-IN accounts:           {fan_in_count}")
        results.append(f"  STACK accounts:            {stack_count}")

    return "\n".join(results)


# ── Agent factory ────────────────────────────────────────────────────────────


# (agent factory removed — tools are bound directly in supervisor.py)
