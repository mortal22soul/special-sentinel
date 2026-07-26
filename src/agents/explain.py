"""Explainability subagent for the Sentinel AML supervisor.

Translates deterministic rule flags and composite anomaly scores into
plain-English AML investigation summaries suitable for frontend display.

Uses rule-based LLM reasoning (no SHAP/LIME) — the deterministic flags
from the anomaly detection agent are fed directly to the LLM with a
structured system prompt.
"""

from __future__ import annotations

import os

from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────────────

DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

# Canonical AML pattern taxonomy — imported from risk.py (single source of truth).
from src.agents.risk import AML_PATTERN_TYPES


# ── Tool input schemas ───────────────────────────────────────────────────────


class ExplainInput(BaseModel):
    account_id: str = Field(
        description="The account ID to generate an investigation summary for",
    )
    composite_score: float = Field(
        description="Composite anomaly score (0.0 to 1.0) from the anomaly detection agent",
    )
    if_score: float = Field(
        default=0.0,
        description="Isolation Forest anomaly score (0.0 to 1.0)",
    )
    rule_score: float = Field(
        default=0.0,
        description="Rule-based anomaly score (0.0 to 1.0)",
    )
    triggered_rules: list[str] = Field(
        default_factory=list,
        description="List of triggered rule names (e.g., 'High Velocity', 'Cross-Currency Risk')",
    )
    pattern_types: list[str] = Field(
        default_factory=list,
        description="Ground-truth AML pattern types matched (e.g., 'FAN-OUT', 'CYCLE')",
    )
    transaction_count: int = Field(
        default=0,
        description="Number of transactions analyzed for this account",
    )
    total_amount: float = Field(
        default=0.0,
        description="Total transaction amount for this account",
    )
    risk_level: str = Field(
        default="LOW",
        description="Risk classification (LOW, MEDIUM, HIGH)",
    )


# ── Prompt template ──────────────────────────────────────────────────────────

EXPLANATION_SYSTEM_PROMPT = """You are an AML investigation analyst. Your job is to translate technical detection results into a plain-English investigation summary for compliance officers.

Given the following account-level detection results, produce a formal "AML Investigation Summary" that:

1. Starts with a clear risk verdict (LOW/MEDIUM/HIGH)
2. Lists all triggered rules and what they mean in business terms
3. Identifies any matched ground-truth AML pattern types with brief descriptions
4. Provides key statistics (transaction count, total volume, velocity)
5. Recommends next steps based on the risk level

Ground-truth AML pattern types and their meanings:
- FAN-OUT: One account rapidly disperses funds to many recipients
- FAN-IN: One account rapidly collects funds from many sources
- CYCLE: Funds circulate through a closed loop of accounts
- STACK: Layered transactions using the same intermediate account
- SCATTER-GATHER: Funds split across many accounts, then reconverge
- GATHER-SCATTER: Funds collected to a hub, then redistributed
- BIPARTITE: Two distinct account sets with only cross-set transactions
- RANDOM: Unstructured, irregular transaction patterns

Scoring:
- Isolation Forest (ML): Detects statistical anomalies without labeled data
- Rule-based: Deterministic flags for known AML typologies
- Composite: 0.4 * ML + 0.6 * Rule (higher = more suspicious)

Risk thresholds:
- LOW: Composite < 0.30
- MEDIUM: Composite 0.30 - 0.70
- HIGH: Composite >= 0.70

Output format:
Use clear sections with headers. Be concise but thorough. Avoid jargon.
Do not include disclaimers about being an AI — write as a compliance analyst would."""


# ── Tool implementation ──────────────────────────────────────────────────────


def generate_investigation_summary(input: ExplainInput) -> str:
    """Generate a plain-English AML investigation summary for an account.

    Uses the Azure OpenAI LLM to translate technical detection results
    into a human-readable investigation summary.
    """
    llm = AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment=DEPLOYMENT,
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version="2025-04-01-preview",
        temperature=0.3,  # Slightly higher for natural language generation
    )

    # Build the user message with detection results
    user_message = f"""Account: {input.account_id}
Risk Level: {input.risk_level}
Composite Score: {input.composite_score:.3f} (ML: {input.if_score:.3f}, Rule: {input.rule_score:.3f})

Statistics:
- Transactions analyzed: {input.transaction_count:,}
- Total transaction amount: {input.total_amount:,.2f} (native currency)

Triggered Rules:
{chr(10).join(f'- {rule}' for rule in input.triggered_rules) if input.triggered_rules else '- None'}

Matched AML Pattern Types:
{chr(10).join(f'- {ptype}' for ptype in input.pattern_types) if input.pattern_types else '- None'}

Please generate a formal AML Investigation Summary for this account."""

    response = llm.invoke([
        {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ])

    return response.content


# (agent factory removed — tools are bound directly in supervisor.py)
