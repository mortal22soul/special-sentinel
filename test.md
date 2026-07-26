❯ uv run pytest tests/ -v
================================================================ test session starts ================================================================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0 -- D:\sentinel\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\sentinel
configfile: pyproject.toml
plugins: anyio-4.14.2, langsmith-0.10.10
collected 42 items

tests/test_features.py::TestRollingFeatures::test_rolling_sum_30d_monotonically_increases PASSED                                               [  2%]
tests/test_features.py::TestRollingFeatures::test_rolling_sum_resets_per_account PASSED                                                        [  4%]
tests/test_features.py::TestRollingFeatures::test_amount_deviation_zero_for_constant_amounts PASSED                                            [  7%]
tests/test_features.py::TestRollingFeatures::test_amount_deviation_large_for_outlier PASSED                                                    [  9%]
tests/test_features.py::TestCrossCurrencyFlag::test_same_currency_not_flagged PASSED                                                           [ 11%]
tests/test_features.py::TestCrossCurrencyFlag::test_different_currencies_flagged PASSED                                                        [ 14%]
tests/test_features.py::TestCrossCurrencyFlag::test_bitcoin_vs_usd_flagged PASSED                                                              [ 16%]
tests/test_features.py::TestFanDetection::test_fan_out_detected_at_threshold PASSED                                                            [ 19%]
tests/test_features.py::TestFanDetection::test_fan_out_below_threshold PASSED                                                                  [ 21%]
tests/test_features.py::TestFanDetection::test_fan_in_detected_at_threshold PASSED                                                             [ 23%]
tests/test_features.py::TestFanDetection::test_fan_in_below_threshold PASSED                                                                   [ 26%]
tests/test_features.py::TestFanDetection::test_fan_out_not_confused_with_fan_in PASSED                                                         [ 28%]
tests/test_features.py::TestCycleDetection::test_simple_cycle_detected PASSED                                                                  [ 30%]
tests/test_features.py::TestCycleDetection::test_no_cycle_in_dag PASSED                                                                        [ 33%]
tests/test_features.py::TestCycleDetection::test_self_loop_short_cycle PASSED                                                                  [ 35%]
tests/test_features.py::TestCycleDetection::test_long_cycle_detected PASSED                                                                    [ 38%]
tests/test_features.py::TestStackDetection::test_stack_detected_with_repeated_relay PASSED                                                     [ 40%]
tests/test_features.py::TestStackDetection::test_stack_not_detected_with_diverse_receivers PASSED                                              [ 42%]
tests/test_features.py::TestStackDetection::test_stack_not_detected_below_min_length PASSED                                                    [ 45%]
tests/test_features.py::TestScatterGatherDetection::test_scatter_gather_detected PASSED                                                        [ 47%]
tests/test_features.py::TestScatterGatherDetection::test_scatter_gather_not_detected_for_pure_fan_out PASSED                                   [ 50%]
tests/test_features.py::TestScatterGatherDetection::test_gather_scatter_detected PASSED                                                        [ 52%]
tests/test_features.py::TestBipartiteDetection::test_bipartite_graph_detected PASSED                                                           [ 54%]
tests/test_features.py::TestBipartiteDetection::test_non_bipartite_graph_not_detected PASSED                                                   [ 57%]
tests/test_features.py::TestGraphBuilder::test_edge_count_matches_unique_pairs PASSED                                                          [ 59%]
tests/test_features.py::TestGraphBuilder::test_node_count_matches_unique_accounts PASSED                                                       [ 61%]
tests/test_routing.py::TestSupervisorOutputSchema::test_all_required_fields_present PASSED                                                     [ 64%]
tests/test_routing.py::TestSupervisorOutputSchema::test_schema_validates_valid_input PASSED                                                    [ 66%]
tests/test_routing.py::TestSupervisorOutputSchema::test_execution_plan_is_list PASSED                                                          [ 69%]
tests/test_routing.py::TestToolRegistry::test_all_expected_tools_registered PASSED                                                             [ 71%]
tests/test_routing.py::TestToolRegistry::test_no_duplicate_tool_names PASSED                                                                   [ 73%]
tests/test_routing.py::TestToolRegistry::test_all_tools_importable PASSED                                                                      [ 76%]
tests/test_routing.py::TestExtractStructuredMetadata::test_parses_json_block_from_ai_message PASSED                                            [ 78%]
tests/test_routing.py::TestExtractStructuredMetadata::test_falls_back_to_tool_message_inference PASSED                                         [ 80%]
tests/test_routing.py::TestExtractStructuredMetadata::test_skipped_tools_are_complement_of_invoked PASSED                                      [ 83%]
tests/test_routing.py::TestExtractStructuredMetadata::test_empty_message_list_returns_defaults PASSED                                          [ 85%]
tests/test_routing.py::TestExtractStructuredMetadata::test_malformed_json_falls_back_gracefully PASSED                                         [ 88%]
tests/test_routing.py::TestIntentValues::test_valid_intents_cover_all_routing_cases PASSED                                                     [ 90%]
tests/test_routing.py::TestRiskThresholds::test_thresholds_consistent_with_plan PASSED                                                         [ 92%]
tests/test_routing.py::TestRiskThresholds::test_escalation_action_present_for_all_tiers PASSED                                                 [ 95%]
tests/test_routing.py::TestAnomalyWeights::test_composite_weights_match_plan PASSED                                                            [ 97%]
tests/test_routing.py::TestAnomalyWeights::test_contamination_matches_plan PASSED                                                              [100%]

================================================================ 42 passed in 9.87s =================================================================

sentinel on  main [!?] is 󰏗 v0.1.0 via  v3.13.7 (sentinel) on   (ap-south-1) took 14s
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
