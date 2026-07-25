"""CLI routing test for the Sentinel AML supervisor.

Tests that the supervisor correctly routes different query types to the
expected tool set without needing a live Azure OpenAI connection (uses
the routing metadata JSON block extracted from the response).

Usage
-----
    uv run python src/test_routing.py

Requires:
    - AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in .env or shell
    - data/sentinel.duckdb ingested (run src/data/ingest.py first)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env before imports that need env vars
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure src/ is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.supervisor import run_supervisor
from langgraph.checkpoint.memory import MemorySaver


# ── Test cases ───────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Pure aggregation query",
        "query": "How many transactions are in the database?",
        "expected_intent": "aggregation",
        "must_invoke": ["query_database"],
        "must_skip": ["score_anomaly", "classify_accounts", "generate_investigation_summary"],
    },
    {
        "name": "EDA profiling query",
        "query": "What is the average transaction amount and currency distribution?",
        "expected_intent": "profiling",
        "must_invoke": ["amount_profile", "currency_distribution"],
        "must_skip": ["score_anomaly"],
    },
    {
        "name": "Investigation query",
        "query": "Investigate Account 8000EBD30 for laundering patterns",
        "expected_intent": "investigation",
        "must_invoke": ["score_anomaly", "generate_investigation_summary"],
        "must_skip": [],
    },
]


def run_test(case: dict, checkpointer: MemorySaver, thread_id: str) -> bool:
    """Run a single routing test. Returns True if passed."""
    print(f"\n{'='*60}")
    print(f"TEST: {case['name']}")
    print(f"QUERY: {case['query']}")
    print("─" * 60)

    try:
        result = run_supervisor(case["query"], thread_id=thread_id, checkpointer=checkpointer)
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return False

    intent = result.get("intent", "unknown")
    invoked = set(result.get("tools_invoked", []))
    skipped = set(result.get("tools_skipped", []))
    reasoning = result.get("reasoning", "")

    print(f"  Intent:        {intent}")
    print(f"  Tools invoked: {sorted(invoked)}")
    print(f"  Tools skipped: {sorted(skipped)}")
    print(f"  Reasoning:     {reasoning[:200]}")
    print(f"  Results preview: {result.get('results', '')[:300]}")

    passed = True

    for tool in case["must_invoke"]:
        if tool not in invoked:
            print(f"  FAIL: expected '{tool}' to be invoked, but it wasn't")
            passed = False

    for tool in case["must_skip"]:
        if tool in invoked:
            print(f"  FAIL: expected '{tool}' to be skipped, but it was invoked")
            passed = False

    if passed:
        print("  PASS ✓")
    return passed


def main() -> None:
    print("Sentinel AML — Routing Tests")
    print("=" * 60)

    checkpointer = MemorySaver()
    results = []

    for i, case in enumerate(TEST_CASES):
        thread_id = f"test-thread-{i}"
        passed = run_test(case, checkpointer, thread_id)
        results.append(passed)

    print(f"\n{'='*60}")
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
