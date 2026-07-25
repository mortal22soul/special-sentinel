# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] -- 2026-07-25

### Added

- **Unit test suite** (`tests/`): 42 tests across `test_features.py` and `test_routing.py`
  - `test_features.py`: rolling sum math, velocity, amount deviation z-score, all 7 AML
    pattern detection functions (FAN-OUT, FAN-IN, CYCLE, STACK, SCATTER-GATHER,
    GATHER-SCATTER, BIPARTITE), cross-currency flag, graph builder
  - `test_routing.py`: `SupervisorOutput` schema validation, tool registry completeness,
    `_extract_structured_metadata` JSON parsing + fallback, intent value coverage,
    risk threshold constants, anomaly weight constants
- **Streamlit UI** (`src/ui/app.py`): full chat dashboard with:
  - Chat input with sidebar example queries and new-session button
  - Execution trace panel (intent, tools invoked/skipped, reasoning)
  - Colour-coded risk gauge (HIGH 🔴 / MEDIUM 🟡 / LOW 🟢)
  - pyvis network graph for fan-out/cycle account visualisation
  - Altair transaction timeline chart
  - Dedicated Explainability Panel for AML Investigation Summary
  - Multi-turn conversation memory (MemorySaver per session)
- **CLI test scripts**:
  - `src/test_routing.py`: routing correctness checks for 3 query types
  - `src/smoke_test.py`: full E2E pipeline check including multi-turn memory validation
- **`pyvis>=0.3.2`**, **`altair>=5.3.0`**, **`python-dotenv>=1.0.0`**,
  **`pytest>=8.0.0`**, **`streamlit-agraph>=0.0.45`** added to `pyproject.toml`

### Fixed

- `supervisor.py`: broken imports (`query_database`/`get_schema` did not exist in
  `data_query.py`); `run_supervisor()` now returns real structured metadata extracted
  from the LLM response JSON block rather than hardcoded placeholders
- `supervisor.py`: `checkpointer` now passed to `create_agent()` directly so multi-turn
  memory works correctly
- `data_query.py`: renamed `query_data` → `query_database` to match supervisor imports;
  added `get_schema` tool for schema inspection
- `anomaly.py`: fixed double-connection walrus operator bug in `train_isolation_forest()`
  that caused a resource leak and stale dataframe
- `.env`: corrected `AZURE_OPENAI_ENDPOINT` — removed trailing `/openai/v1` suffix that
  caused the SDK to construct duplicate URL paths (404 errors)

### Performance

- Full DuckDB ingest pipeline tested on 5M-row dataset: ~45s on commodity hardware
- Data Query agent: first-run SQL latency ~1.2s (DuckDB in-process, read_only=True)
- Streamlit UI startup: ~3s cold start; chat response ~4-8s depending on tool chain
- Isolation Forest trained on 273,371 samples (100K sample → full account subgraph expansion); saved to `models/isolation_forest.pkl`
- Smoke test: 10/10 checks pass including full investigation chain and multi-turn memory

## [0.9.0] -- 2026-07-25

### Added

- `src/agents/explain.py`: explainability subagent with `generate_investigation_summary` tool
- Rule-based LLM explanation (no SHAP/LIME): deterministic flags fed directly to LLM
- Formal "AML Investigation Summary" with risk verdict, triggered rules, pattern type descriptions, and next steps
- Structured system prompt covers all 7 ground-truth AML pattern types with business meanings
- Temperature=0.3 for natural language generation (higher than other agents)

## [0.8.0] -- 2026-07-25

### Added

- `src/agents/risk.py`: risk classification subagent with `classify_accounts` tool
- Numerical thresholds: LOW < 0.30, MEDIUM < 0.70, HIGH >= 0.70
- Escalation actions: "Auto-Block + Immediate Investigation", "Manual Review Required", "No Action Required"
- Risk-tiered output grouping: all HIGH accounts first, then MEDIUM, then LOW
- Summary statistics: counts and high-risk rate percentage

## [0.7.0] -- 2026-07-25

### Added

- `src/agents/anomaly.py`: anomaly detection subagent with hybrid IF + rule-based scoring
- Isolation Forest (`contamination=0.0015`, `n_estimators=200`) trained on train split
- Rule-based flags: high velocity, amount anomaly, cross-currency risk, known patterns, high volume
- Composite scoring: `0.4 * IF_score + 0.6 * Rule_score`
- Model checkpointing via pickle (`models/isolation_forest.pkl`, `models/scaler.pkl`)
- Unlabeled laundering rows excluded from rules, included in IF validation set

## [0.6.0] -- 2026-07-25

### Added

- `src/agents/features.py`: feature engineering subagent with `compute_features` tool
- Standard features: velocity (30-day txn count), rolling sum of Amount Paid, amount deviation z-score
- 7 ground-truth AML pattern types: FAN-OUT, FAN-IN, CYCLE, STACK, SCATTER-GATHER, GATHER-SCATTER, BIPARTITE, RANDOM
- Cross-currency risk flag (Receiving Currency != Payment Currency)
- Networkx graph detection for CYCLE, SCATTER-GATHER, GATHER-SCATTER, BIPARTITE
- Pattern distribution reporting from labeled transactions

## [0.5.0] -- 2026-07-25

### Added

- `src/agents/eda.py`: 4 profiling tools for the EDA subagent
- `amount_profile`: min/max/mean/median/std dev + laundering count per split
- `currency_distribution`: count and percentage breakdown by currency
- `data_quality_check`: null counts across all transaction columns
- `top_accounts`: most active sender/receiver accounts by volume

## [0.4.0] -- 2026-07-25

### Added

- `src/agents/data_query.py`: LangChain agent with `@tool`-wrapped DuckDB SQL executor
- Read-only query enforcement (blocks INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE)
- Azure OpenAI binding with `gpt-5.4-mini` deployment, temperature=0.0 for deterministic SQL
- System prompt covers table names, quoted-column syntax, and LIMIT guidance
- `HOW_TO_RUN.md` updated with data pipeline steps

## [0.3.0] -- 2026-07-25

### Added

- `src/data/ingest.py`: DuckDB ingestion pipeline with `read_csv_auto`
- Chronological train/val/test split (60/20/20) based on Timestamp ordering
- Split boundaries persisted in `splits.metadata` table for consistent downstream reference
- Indexes on Account columns in both `raw.transactions` and `raw.accounts`
- `data/sentinel.duckdb` (gitignored binary artifact -- 5M rows + accounts + split tables)

### Verified

- All 5,177 laundering rows present across splits (2,298 train / 1,082 val / 1,797 test)
- 518,581 account records loaded
- Class imbalance (0.1%) preserved in each split bucket

## [0.2.0] -- 2026-07-25

### Added

- `src/data/parse_patterns.py`: regex-based laundering block parser for `HI-Small_Patterns.txt`
- Validation: exactly 370 blocks across 7 ground-truth pattern types (FAN-OUT, FAN-IN, CYCLE, STACK, SCATTER-GATHER, GATHER-SCATTER, BIPARTITE, RANDOM)
- Pattern join step: `pattern_labels.csv` (3,209 labeled rows) merged onto full 5M-row `joined_labeled.csv`
- Handles duplicate `Account` column headers and trailing `:` suffix on some pattern markers
- Explicit `UNLABELED` bucket for ~1,968 unlabeled laundering positives (Is Laundering=1, no pattern label)

### Fixed

- Windows console encoding issue with box-drawing characters in print statements
- `CYCLE:` / `GATHER-SCATTER:` trailing colon in pattern names
- Duplicate `Account` column in CSV header breaks DictReader join (switched to index-based csv.reader)

## [0.1.0] -- 2026-07-25

### Added

- Project initialization: `uv`-managed Python project with `pyproject.toml`
- Dependencies: LangChain, LangGraph, DuckDB, scikit-learn, Streamlit, Pydantic
- Git repository with `.gitignore` covering venvs, DuckDB files, ML artifacts, Streamlit cache
- Dataset files staged: `HI-Small_Trans.csv`, `HI-Small_accounts.csv`, `HI-Small_Patterns.txt`
- `HOW_TO_RUN.md` with environment setup, run commands, and troubleshooting
- `implementation_plan.md` with 15 subtasks for the 48-hour hackathon build
- Dataset audit: confirmed 5M rows, 370 labeled laundering blocks, 7 ground-truth pattern types
- Design decisions documented in `CLAUDE.md` (dynamic routing, 100% Python, Streamlit-first)

### Notes

- SQLGlot was removed from the tech stack (no AST validation layer)
- Cross-Currency Risk replaces the originally planned "Country Risk" typology (no country column in dataset)
- ~31% of laundering rows lack pattern labels; Isolation Forest validates independently on unlabeled positives
