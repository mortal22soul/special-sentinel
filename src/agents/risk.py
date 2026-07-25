"""Risk Classification subagent for the Sentinel AML supervisor.

Maps composite anomaly scores (0-1) to Low/Medium/High risk tiers and
generates recommended escalation actions.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────────────

DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

# Risk thresholds (composite score 0-1 range) — single source of truth used
# by score_anomaly, classify_accounts, batch_scan_top_accounts, and tests.
LOW_THRESHOLD = 0.30
MEDIUM_THRESHOLD = 0.70

# Single shared database location (imported by other agent modules).
DB_PATH = Path("data/sentinel.duckdb")

# Canonical AML pattern taxonomy — single source of truth shared by
# anomaly.py (pattern encoding) and explain.py (display labels).
AML_PATTERN_TYPES = [
    "FAN-OUT", "FAN-IN", "CYCLE", "STACK",
    "SCATTER-GATHER", "GATHER-SCATTER", "BIPARTITE", "RANDOM",
]
PATTERN_ENCODING = {name: i + 1 for i, name in enumerate(AML_PATTERN_TYPES)}


# ── Tool input schemas ───────────────────────────────────────────────────────


class RiskInput(BaseModel):
    account_ids: list[str] = Field(
        description="List of account IDs to classify",
    )
    scores: dict[str, float] = Field(
        description="Composite anomaly scores per account (0.0 to 1.0)",
    )
    triggered_rules: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Triggered rule names per account (from anomaly detection)",
    )


# ── Risk classification logic ────────────────────────────────────────────────


def classify_risk(composite_score: float) -> tuple[str, str]:
    """Classify risk level and return escalation action based on composite score.

    Returns (risk_level, escalation_action).
    """
    if composite_score >= MEDIUM_THRESHOLD:
        return (
            "HIGH",
            "Auto-Block + Immediate Investigation: "
            "Strong anomaly signals detected. Escalate to compliance team "
            "for SAR filing consideration.",
        )
    elif composite_score >= LOW_THRESHOLD:
        return (
            "MEDIUM",
            "Manual Review Required: "
            "Moderate anomaly signals detected. Assign to analyst for "
            "further investigation and transaction monitoring.",
        )
    else:
        return (
            "LOW",
            "No Action Required: "
            "Low anomaly score. Continue routine monitoring.",
        )


def classify_accounts(input: RiskInput) -> str:
    """Classify accounts into Low/Medium/High risk tiers with escalation actions.

    Takes composite anomaly scores and triggered rules from the anomaly detection
    agent and produces a risk classification summary.
    """
    if not input.account_ids:
        return "No account IDs provided."

    results = [f"Risk Classification for {len(input.account_ids)} accounts:"]
    results.append(f"Thresholds: LOW < {LOW_THRESHOLD}, MEDIUM < {MEDIUM_THRESHOLD}, HIGH >= {MEDIUM_THRESHOLD}")
    results.append("")

    # Aggregate by risk tier
    high_risk = []
    medium_risk = []
    low_risk = []

    for acct in input.account_ids:
        score = input.scores.get(acct, 0.0)
        risk, action = classify_risk(score)
        triggered = input.triggered_rules.get(acct, [])

        entry = {
            "account": acct,
            "score": score,
            "risk": risk,
            "action": action,
            "triggered": triggered,
        }

        if risk == "HIGH":
            high_risk.append(entry)
        elif risk == "MEDIUM":
            medium_risk.append(entry)
        else:
            low_risk.append(entry)

    # Format results grouped by risk tier
    for tier_name, tier_list in [("HIGH RISK", high_risk), ("MEDIUM RISK", medium_risk), ("LOW RISK", low_risk)]:
        if not tier_list:
            continue
        results.append(f"=== {tier_name} ({len(tier_list)} accounts) ===")
        for entry in tier_list:
            results.append(f"  {entry['account']}:")
            results.append(f"    Score:    {entry['score']:.3f}")
            results.append(f"    Risk:     {entry['risk']}")
            results.append(f"    Action:   {entry['action']}")
            if entry["triggered"]:
                results.append(f"    Triggered: {', '.join(entry['triggered'])}")
            else:
                results.append(f"    Triggered: None")
        results.append("")

    # Summary statistics
    results.append("=== Summary ===")
    results.append(f"  HIGH:   {len(high_risk)} accounts")
    results.append(f"  MEDIUM: {len(medium_risk)} accounts")
    results.append(f"  LOW:    {len(low_risk)} accounts")
    total = len(input.account_ids)
    if total > 0:
        results.append(f"  High-risk rate: {len(high_risk)/total:.1%}")

    return "\n".join(results)


# (agent factory removed — tools are bound directly in supervisor.py)
