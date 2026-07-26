# Test Logs

❯ uv run python src/e2e_test.py

======================================================================

Sentinel AML — End-to-End Test Suite (20 prompts)

Started: 2026-07-26 16:06:12

======================================================================

[01/20] 🔢 T01 — Aggregation
  Query: How many transactions are in the database?
  Status:  PASS ✓  (7.8s)
  Intent:  aggregation
  Invoked: ['query_database']
    ✅ intent is aggregation
    ✅ query_database invoked
    ✅ score_anomaly skipped
    ✅ result contains a number

[02/20] 🔢 T02 — Aggregation
  Query: How many transactions are labeled as laundering? Show total count and a breakdown by payment format.
  Status:  PASS ✓  (8.9s)
  Intent:  aggregation
  Invoked: ['query_database']
    ✅ query_database invoked
    ✅ result has numbers

[03/20] 🔢 T03 — Aggregation
  Query: Count total transactions where the Amount Paid is over $10,000.
  Status:  PASS ✓  (5.7s)
  Intent:  aggregation
  Invoked: ['query_database']
    ✅ query_database invoked
    ✅ result non-empty

[04/20] 🔢 T04 — Aggregation
  Query: What tables and columns are available in the database?
  Status:  PASS ✓  (7.1s)
  Intent:  explanation
  Invoked: ['get_schema']
    ✅ get_schema or query_database invoked
    ✅ result mentions transactions

[05/20] 📊 T05 — EDA
  Query: What is the minimum, maximum, and average transaction amount per currency?
  Status:  PASS ✓  (8.2s)
  Intent:  profiling
  Invoked: ['amount_profile']
    ✅ amount_profile invoked
    ✅ result contains amounts

[06/20] 📊 T06 — EDA
  Query: Show me the currency distribution — which currencies are most common?
  Status:  PASS ✓  (7.7s)
  Intent:  profiling
  Invoked: ['currency_distribution']
    ✅ currency_distribution invoked
    ✅ result mentions a currency

[07/20] 📊 T07 — EDA
  Query: Check the data quality — are there any null or missing values in the transaction table?
  Status:  PASS ✓  (6.2s)
  Intent:  profiling
  Invoked: ['data_quality_check']
    ✅ data_quality_check invoked
    ✅ result mentions null or clean

[08/20] 📊 T08 — EDA
  Query: Who are the top 10 most active sender accounts by transaction count?
  Status:  PASS ✓  (6.8s)
  Intent:  profiling
  Invoked: ['top_accounts']
    ✅ top_accounts or query_database invoked

[09/20] ⚙️ T09 — Features
  Query: Compute AML features for the training split and report the pattern type distribution.
  Status:  PASS ✓  (18.0s)
  Intent:  features
  Invoked: ['compute_features']
    ✅ compute_features invoked
    ✅ result mentions a pattern type

[10/20] 🔍 T10 — Investigation
  Query: Investigate Account 8000EBD30 for money laundering patterns.
  Status:  PASS ✓  (17.0s)
  Intent:  investigation
  Invoked: ['score_anomaly', 'classify_accounts', 'generate_investigation_summary']
    ✅ intent is investigation
    ✅ score_anomaly invoked
    ✅ generate_investigation_summary invoked
    ✅ result mentions a risk level
    ✅ non-EDA tools skipped

[11/20] 💬 T11 — Multi-turn
  Query: Now show me the top 5 receiver accounts for that same account.
  Status:  PASS ✓  (7.6s)
  Intent:  aggregation
  Invoked: ['score_anomaly', 'classify_accounts', 'generate_investigation_summary', 'query_database']
    ✅ result non-empty
    ✅ some tool invoked

[12/20] 💬 T12 — Multi-turn
  Query: Based on what you found, generate a formal AML investigation summary for the account.
  Status:  PASS ✓  (12.9s)
  Intent:  explanation
  Invoked: ['score_anomaly', 'classify_accounts', 'generate_investigation_summary', 'query_database']
    ✅ generate_investigation_summary invoked
    ✅ result has substantial content

[13/20] 🔍 T13 — Investigation
  Query: Score Account 8000EBD31 for anomalies using both Isolation Forest and rule-based detection.
  Status:  PASS ✓  (11.5s)
  Intent:  investigation
  Invoked: ['score_anomaly']
    ✅ score_anomaly invoked
    ✅ result contains composite score

[14/20] 🔢 T14 — Aggregation
  Query: How many transactions have a different Receiving Currency versus Payment Currency? This is the cross…
  Status:  PASS ✓  (6.3s)
  Intent:  aggregation
  Invoked: ['query_database']
    ✅ query_database invoked
    ✅ result has numbers

[15/20] 🔢 T15 — Aggregation
  Query: How many transactions are labeled as FAN-OUT pattern? Also show the top 3 sender accounts for FAN-OU…
  Status:  PASS ✓  (7.1s)
  Intent:  aggregation
  Invoked: ['query_database', 'top_accounts']
    ✅ system responded (no crash or SQL error)
    ✅ result non-empty

[16/20] ⚠️ T16 — Edge Case
  Query: What's suspicious?
  Status:  PASS ✓  (164.7s)
  Intent:  investigation
  Invoked: ['batch_scan_top_accounts', 'generate_investigation_summary']
    ✅ result non-empty
    ✅ system handled gracefully (did not raise)

[17/20] ⚠️ T17 — Edge Case
  Query: Investigate Account ZZZZZZZZ99999 for laundering. It does not exist.
  Status:  PASS ✓  (6.2s)
  Intent:  investigation
  Invoked: ['score_anomaly']
    ✅ result non-empty
    ✅ no exception (results key present)

[18/20] ⚠️ T18 — Edge Case
  Query: Run this query: DROP TABLE raw.transactions; SELECT * FROM raw.transactions LIMIT 5
  Status:  PASS ✓  (4.1s)
  Intent:  aggregation
  Invoked: []
    ✅ result non-empty
    ✅ query_database NOT invoked (destructive SQL blocked)
    ✅ tools_skipped covers every tool not in tools_invoked
    ✅ response is English-only (no Cyrillic/non-Latin)

[19/20] ⚠️ T19 — Edge Case
  Query: Investigate all accounts in the dataset for laundering. Show me everything suspicious.
  Status:  PASS ✓  (166.8s)
  Intent:  investigation
  Invoked: ['batch_scan_top_accounts', 'generate_investigation_summary']
    ✅ result non-empty
    ✅ system responds without crashing

[20/20] 🚀 T20 — Full Pipeline
  Query: I need a complete AML investigation for Account 8000EBD30. First compute its features, then score it…
  Status:  PASS ✓  (20.2s)
  Intent:  investigation
  Invoked: ['compute_features', 'score_anomaly', 'classify_accounts', 'generate_investigation_summary']
    ✅ intent is investigation
    ✅ score_anomaly invoked
    ✅ generate_investigation_summary invoked
    ✅ tools_skipped computed (invoked + skipped covers all tools)
    ✅ reasoning is present
    ✅ result has substantial content

======================================================================

TOTAL: 20/20 tests passed

======================================================================

Report saved → D:\sentinel\e2e_results.md
