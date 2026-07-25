# Sentinel -- AI-Powered AML Detection

Sentinel is an AI-powered Anti-Money Laundering (AML) detection system built for the VIT Campus Hackathon. The architecture is a 100% Python LangChain Subagent system in which a supervisor routes natural-language investigation queries to specialized subagents.

## Problem Statement (PS1)

Suspicious Activity Detection (AML) -- given the IBM HI-Small transaction dataset, surface accounts whose transfer graph matches known money-laundering typologies, explain why each account is flagged, and present the evidence through an interactive UI.

## Dataset

**Source:** [IBM Transactions for Anti Money Laundering (AML)](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml) (`ealtman2019`)

- 5,078,346 transactions across 518,582 accounts
- 370 labeled laundering blocks covering 7 ground-truth pattern types:
  FAN-OUT, FAN-IN, CYCLE, STACK, SCATTER-GATHER, GATHER-SCATTER, BIPARTITE, RANDOM
- 5,177 laundering rows total in the CSV; ~3,577 are labeled, ~1,600 are unlabeled positives used to validate the Isolation Forest component independently
- Class imbalance: 0.1% (5,073,168 benign vs 5,177 laundering)

## Solution Approach

A **LangChain supervisor** dynamically routes each user query to one or more specialized subagents. Pure aggregation queries (e.g., "count transactions over $10,000") skip the ML pipeline and go straight to the Data Query agent. Investigation queries invoke a hybrid rule + Isolation Forest scorer and produce a plain-English AML investigation summary.

Subagents:

1. **Data Query** -- DuckDB SQL execution
2. **EDA** -- distribution/aggregation profiling
3. **Features** -- velocity, rolling sums, 7 graph-pattern features + cross-currency risk
4. **Anomaly** -- Isolation Forest (contamination=0.0015) + rule-based hybrid scoring
5. **Risk** -- Low / Medium / High classification
6. **Explain** -- deterministic rule flags translated into plain English

## Tech Stack

- **Language:** Python 3.10+
- **Package Manager:** uv
- **Orchestration:** LangChain `create_agent` with `@tool`-wrapped subagents
- **LLM:** Azure OpenAI `gpt-5.4-mini` via AI Foundry (`langchain-openai`)
- **Data Layer:** DuckDB (in-process SQL)
- **ML:** scikit-learn Isolation Forest + rule-based hybrid
- **Frontend:** Streamlit (chat + risk dashboard + explainability panel)
- **Visualization:** pyvis (network graphs), Altair (Streamlit-native charts)

External tools used: DuckDB, scikit-learn, LangChain, LangGraph, Streamlit, pyvis, Azure OpenAI.

## Setup

See [HOW_TO_RUN.md](HOW_TO_RUN.md) for full setup instructions.

```bash
uv sync
cp .env.example .env  # fill in Azure OpenAI credentials
```

## Usage

```bash
# Step 1: Parse pattern labels (once)
uv run python src/data/parse_patterns.py

# Step 2: Ingest into DuckDB (once, ~45s)
uv run python src/data/ingest.py

# Step 3: Launch the Streamlit UI
uv run streamlit run src/ui/app.py

# Run the full unit test suite (no credentials needed)
uv run pytest tests/ -v

# Run the E2E smoke test (needs Azure credentials + DuckDB)
uv run python src/smoke_test.py
```

Once running, open `http://localhost:8501` and try queries like:

- "Investigate Account 8000EBD30 for layering patterns over the last 30 days"
- "Count total transactions over $10,000"
- "Find all FAN-OUT accounts in the last week"

## Project Structure

```text
src/
  data/          -- pattern parsing, DuckDB ingestion
  agents/        -- 6 subagent tools
  supervisor.py  -- orchestrator
  ui/app.py      -- Streamlit frontend
tests/           -- pytest suite
data/            -- CSV inputs (not committed)
```
