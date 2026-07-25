"""Supervisor Orchestration Core for the Sentinel AML detection system.

The supervisor dynamically routes natural-language investigation queries to
specialized subagents using LangChain's ``create_agent`` with tool-wrapped
subagent functions. It uses a structured output schema (Pydantic) to ensure
every response includes ``intent``, ``execution_plan``, ``tools_invoked``,
``tools_skipped``, ``reasoning``, and ``results``.

A ``MemorySaver`` checkpointer enables multi-turn conversation support so that
follow-up queries like "Now show its top receivers" have full context from the
prior turn.

Azure OpenAI configuration
--------------------------
Reads from environment variables (set in ``.env`` or shell):

    AZURE_OPENAI_API_KEY          — required
    AZURE_OPENAI_ENDPOINT         — required (base URL, e.g.
                                    https://<resource>.openai.azure.com/)
    AZURE_OPENAI_DEPLOYMENT_NAME  — optional, defaults to ``gpt-5.4-mini``
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────────────

DB_PATH = Path("data/sentinel.duckdb")
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

# ── Structured output schema ─────────────────────────────────────────────────


class SupervisorOutput(BaseModel):
    """Structured output returned by the supervisor for every query."""

    intent: str = Field(
        description=(
            "Detected intent: 'aggregation', 'investigation', 'profiling', "
            "'features', 'explanation', or 'unknown'"
        )
    )
    execution_plan: list[str] = Field(
        description="Ordered list of tool calls the supervisor planned to make"
    )
    tools_invoked: list[str] = Field(
        description="Tools actually invoked during execution"
    )
    tools_skipped: list[str] = Field(
        description="Tools NOT invoked (demonstrates dynamic routing)"
    )
    reasoning: str = Field(
        description="Plain-English explanation of the routing decision"
    )
    results: str = Field(
        description="Concise summary of results from the invoked tools"
    )


# ── Subagent tool imports ────────────────────────────────────────────────────

from src.agents.data_query import get_schema, query_database
from src.agents.features import compute_features
from src.agents.anomaly import batch_scan_top_accounts, score_anomaly
from src.agents.risk import classify_accounts
from src.agents.explain import generate_investigation_summary

# All tools available to the supervisor — used for tools_skipped calculation.
ALL_TOOLS = [
    query_database,
    get_schema,
    compute_features,
    score_anomaly,
    batch_scan_top_accounts,
    classify_accounts,
    generate_investigation_summary,
]

# Derived automatically from ALL_TOOLS so the list stays in sync with the
# actual tool registry.  LangChain tools expose ``.name``; plain Python
# functions fall back to ``__name__``.
ALL_TOOL_NAMES = [
    t.name if hasattr(t, "name") else t.__name__
    for t in ALL_TOOLS
]

SYSTEM_PROMPT = """You are the Sentinel AML Supervisor — an orchestrator that routes
natural-language investigation queries to specialized subagents.

## Available Tools & Their Purposes

1. **query_database** — Execute read-only DuckDB SQL for aggregations, counts,
   filters, and profiling queries.
   Use for: "count transactions over $10,000", "what's the average amount?",
   "top 10 sender accounts", "currency breakdown", "any null values?".
   For EDA/profiling, write SQL directly — e.g.
   `SELECT "Payment Currency", COUNT(*), ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM raw.transactions GROUP BY 1 ORDER BY COUNT(*) DESC`
   for currency distribution, or `SELECT "Account", COUNT(*), SUM("Amount Paid")
   FROM raw.transactions GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 10` for top accounts.

2. **get_schema** — Get the DuckDB schema (table names, columns).
   Use for: understanding the database structure before writing SQL.

3. **compute_features** — Compute transaction-level features (velocity, rolling sums,
   amount deviation) and detect AML patterns (FAN-OUT, FAN-IN, CYCLE, STACK,
   SCATTER-GATHER, GATHER-SCATTER, BIPARTITE, RANDOM) using networkx graph analysis.
   Use for: "compute features for account X", "detect AML patterns", "find cycles".

4. **score_anomaly** — Hybrid Isolation Forest + rule-based anomaly scoring for specific accounts.
   Composite = 0.4 * IF + 0.6 * Rule. Returns risk tier (LOW/MEDIUM/HIGH).
   Use for: "investigate account X", "score this account for anomalies".

5. **batch_scan_top_accounts** — Scan the top-N most active accounts for anomalies.
   Returns a ranked suspicious account list. Capped at 50 accounts for runtime.
   Use for: "find everything suspicious", "scan the whole dataset", "which accounts are most at risk?",
   "show me all suspicious accounts", "investigate all accounts".

6. **classify_accounts** — Map composite scores to Low/Medium/High risk tiers
   with escalation actions.
   Use for: "classify risk for these accounts", "what's the risk level?"

7. **generate_investigation_summary** — Generate plain-English AML Investigation
   Summary from detection results.
   Use for: "explain why this account is flagged", "generate investigation report".

## Routing Rules

- **Pure aggregation/profiling queries** → Use query_database (+ get_schema if needed)
  Examples: "count transactions over $10,000", "what's the average amount?",
  "top 10 accounts by transaction count", "currency breakdown", "check for null values".
  Write SQL directly — do not invoke compute_features or other ML tools.

- **Investigation queries** → Use score_anomaly → classify_accounts → generate_investigation_summary
  Examples: "Investigate Account 8000EBD30", "show me high-risk accounts"

- **Dataset-wide scan queries** → Use batch_scan_top_accounts → generate_investigation_summary
  Examples: "find everything suspicious", "scan the whole dataset", "which accounts are most at risk?"

- **Feature / AML pattern queries** → Use compute_features
  Examples: "compute velocity for Account X", "detect FAN-OUT patterns"

- **Multi-step investigations** → Invoke sequentially: compute_features → score_anomaly → classify_accounts → generate_investigation_summary

## Output Instructions

At the END of your response, after completing the task, always include a JSON block
(fenced with ```json ... ```) containing the structured routing metadata:

{
  "intent": "<one of: aggregation|investigation|profiling|features|explanation|unknown>",
  "execution_plan": ["<tool1>", "<tool2>", ...],
  "tools_invoked": ["<tool1>", "<tool2>", ...],
  "tools_skipped": ["<tool3>", "<tool4>", ...],
  "reasoning": "<plain-English explanation of why these tools were chosen>"
}

## Constraints

- All SQL queries must be READ-ONLY (no INSERT/UPDATE/DELETE/DROP/ALTER)
- Column names with spaces MUST be double-quoted: "Amount Paid", "Is Laundering", "From Bank", "To Bank"
- The sender account column is "Account" (NOT "From Account"). The receiver column is "Account.1" (NOT "To Account").
- Always use subqueries or CTEs correctly: columns referenced in outer SELECT must appear in GROUP BY or aggregates
- Always explain WHY certain tools were chosen and which were skipped
"""

# ── Supervisor factory ───────────────────────────────────────────────────────


def create_supervisor(checkpointer: MemorySaver | None = None) -> Any:
    """Create and return the supervisor agent with all subagent tools wired in.

    Args:
        checkpointer: ``MemorySaver`` for multi-turn conversation support.
                      If ``None``, a new one is created automatically.

    Returns:
        A compiled LangChain/LangGraph agent ready to route AML queries.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    llm = AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment=DEPLOYMENT,
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version="2025-04-01-preview",
        temperature=0.0,
    )

    agent = create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return agent


# ── Run helper ───────────────────────────────────────────────────────────────


def _extract_structured_metadata(messages: list) -> dict[str, Any]:
    """Parse the JSON routing metadata block from the final AI message.

    The supervisor is instructed to append a ```json ... ``` block at the end
    of its response.  We extract it here and return a structured dict.
    Falls back to sensible defaults if the block is absent or malformed.

    ``tools_invoked`` and ``tools_skipped`` are ALWAYS recomputed from the
    actual ``ToolMessage`` history so that the LLM cannot hallucinate an
    inconsistent skip list.  Other fields (intent, reasoning, execution_plan)
    come from the JSON block when present, otherwise from defaults.
    """
    import re

    parsed: dict[str, Any] | None = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str):
            match = re.search(r"```json\s*(\{.*?\})\s*```", msg.content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    break
                except json.JSONDecodeError:
                    parsed = None

    # Authoritative: tools_invoked comes from the actual ToolMessage history,
    # not from the LLM's JSON block (which has been seen to omit tools).
    tool_names_used: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_names_used.append(msg.name)
    tools_invoked = list(dict.fromkeys(tool_names_used))  # deduplicated, ordered

    return {
        "intent": (parsed or {}).get("intent", "unknown"),
        "execution_plan": (parsed or {}).get("execution_plan", tools_invoked),
        "tools_invoked": tools_invoked,
        # Always the exact complement of tools_invoked over the full registry —
        # guarantees the JSON block cannot hallucinate a partial skip list.
        "tools_skipped": [t for t in ALL_TOOL_NAMES if t not in tools_invoked],
        "reasoning": (parsed or {}).get(
            "reasoning",
            "Routing metadata not found in response; inferred from tool call history.",
        ),
    }


def run_supervisor(
    query: str,
    thread_id: str = "default",
    checkpointer: MemorySaver | None = None,
) -> dict[str, Any]:
    """Run a query through the supervisor and return structured results.

    Args:
        query:       Natural-language query from the user.
        thread_id:   Conversation thread ID for multi-turn memory.
        checkpointer: ``MemorySaver`` instance; created fresh if ``None``.

    Returns:
        Dict matching the ``SupervisorOutput`` schema plus a ``messages`` key.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    agent = create_supervisor(checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    try:
        response = agent.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
        )
    except Exception as exc:
        # If the thread state is corrupted (e.g. dangling tool_call_id from a
        # prior failed turn), retry once on a fresh sub-thread so multi-turn
        # sessions survive transient tool errors.
        err_str = str(exc)
        if "tool_call_id" in err_str or "tool_calls" in err_str:
            import uuid
            fallback_thread = f"{thread_id}-retry-{uuid.uuid4().hex[:6]}"
            config = {"configurable": {"thread_id": fallback_thread}}
            response = agent.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=config,
            )
        else:
            raise

    messages = response.get("messages", [])

    # Extract structured routing metadata from the JSON block in the response
    meta = _extract_structured_metadata(messages)

    # Extract the final human-readable answer, stripping the trailing ```json...```
    # metadata block so callers receive clean prose only.
    final_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
            final_text = re.sub(
                r"\n*```json\s*\{.*?\}\s*```\s*$", "", msg.content, flags=re.DOTALL
            ).rstrip()
            break

    return {
        "intent": meta.get("intent", "unknown"),
        "execution_plan": meta.get("execution_plan", []),
        "tools_invoked": meta.get("tools_invoked", []),
        "tools_skipped": meta.get("tools_skipped", []),
        "reasoning": meta.get("reasoning", ""),
        "results": final_text,
        "messages": messages,
    }
