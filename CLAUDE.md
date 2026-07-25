# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

VIT Campus Hackathon Round 1 (48 hours) — Problem Statement 1: AI-Powered Suspicious Activity Detection (AML). The team chose PS1 over PS2 because the required dynamic supervisor-routing pattern matches an already-debugged LangGraph multi-agent system, giving a time advantage under 48-hour pressure.

## Tech Stack & Constraints

- **Language:** 100% Python (no JS/TypeScript)
- **Package Manager:** `uv`
- **LLM:** Azure OpenAI `GPT-5.4-mini` via AI Foundry (`langchain-openai`)
- **Orchestration:** LangChain `create_agent` with `@tool`-wrapped Subagents (supervisor pattern)
- **Data Layer:** DuckDB (in-process SQL)
- **Frontend:** Streamlit (primary UI from the start, replacing the originally planned API-only approach)
- **ML:** scikit-learn Isolation Forest + rule-based hybrid
- **Explainability:** Rule-based LLM explanation (deterministic rule flags fed to LLM, NOT SHAP/LIME)

## Planned Directory Structure

```text
src/
  data/
    parse_patterns.py    — regex parsing of HI-Small_Patterns.txt laundering blocks
    ingest.py            — DuckDB CSV ingestion via read_csv_auto
  agents/
    data_query.py        — SQL generation + DuckDB execution tool
    eda.py               — profiling queries (amounts, currency, volume)
    features.py          — velocity, rolling sums, 7 ground-truth AML pattern features + cross-currency risk
    anomaly.py           — Isolation Forest + rule-based hybrid scoring
    risk.py              — Low/Medium/High threshold classification
    explain.py           — plain-English AML investigation summaries
  supervisor.py          — orchestrator: structured output schema, Azure OpenAI config, routing logic
  ui/app.py              — Streamlit chat + dashboard (network graphs, risk gauges, explainability panel)
tests/
  test_routing.py        — supervisor intent/routing validation
  test_features.py       — rolling sum math and 7 ground-truth pattern type validation
```

## Key Design Decisions

- **Dynamic routing is the critical differentiator.** The supervisor must parse natural language queries, detect intent/filters/entities/pattern types, and construct an execution plan — invoking only necessary tools. Hardcoded if/else routing will fail judging criteria.
- **Subagent tools are wrapped with LangChain `@tool`** and bound to the Azure OpenAI model via `create_agent`.
- **Structured output schema** (Pydantic): `intent`, `execution_plan`, `tools_invoked`, `tools_skipped`, `reasoning`, `results`. Every response must include `tools_skipped` to demonstrate dynamic routing.
- **Fallback:** Pure aggregation queries (e.g., "count transactions over $10,000") bypass ML tools and go straight to Data Query agent.
- **Data:** IBM HI-Small dataset from Kaggle (`ealtman2019/ibm-transactions-for-anti-money-laundering-aml`). Pattern labels from `HI-Small_Patterns.txt` are joined to transaction rows. Downsampled to ~200–500K rows for live demo; full dataset kept for offline fitting.

## How to Run (once implemented)

```bash
uv sync

# Run the Streamlit UI
uv run streamlit run src/ui/app.py

# Run tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_routing.py -v
```

## Environment Variables

```text
AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT_NAME  (optional override, defaults to GPT-5.4-mini)
```

## Dataset Files (already in repo)

- `data/HI-Small_Trans.csv` — transaction records (~5M rows)
- `data/HI-Small_accounts.csv` — account metadata
- `data/HI-Small_Patterns.txt` — laundering pattern labels (BEGIN/END blocks)
- `data/AML-Data-Public.zip` — additional reference data

## AML Typologies (7 ground-truth pattern types from HI-Small_Patterns.txt)

FAN-OUT, FAN-IN, CYCLE, STACK, SCATTER-GATHER, GATHER-SCATTER, BIPARTITE, RANDOM.

Plus one additional computable feature: Cross-Currency Risk (flag when Receiving Currency ≠ Payment Currency).

## Data Constraints (from actual dataset audit)

- **No country column** — drop "Country Risk" typology, use cross-currency flag instead
- **5,177 laundering rows** in CSV, but Patterns.txt labels only ~3,577 (~69%). The remaining ~1,600 unlabeled positives validate Isolation Forest independently
- **0.1% class imbalance** — IsolationForest must use contamination=0.0015
- **Graph patterns (CYCLE, SCATTER-GATHER)** should be detected in Python (Pandas/networkx on filtered subgraphs), not pure SQL recursive CTEs

## Important Constraints

- No references to "SG", "Societe Generale", "SocGen", "SGGSC" anywhere in the repo
- README must include: problem statement, dataset citation, solution approach, tech stack, setup, usage, and all external tools disclosed
- All work must be original and created during the hackathon window
- Simplicity, explainability, and working end-to-end demo > model complexity
