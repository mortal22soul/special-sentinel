"""End-to-end smoke test for the Sentinel AML detection system.

Runs one full investigation query through the supervisor and validates that:
1. All 7 tools are importable
2. The supervisor returns all required structured output fields
3. The full pipeline (supervisor → tools → structured output) works

Usage
-----
    uv run python src/smoke_test.py

Requires:
    - AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in .env or shell
    - data/sentinel.duckdb ingested (run src/data/ingest.py first)
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS ✓" if condition else "FAIL ✗"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f": {detail}"
    print(msg)
    return condition


def main() -> None:
    print("=" * 60)
    print("Sentinel AML — Smoke Test")
    print("=" * 60)

    results: list[bool] = []

    # ── Step 1: Import all tools ───────────────────────────────────────────────
    print("\n[1] Importing all 7 tools...")
    try:
        from src.agents.data_query import query_database, get_schema
        from src.agents.features import compute_features
        from src.agents.anomaly import score_anomaly
        from src.agents.risk import classify_accounts
        from src.agents.explain import generate_investigation_summary
        from src.supervisor import SupervisorOutput, run_supervisor, create_supervisor

        results.append(check("All imports", True))
    except ImportError as exc:
        results.append(check("All imports", False, str(exc)))
        print("\nSmoke test aborted — imports failed.")
        sys.exit(1)

    # ── Step 2: Validate SupervisorOutput schema fields ──────────────────────
    print("\n[2] Validating SupervisorOutput schema fields...")
    required_fields = {"intent", "execution_plan", "tools_invoked", "tools_skipped", "reasoning", "results"}
    actual_fields = set(SupervisorOutput.model_fields.keys())
    results.append(check(
        "SupervisorOutput has all required fields",
        required_fields.issubset(actual_fields),
        f"missing: {required_fields - actual_fields}" if not required_fields.issubset(actual_fields) else "OK"
    ))

    # ── Step 3: Run full investigation query ─────────────────────────────────
    print("\n[3] Running full investigation query through supervisor...")
    print("    Query: 'Investigate Account 8000EBD30 for laundering patterns'")

    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()

    try:
        result = run_supervisor(
            "Investigate Account 8000EBD30 for laundering patterns",
            thread_id="smoke-test",
            checkpointer=checkpointer,
        )
    except Exception as exc:
        results.append(check("Supervisor invocation", False, str(exc)))
        print("\nSmoke test aborted — supervisor invocation failed.")
        sys.exit(1)

    results.append(check("Supervisor invocation", True))

    # ── Step 4: Validate structured output fields ────────────────────────────
    print("\n[4] Validating structured output fields...")

    results.append(check("'intent' present", "intent" in result, result.get("intent", "MISSING")))
    results.append(check("'execution_plan' is list", isinstance(result.get("execution_plan"), list)))
    results.append(check("'tools_invoked' is list", isinstance(result.get("tools_invoked"), list)))
    results.append(check("'tools_skipped' is list", isinstance(result.get("tools_skipped"), list)))
    results.append(check("'reasoning' present", bool(result.get("reasoning"))))
    results.append(check("'results' non-empty", bool(result.get("results"))))

    # ── Step 5: Validate multi-turn memory (follow-up query) ─────────────────
    print("\n[5] Testing multi-turn memory with follow-up query...")
    try:
        followup = run_supervisor(
            "Now show me the top 5 receivers for that account",
            thread_id="smoke-test",   # same thread_id = same conversation context
            checkpointer=checkpointer,
        )
        results.append(check(
            "Follow-up query succeeded",
            bool(followup.get("results")),
            "multi-turn memory working" if followup.get("results") else "empty result"
        ))
    except Exception as exc:
        results.append(check("Follow-up query", False, str(exc)))

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Results: {sum(results)}/{len(results)} checks passed")

    print("\n--- Supervisor Output ---")
    print(f"Intent:        {result.get('intent')}")
    print(f"Tools invoked: {result.get('tools_invoked')}")
    print(f"Tools skipped: {result.get('tools_skipped')}")
    print(f"Reasoning:     {result.get('reasoning', '')}")
    print(f"\nResults:\n{result.get('results', '')}")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
