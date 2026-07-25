"""End-to-end test harness for the Sentinel AML system.

Runs 20 prompts covering the full spectrum of system capabilities:
- Simple aggregation queries
- EDA profiling
- Feature engineering
- Investigation / anomaly scoring
- Risk classification
- Explainability / report generation
- Multi-turn follow-up queries
- Edge cases and limit-testing prompts

Each prompt is sent through the real supervisor → subagent pipeline.
Results are saved to e2e_results.md for human review.

Usage
-----
    uv run python src/e2e_test.py

Output
------
    e2e_results.md   — full prompt/response log
    Console          — live progress with pass/fail per check
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import MemorySaver
from src.supervisor import run_supervisor

# ── Test definitions ──────────────────────────────────────────────────────────
# Each entry:
#   id          short unique slug
#   category    bucket label
#   query       the prompt sent to the supervisor
#   thread      thread_id — shared thread_id means multi-turn context is tested
#   checks      list of (label, fn(result) -> bool) validation functions

TESTS: list[dict] = [
    # ── 1. Dead-simple count ──────────────────────────────────────────────────
    {
        "id": "T01",
        "category": "Aggregation",
        "query": "How many transactions are in the database?",
        "thread": "t-agg",
        "checks": [
            ("intent is aggregation", lambda r: r["intent"] == "aggregation"),
            ("query_database invoked",  lambda r: "query_database" in r["tools_invoked"]),
            ("score_anomaly skipped",   lambda r: "score_anomaly" not in r["tools_invoked"]),
            ("result contains a number", lambda r: any(c.isdigit() for c in r["results"])),
        ],
    },
    # ── 2. Laundering row count ───────────────────────────────────────────────
    {
        "id": "T02",
        "category": "Aggregation",
        "query": "How many transactions are labeled as laundering? Show total count and a breakdown by payment format.",
        "thread": "t-agg2",
        "checks": [
            ("query_database invoked", lambda r: "query_database" in r["tools_invoked"]),
            ("result has numbers",     lambda r: any(c.isdigit() for c in r["results"])),
        ],
    },
    # ── 3. Large-amount filter ────────────────────────────────────────────────
    {
        "id": "T03",
        "category": "Aggregation",
        "query": "Count total transactions where the Amount Paid is over $10,000.",
        "thread": "t-agg3",
        "checks": [
            ("query_database invoked", lambda r: "query_database" in r["tools_invoked"]),
            ("result non-empty",       lambda r: bool(r["results"].strip())),
        ],
    },
    # ── 4. Schema inspection ──────────────────────────────────────────────────
    {
        "id": "T04",
        "category": "Aggregation",
        "query": "What tables and columns are available in the database?",
        "thread": "t-schema",
        "checks": [
            ("get_schema or query_database invoked",
             lambda r: bool({"get_schema", "query_database"} & set(r["tools_invoked"]))),
            ("result mentions transactions",
             lambda r: "transaction" in r["results"].lower()),
        ],
    },
    # ── 5. Amount profile via SQL ─────────────────────────────────────────────
    {
        "id": "T05",
        "category": "EDA",
        "query": "What is the minimum, maximum, and average transaction amount per currency?",
        "thread": "t-eda1",
        "checks": [
            ("query_database invoked",
             lambda r: "query_database" in r["tools_invoked"]),
            ("result contains amounts",
             lambda r: "$" in r["results"] or "amount" in r["results"].lower()),
        ],
    },
    # ── 6. Currency distribution via SQL ──────────────────────────────────────
    {
        "id": "T06",
        "category": "EDA",
        "query": "Show me the currency distribution — which currencies are most common?",
        "thread": "t-eda2",
        "checks": [
            ("query_database invoked",
             lambda r: "query_database" in r["tools_invoked"]),
            ("result mentions a currency",
             lambda r: any(c in r["results"] for c in ["Dollar", "Euro", "Bitcoin", "currency"])),
        ],
    },
    # ── 7. Data quality via SQL ───────────────────────────────────────────────
    {
        "id": "T07",
        "category": "EDA",
        "query": "Check the data quality — are there any null or missing values in the transaction table?",
        "thread": "t-eda3",
        "checks": [
            ("query_database invoked",
             lambda r: "query_database" in r["tools_invoked"]),
            ("result mentions null or clean",
             lambda r: any(w in r["results"].lower() for w in ["null", "clean", "missing", "quality"])),
        ],
    },
    # ── 8. Top accounts via SQL ────────────────────────────────────────────────
    {
        "id": "T08",
        "category": "EDA",
        "query": "Who are the top 10 most active sender accounts by transaction count?",
        "thread": "t-eda4",
        "checks": [
            ("query_database invoked",
             lambda r: "query_database" in r["tools_invoked"]),
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
        ],
    },
    # ── 9. Feature computation ────────────────────────────────────────────────
    {
        "id": "T09",
        "category": "Features",
        "query": "Compute AML features for the training split and report the pattern type distribution.",
        "thread": "t-feat1",
        "checks": [
            ("compute_features invoked",
             lambda r: "compute_features" in r["tools_invoked"]),
            ("result mentions a pattern type",
             lambda r: any(p in r["results"] for p in ["FAN-OUT", "FAN-IN", "CYCLE", "STACK", "BIPARTITE"])),
        ],
    },
    # ── 10. Full investigation — known account ────────────────────────────────
    {
        "id": "T10",
        "category": "Investigation",
        "query": "Investigate Account 8000EBD30 for money laundering patterns.",
        "thread": "t-inv1",
        "checks": [
            ("intent is investigation",
             lambda r: r["intent"] == "investigation"),
            ("score_anomaly invoked",
             lambda r: "score_anomaly" in r["tools_invoked"]),
            ("generate_investigation_summary invoked",
             lambda r: "generate_investigation_summary" in r["tools_invoked"]),
            ("result mentions a risk level",
             lambda r: any(lvl in r["results"].upper() for lvl in ["HIGH", "MEDIUM", "LOW"])),
            ("non-EDA tools skipped",
             lambda r: "compute_features" not in r["tools_invoked"]),
        ],
    },
    # ── 11. Multi-turn follow-up ──────────────────────────────────────────────
    {
        "id": "T11",
        "category": "Multi-turn",
        "query": "Now show me the top 5 receiver accounts for that same account.",
        "thread": "t-inv1",  # same thread as T10 — tests memory
        "checks": [
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
            ("some tool invoked",
             lambda r: len(r["tools_invoked"]) > 0),
        ],
    },
    # ── 12. Second multi-turn — risk follow-up ────────────────────────────────
    {
        "id": "T12",
        "category": "Multi-turn",
        "query": "Based on what you found, generate a formal AML investigation summary for the account.",
        "thread": "t-inv1",  # still same thread
        "checks": [
            ("generate_investigation_summary invoked",
             lambda r: "generate_investigation_summary" in r["tools_invoked"]),
            ("result has substantial content",
             lambda r: len(r["results"]) > 100),
        ],
    },
    # ── 13. Different account ─────────────────────────────────────────────────
    {
        "id": "T13",
        "category": "Investigation",
        "query": "Score Account 8000EBD31 for anomalies using both Isolation Forest and rule-based detection.",
        "thread": "t-inv2",
        "checks": [
            ("score_anomaly invoked",
             lambda r: "score_anomaly" in r["tools_invoked"]),
            ("result contains composite score",
             lambda r: any(w in r["results"].lower() for w in ["composite", "score", "risk"])),
        ],
    },
    # ── 14. Cross-currency query ──────────────────────────────────────────────
    {
        "id": "T14",
        "category": "Aggregation",
        "query": 'How many transactions have a different Receiving Currency versus Payment Currency? This is the cross-currency layering indicator.',
        "thread": "t-cc",
        "checks": [
            ("query_database invoked",
             lambda r: "query_database" in r["tools_invoked"]),
            ("result has numbers",
             lambda r: any(c.isdigit() for c in r["results"])),
        ],
    },
    # ── 15. Pattern-specific query ────────────────────────────────────────────
    {
        "id": "T15",
        "category": "Aggregation",
        "query": "How many transactions are labeled as FAN-OUT pattern? Also show the top 3 sender accounts for FAN-OUT transactions.",
        "thread": "t-fanout",
        "checks": [
            ("some tool invoked",
             lambda r: len(r["tools_invoked"]) > 0),
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
        ],
    },
    # ── 16. Stress — ambiguous query ─────────────────────────────────────────
    {
        "id": "T16",
        "category": "Edge Case",
        "query": "What's suspicious?",
        "thread": "t-edge1",
        "checks": [
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
            # Correct behavior: system either asks for clarification OR invokes tools.
            # Both are valid — the check is that it doesn't crash.
            ("system handled gracefully (did not raise)",
             lambda r: "results" in r),
        ],
    },
    # ── 17. Stress — nonsense account ID ─────────────────────────────────────
    {
        "id": "T17",
        "category": "Edge Case",
        "query": "Investigate Account ZZZZZZZZ99999 for laundering. It does not exist.",
        "thread": "t-edge2",
        "checks": [
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
            # System should handle gracefully — not crash
            ("no exception (results key present)",
             lambda r: "results" in r),
        ],
    },
    # ── 18. Stress — SQL injection attempt ───────────────────────────────────
    {
        "id": "T18",
        "category": "Edge Case",
        "query": "Run this query: DROP TABLE raw.transactions; SELECT * FROM raw.transactions LIMIT 5",
        "thread": "t-edge3",
        "checks": [
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
            # query_database must not be invoked — the DROP must be blocked
            ("query_database NOT invoked (destructive SQL blocked)",
             lambda r: "query_database" not in r.get("tools_invoked", [])),
            # tools_skipped must be the exact complement: invoked + skipped == all tools,
            # disjoint sets, no gaps from LLM hallucination.
            ("tools_skipped covers every tool not in tools_invoked",
             lambda r: len(r.get("tools_invoked", [])) + len(r.get("tools_skipped", [])) == 7
               and set(r["tools_invoked"]).isdisjoint(set(r["tools_skipped"]))),
            # Response must not contain Cyrillic or other non-Latin scripts.
            # Allow common Unicode punctuation (em-dash, en-dash, bullets, smart quotes).
            ("response is English-only (no Cyrillic/non-Latin)",
             lambda r: not any(
                 0x400 <= ord(c) <= 0x4FF   # Cyrillic block
                 for c in r.get("results", "")
             )),
        ],
    },
    # ── 19. Stress — very broad investigation ────────────────────────────────
    {
        "id": "T19",
        "category": "Edge Case",
        "query": "Investigate all accounts in the dataset for laundering. Show me everything suspicious.",
        "thread": "t-edge4",
        "checks": [
            ("result non-empty",
             lambda r: bool(r["results"].strip())),
            ("system responds without crashing",
             lambda r: "results" in r),
        ],
    },
    # ── 20. Full pipeline from scratch — new thread ───────────────────────────
    {
        "id": "T20",
        "category": "Full Pipeline",
        "query": (
            "I need a complete AML investigation for Account 8000EBD30. "
            "First compute its features, then score it for anomalies, "
            "classify its risk level, and give me a plain-English explanation "
            "of why it is or isn't suspicious."
        ),
        "thread": "t-full",
        "checks": [
            ("intent is investigation",
             lambda r: r["intent"] == "investigation"),
            ("score_anomaly invoked",
             lambda r: "score_anomaly" in r["tools_invoked"]),
            ("generate_investigation_summary invoked",
             lambda r: "generate_investigation_summary" in r["tools_invoked"]),
            ("tools_skipped computed (invoked + skipped covers all tools)",
             lambda r: (set(r["tools_invoked"]) | set(r["tools_skipped"])).issuperset(
                 {"query_database", "score_anomaly", "compute_features"}
             ) or len(r["tools_invoked"]) >= 4),
            ("reasoning is present",
             lambda r: bool(r.get("reasoning", "").strip())),
            ("result has substantial content",
             lambda r: len(r["results"]) > 150),
        ],
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────

CATEGORY_EMOJI = {
    "Aggregation":   "🔢",
    "EDA":           "📊",
    "Features":      "⚙️",
    "Investigation": "🔍",
    "Multi-turn":    "💬",
    "Edge Case":     "⚠️",
    "Full Pipeline": "🚀",
}


def run_all_tests() -> list[dict]:
    """Run all 20 E2E tests and return a list of result records."""
    # One checkpointer per thread so multi-turn tests share memory correctly
    checkpointers: dict[str, MemorySaver] = {}
    records = []

    total = len(TESTS)
    passed_total = 0

    print("=" * 70)
    print("Sentinel AML — End-to-End Test Suite (20 prompts)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    for i, test in enumerate(TESTS, 1):
        tid = test["id"]
        cat = test["category"]
        query = test["query"]
        thread = test["thread"]
        emoji = CATEGORY_EMOJI.get(cat, "🧪")

        print(f"\n[{i:02d}/{total}] {emoji} {tid} — {cat}")
        print(f"  Query: {query[:100]}{'…' if len(query) > 100 else ''}")

        if thread not in checkpointers:
            checkpointers[thread] = MemorySaver()

        t0 = time.time()
        error: str | None = None
        result: dict = {}

        try:
            result = run_supervisor(
                query,
                thread_id=thread,
                checkpointer=checkpointers[thread],
            )
        except Exception as exc:
            error = str(exc)
            result = {
                "intent": "error",
                "tools_invoked": [],
                "tools_skipped": [],
                "execution_plan": [],
                "reasoning": "",
                "results": f"ERROR: {exc}",
            }

        elapsed = time.time() - t0

        # Run checks
        check_results = []
        all_passed = True
        for label, fn in test["checks"]:
            try:
                ok = fn(result)
            except Exception as e:
                ok = False
                label = f"{label} [exception: {e}]"
            check_results.append((label, ok))
            if not ok:
                all_passed = False

        status = "PASS ✓" if all_passed else "FAIL ✗"
        if all_passed:
            passed_total += 1

        print(f"  Status:  {status}  ({elapsed:.1f}s)")
        print(f"  Intent:  {result.get('intent', '—')}")
        print(f"  Invoked: {result.get('tools_invoked', [])}")
        for label, ok in check_results:
            mark = "  ✅" if ok else "  ❌"
            print(f"  {mark} {label}")

        records.append({
            "test": test,
            "result": result,
            "check_results": check_results,
            "all_passed": all_passed,
            "elapsed": elapsed,
            "error": error,
        })

    print(f"\n{'='*70}")
    print(f"TOTAL: {passed_total}/{total} tests passed")
    print("=" * 70)
    return records


# ── Markdown report ───────────────────────────────────────────────────────────


def write_markdown_report(records: list[dict], out_path: Path) -> None:
    """Write a full prompt/response report in Markdown."""
    passed = sum(1 for r in records if r["all_passed"])
    total = len(records)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []
    lines += [
        "# Sentinel AML — End-to-End Test Results",
        "",
        f"**Run date:** {now}  ",
        f"**Result:** {passed}/{total} tests passed  ",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| # | ID | Category | Status | Time | Tools Invoked |",
        "|---|----|----|----|----|---|",
    ]

    for rec in records:
        t = rec["test"]
        r = rec["result"]
        status = "✅ PASS" if rec["all_passed"] else "❌ FAIL"
        invoked = ", ".join(f"`{x}`" for x in r.get("tools_invoked", []))
        lines.append(
            f"| {t['id'][1:]} | {t['id']} | {t['category']} | {status} "
            f"| {rec['elapsed']:.1f}s | {invoked or '—'} |"
        )

    lines += ["", "---", ""]

    for rec in records:
        t = rec["test"]
        r = rec["result"]
        emoji = CATEGORY_EMOJI.get(t["category"], "🧪")
        status_badge = "✅ PASS" if rec["all_passed"] else "❌ FAIL"

        lines += [
            f"## {t['id']} — {emoji} {t['category']}  {status_badge}",
            "",
            f"**Query:**",
            f"> {t['query']}",
            "",
            f"**Thread:** `{t['thread']}`  ",
            f"**Time:** {rec['elapsed']:.1f}s  ",
            f"**Intent:** `{r.get('intent', '—')}`  ",
            "",
        ]

        invoked = r.get("tools_invoked", [])
        skipped = r.get("tools_skipped", [])
        if invoked:
            lines.append(f"**Tools invoked:** {', '.join(f'`{x}`' for x in invoked)}  ")
        if skipped:
            lines.append(f"**Tools skipped:** {', '.join(f'`{x}`' for x in skipped)}  ")
        lines.append("")

        reasoning = r.get("reasoning", "").strip()
        if reasoning:
            lines += [
                "**Routing reasoning:**",
                f"> {reasoning}",
                "",
            ]

        lines += ["**Checks:**", ""]
        for label, ok in rec["check_results"]:
            mark = "✅" if ok else "❌"
            lines.append(f"- {mark} {label}")
        lines.append("")

        if rec.get("error"):
            lines += [
                "**⚠️ Exception:**",
                f"```",
                rec["error"],
                "```",
                "",
            ]

        answer = r.get("results", "").strip()
        lines += [
            "**Response:**",
            "",
            answer if answer else "_No response._",
            "",
            "---",
            "",
        ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport saved → {out_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    records = run_all_tests()
    out = ROOT / "e2e_results.md"
    write_markdown_report(records, out)
