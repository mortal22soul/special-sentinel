# Sentinel AML — End-to-End Test Results

**Run date:** 2026-07-26 16:14:33  
**Result:** 20/20 tests passed  

---

## Summary Table

| # | ID | Category | Status | Time | Tools Invoked |
|---|----|----|----|----|---|
| 01 | T01 | Aggregation | ✅ PASS | 7.8s | `query_database` |
| 02 | T02 | Aggregation | ✅ PASS | 8.9s | `query_database` |
| 03 | T03 | Aggregation | ✅ PASS | 5.7s | `query_database` |
| 04 | T04 | Aggregation | ✅ PASS | 7.1s | `get_schema` |
| 05 | T05 | EDA | ✅ PASS | 8.2s | `amount_profile` |
| 06 | T06 | EDA | ✅ PASS | 7.7s | `currency_distribution` |
| 07 | T07 | EDA | ✅ PASS | 6.2s | `data_quality_check` |
| 08 | T08 | EDA | ✅ PASS | 6.8s | `top_accounts` |
| 09 | T09 | Features | ✅ PASS | 18.0s | `compute_features` |
| 10 | T10 | Investigation | ✅ PASS | 17.0s | `score_anomaly`, `classify_accounts`, `generate_investigation_summary` |
| 11 | T11 | Multi-turn | ✅ PASS | 7.6s | `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database` |
| 12 | T12 | Multi-turn | ✅ PASS | 12.9s | `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database` |
| 13 | T13 | Investigation | ✅ PASS | 11.5s | `score_anomaly` |
| 14 | T14 | Aggregation | ✅ PASS | 6.3s | `query_database` |
| 15 | T15 | Aggregation | ✅ PASS | 7.1s | `query_database`, `top_accounts` |
| 16 | T16 | Edge Case | ✅ PASS | 164.7s | `batch_scan_top_accounts`, `generate_investigation_summary` |
| 17 | T17 | Edge Case | ✅ PASS | 6.2s | `score_anomaly` |
| 18 | T18 | Edge Case | ✅ PASS | 4.1s | — |
| 19 | T19 | Edge Case | ✅ PASS | 166.8s | `batch_scan_top_accounts`, `generate_investigation_summary` |
| 20 | T20 | Full Pipeline | ✅ PASS | 20.2s | `compute_features`, `score_anomaly`, `classify_accounts`, `generate_investigation_summary` |

---

## T01 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions are in the database?

**Thread:** `t-agg`  
**Time:** 7.8s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a simple read-only aggregation request asking for the total number of rows in the transactions table. A direct SQL COUNT(*) query is the most appropriate and efficient tool; profiling, investigation, and feature/scoring tools were unnecessary.

**Checks:**

- ✅ intent is aggregation
- ✅ query_database invoked
- ✅ score_anomaly skipped
- ✅ result contains a number

**Response:**

There are **5,078,345 transactions** in the database.

---

## T02 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions are labeled as laundering? Show total count and a breakdown by payment format.

**Thread:** `t-agg2`  
**Time:** 8.9s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation question asking for a total count and a categorical breakdown by payment format. query_database is the appropriate tool because the structured EDA tools do not cover laundering-label counts by payment format.

**Checks:**

- ✅ query_database invoked
- ✅ result has numbers

**Response:**

There are **5,177 laundering-labeled transactions** in total.

### Breakdown by payment format
- **ACH**: 4,483
- **Cheque**: 324
- **Credit Card**: 206
- **Cash**: 108
- **Bitcoin**: 56

If you want, I can also provide the **percentage breakdown** by payment format.

---

## T03 — 🔢 Aggregation  ✅ PASS

**Query:**
> Count total transactions where the Amount Paid is over $10,000.

**Thread:** `t-agg3`  
**Time:** 5.7s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a simple read-only aggregation query asking for a count above a threshold, which is best handled directly with SQL. Profiling and investigation tools were unnecessary because the user did not ask for distributions, account-level analysis, or anomaly detection.

**Checks:**

- ✅ query_database invoked
- ✅ result non-empty

**Response:**

There are **1,370,620** transactions where **"Amount Paid" > 10,000**.

---

## T04 — 🔢 Aggregation  ✅ PASS

**Query:**
> What tables and columns are available in the database?

**Thread:** `t-schema`  
**Time:** 7.1s  
**Intent:** `explanation`  

**Tools invoked:** `get_schema`  
**Tools skipped:** `query_database`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The user asked for the database structure, so the schema inspection tool was the correct choice. No profiling, aggregation, or AML investigation tools were needed because the request was purely about available tables and columns.

**Checks:**

- ✅ get_schema or query_database invoked
- ✅ result mentions transactions

**Response:**

Here are the available tables and columns in the database:

### `raw`
- **accounts**
  - `Bank Name` (VARCHAR)
  - `Bank ID` (BIGINT)
  - `Account Number` (VARCHAR)
  - `Entity ID` (VARCHAR)
  - `Entity Name` (VARCHAR)

- **transactions**
  - `Timestamp` (TIMESTAMP)
  - `From Bank` (VARCHAR)
  - `Account` (VARCHAR)
  - `To Bank` (VARCHAR)
  - `Account.1` (VARCHAR)
  - `Amount Received` (DOUBLE)
  - `Receiving Currency` (VARCHAR)
  - `Amount Paid` (DOUBLE)
  - `Payment Currency` (VARCHAR)
  - `Payment Format` (VARCHAR)
  - `Is Laundering` (BIGINT)
  - `pattern_type` (VARCHAR)

### `splits`
- **metadata**
  - `train_row_cutoff` (INTEGER)
  - `val_row_cutoff` (INTEGER)
  - `train_start_ts` (VARCHAR)
  - `test_end_ts` (VARCHAR)
  - `train_ratio` (DECIMAL(2,1))
  - `val_ratio` (DECIMAL(2,1))
  - `test_ratio` (DECIMAL(2,1))

- **train**
  - `Timestamp` (TIMESTAMP)
  - `From Bank` (VARCHAR)
  - `Account` (VARCHAR)
  - `To Bank` (VARCHAR)
  - `Account.1` (VARCHAR)
  - `Amount Received` (DOUBLE)
  - `Receiving Currency` (VARCHAR)
  - `Amount Paid` (DOUBLE)
  - `Payment Currency` (VARCHAR)
  - `Payment Format` (VARCHAR)
  - `Is Laundering` (BIGINT)
  - `pattern_type` (VARCHAR)

- **validation**
  - same columns as `train`

- **test**
  - same columns as `train`

If you want, I can also summarize which tables are best for profiling vs AML investigation.

---

## T05 — 📊 EDA  ✅ PASS

**Query:**
> What is the minimum, maximum, and average transaction amount per currency?

**Thread:** `t-eda1`  
**Time:** 8.2s  
**Intent:** `profiling`  

**Tools invoked:** `amount_profile`  
**Tools skipped:** `query_database`, `get_schema`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a transaction amount profiling request asking for min, max, and average per currency. The structured amount_profile tool is the correct choice because it returns per-currency native-currency statistics with the proper caveat about no FX normalisation. Other tools were unnecessary because this is not a custom aggregation, investigation, or anomaly-detection task.

**Checks:**

- ✅ amount_profile invoked
- ✅ result contains amounts

**Response:**

Here are the minimum, maximum, and average transaction amounts per currency in the full dataset.

Note: amounts are reported in native currency units, so cross-currency comparisons can be misleading.

| Currency | Min | Max | Average |
|---|---:|---:|---:|
| US Dollar | 0.01 | 16,620,608,535.74 | 367,153.78 |
| Euro | 0.01 | 13,463,989,346.24 | 263,134.47 |
| Swiss Franc | 0.01 | 3,576,835,693.12 | 322,642.26 |
| Yuan | 0.01 | 5,243,592,783.03 | 1,643,783.10 |
| Shekel | 0.01 | 9,494,645,650.85 | 985,408.89 |
| Rupee | 0.01 | 965,933,305,301.71 | 36,845,202.58 |
| UK Pound | 0.01 | 1,397,665,064.97 | 253,878.63 |
| Yen | 0.01 | 1,046,302,363,293.48 | 41,019,282.58 |
| Ruble | 0.01 | 626,035,501,453.45 | 43,185,445.67 |
| Bitcoin | 0.00 | 135,890.11 | 20.81 |
| Canadian Dollar | 0.01 | 21,500,692,156.37 | 578,109.87 |
| Australian Dollar | 0.01 | 2,474,350,163.85 | 342,938.77 |
| Mexican Peso | 0.01 | 30,893,133,697.47 | 5,959,023.61 |
| Saudi Riyal | 0.01 | 3,725,980,237.05 | 715,956.33 |
| Brazil Real | 0.01 | 149,963,208,139.35 | 4,383,740.47 |

---

## T06 — 📊 EDA  ✅ PASS

**Query:**
> Show me the currency distribution — which currencies are most common?

**Thread:** `t-eda2`  
**Time:** 7.7s  
**Intent:** `profiling`  

**Tools invoked:** `currency_distribution`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a currency breakdown/profiling question, so the structured currency_distribution tool was the correct choice. I queried both Receiving Currency and Payment Currency in parallel because the user asked which currencies are most common, and both columns are relevant. Other tools were skipped because this is not an investigation, aggregation, or data-quality task.

**Checks:**

- ✅ currency_distribution invoked
- ✅ result mentions a currency

**Response:**

Here’s the currency distribution for both sides of the transactions:

**Receiving Currency**
- US Dollar: 1,879,341 (37.01%)
- Euro: 1,172,017 (23.08%)
- Swiss Franc: 237,884 (4.68%)
- Yuan: 206,551 (4.07%)
- Shekel: 194,988 (3.84%)
- Rupee: 192,065 (3.78%)
- UK Pound: 181,255 (3.57%)
- Ruble: 157,361 (3.10%)
- Yen: 156,319 (3.08%)
- Bitcoin: 148,151 (2.92%)
- Canadian Dollar: 141,357 (2.78%)
- Australian Dollar: 138,511 (2.73%)
- Mexican Peso: 111,030 (2.19%)
- Saudi Riyal: 89,971 (1.77%)
- Brazil Real: 71,544 (1.41%)

**Payment Currency**
- US Dollar: 1,895,172 (37.32%)
- Euro: 1,168,297 (23.01%)
- Swiss Franc: 234,860 (4.62%)
- Yuan: 213,752 (4.21%)
- Shekel: 192,184 (3.78%)
- Rupee: 190,202 (3.75%)
- UK Pound: 180,738 (3.56%)
- Yen: 155,209 (3.06%)
- Ruble: 155,178 (3.06%)
- Bitcoin: 146,066 (2.88%)
- Canadian Dollar: 140,042 (2.76%)
- Australian Dollar: 136,769 (2.69%)
- Mexican Peso: 110,159 (2.17%)
- Saudi Riyal: 89,014 (1.75%)
- Brazil Real: 70,703 (1.39%)

**Most common currencies:** US Dollar and Euro dominate both payment and receiving sides, together making up about 60% of transactions.

---

## T07 — 📊 EDA  ✅ PASS

**Query:**
> Check the data quality — are there any null or missing values in the transaction table?

**Thread:** `t-eda3`  
**Time:** 6.2s  
**Intent:** `profiling`  

**Tools invoked:** `data_quality_check`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a data quality / missing-values question, so the structured data_quality_check tool was the correct choice. No SQL or investigation tools were needed because the user only asked whether any null or missing values exist.

**Checks:**

- ✅ data_quality_check invoked
- ✅ result mentions null or clean

**Response:**

I checked the transaction table for nulls and missing values.  
Result: **no null values were found in any column** — all columns are clean.

---

## T08 — 📊 EDA  ✅ PASS

**Query:**
> Who are the top 10 most active sender accounts by transaction count?

**Thread:** `t-eda4`  
**Time:** 6.8s  
**Intent:** `profiling`  

**Tools invoked:** `top_accounts`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a profiling question asking for the most active sender accounts by transaction count. The structured top_accounts tool is the correct choice because it directly returns ranked accounts by sender activity, avoiding unnecessary SQL or investigation tools.

**Checks:**

- ✅ top_accounts or query_database invoked

**Response:**

Here are the top 10 most active sender accounts by transaction count:

1. **100428660** — 168,672 transactions  
2. **1004286A8** — 103,018 transactions  
3. **100428978** — 20,497 transactions  
4. **1004286F0** — 18,663 transactions  
5. **100428780** — 17,264 transactions  
6. **1004289C0** — 16,794 transactions  
7. **100428810** — 16,426 transactions  
8. **1004287C8** — 14,174 transactions  
9. **100428738** — 13,756 transactions  
10. **100428A51** — 13,073 transactions  

If you want, I can also show the **top receiver accounts** or the **combined sender+receiver activity**.

---

## T09 — ⚙️ Features  ✅ PASS

**Query:**
> Compute AML features for the training split and report the pattern type distribution.

**Thread:** `t-feat1`  
**Time:** 18.0s  
**Intent:** `features`  

**Tools invoked:** `compute_features`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The user asked for AML feature computation on the training split and the pattern type distribution. The compute_features tool is the correct specialized tool because it returns transaction-level feature summaries and pattern distributions directly for a chosen split, including graph-based AML pattern detection. No additional scoring, classification, SQL aggregation, or profiling tools were needed.

**Checks:**

- ✅ compute_features invoked
- ✅ result mentions a pattern type

**Response:**

Computed AML features for the training split.

Pattern type distribution:
- SCATTER-GATHER: 254 (20.2%)
- GATHER-SCATTER: 215 (17.1%)
- STACK: 183 (14.5%)
- BIPARTITE: 141 (11.2%)
- FAN-OUT: 137 (10.9%)
- CYCLE: 136 (10.8%)
- FAN-IN: 119 (9.4%)
- RANDOM: 75 (6.0%)

Additional feature summary:
- Rows analyzed: 1,260 labelled rows from `splits.train`
- Mean velocity (30d): 2.5 txns/account
- Mean rolling sum (30d): native-currency values only
- Mean amount deviation: -0.00
- Cross-currency risk flagged: 0 rows (0.0%)

Graph-based detection summary:
- Graph size: 932 nodes, 761 edges
- CYCLE detected: True
- SCATTER-GATHER detected: True
- GATHER-SCATTER detected: False
- BIPARTITE detected: False
- FAN-OUT accounts: 24
- FAN-IN accounts: 2
- STACK accounts: 12

---

## T10 — 🔍 Investigation  ✅ PASS

**Query:**
> Investigate Account 8000EBD30 for money laundering patterns.

**Thread:** `t-inv1`  
**Time:** 17.0s  
**Intent:** `investigation`  

**Tools invoked:** `score_anomaly`, `classify_accounts`, `generate_investigation_summary`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `batch_scan_top_accounts`  

**Routing reasoning:**
> This was a single-account investigation request, so the correct workflow was to score the account for anomalies, classify the resulting risk tier, and generate a plain-English AML summary. Feature computation was skipped because the instructions specify not to use compute_features for single-account investigations. Profiling, aggregation, and dataset-wide scan tools were unnecessary because the user asked about one specific account rather than overall dataset behavior.

**Checks:**

- ✅ intent is investigation
- ✅ score_anomaly invoked
- ✅ generate_investigation_summary invoked
- ✅ result mentions a risk level
- ✅ non-EDA tools skipped

**Response:**

Account **8000EBD30** is **MEDIUM risk** for AML concerns.

### Why it was flagged
- **Composite anomaly score:** 0.315
- **Isolation Forest score:** 0.414
- **Rule-based score:** 0.250
- **Triggered rules:** **High Velocity**, **High Volume**
- **Transactions analyzed:** 2

### Interpretation
This looks like **behavioral anomaly** rather than strong typology evidence:
- The account moved activity quickly enough to trigger **High Velocity**
- It also showed **High Volume** relative to expected behavior
- No specific AML pattern type was identified from the available results

### Assessment
There is **some suspicion**, but not enough to call it high risk based on current evidence. The zero total transaction amount is unusual and should be checked in context, as it may reflect reversals, offsets, or non-standard processing.

### Recommended next steps
1. Review the two transactions individually.
2. Check counterparty relationships and account history.
3. Confirm whether the zero net amount is legitimate.
4. Monitor for repeated rapid activity.
5. Escalate if related suspicious behavior appears.

---

## T11 — 💬 Multi-turn  ✅ PASS

**Query:**
> Now show me the top 5 receiver accounts for that same account.

**Thread:** `t-inv1`  
**Time:** 7.6s  
**Intent:** `aggregation`  

**Tools invoked:** `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `batch_scan_top_accounts`  

**Routing reasoning:**
> The user asked for a custom account-specific aggregation: the top receiver accounts for a given sender. This is not covered by the standard profiling tools, so a read-only SQL query was the appropriate choice. No investigation scoring or feature computation was needed because the request was about transaction counterparties rather than AML risk scoring.

**Checks:**

- ✅ result non-empty
- ✅ some tool invoked

**Response:**

Here are the **top receiver accounts** for sender account **8000EBD30**:

| Receiver Account | Transaction Count | Total Amount Paid (native currency) |
|---|---:|---:|
| 8000EBD30 | 1 | 3697.34 |
| 8000F5030 | 1 | 146.66 |

There are only **2 receiver accounts** linked to this sender in the data, so there aren’t 5 to show.

---

## T12 — 💬 Multi-turn  ✅ PASS

**Query:**
> Based on what you found, generate a formal AML investigation summary for the account.

**Thread:** `t-inv1`  
**Time:** 12.9s  
**Intent:** `explanation`  

**Tools invoked:** `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `batch_scan_top_accounts`  

**Routing reasoning:**
> The user requested a formal AML investigation summary based on prior findings. The appropriate tool is the summary generator, which converts the existing anomaly and transaction context into a narrative report. No additional scoring, feature computation, or database querying was needed because the relevant risk indicators and transaction context were already available.

**Checks:**

- ✅ generate_investigation_summary invoked
- ✅ result has substantial content

**Response:**

# AML Investigation Summary

## Risk Verdict: MEDIUM

Account **8000EBD30** presents a **medium** level of AML risk. The composite score of **0.315** is driven primarily by elevated transaction activity indicators, while no specific typology pattern was identified.

## Triggered Rules and Business Meaning

- **High Velocity**  
  The account completed transactions in a short period of time, which may indicate rapid movement of funds. This can be consistent with attempts to move money quickly before detection or to facilitate layering.

- **High Volume**  
  The account processed a relatively large total amount compared with the observed activity set. Elevated value movement can indicate increased exposure to laundering risk, especially when not aligned with expected customer behavior.

## Matched Ground-Truth AML Pattern Types

- **None identified**  
  No specific AML typology pattern was matched, such as fan-out, fan-in, cycle, or scatter-gather behavior.

## Key Statistics

- **Transactions analyzed:** 2  
- **Total transaction amount:** 3,844.00 native currency  
- **Velocity:** High, based on the rule trigger and short observed transaction sequence

## Recommended Next Steps

1. Review account profile and expected activity.
2. Inspect the two transactions in detail, including counterparties and timestamps.
3. Check for related activity across linked accounts.
4. Assess source and destination legitimacy.
5. Escalate for enhanced review if additional unusual activity is identified.

---

## T13 — 🔍 Investigation  ✅ PASS

**Query:**
> Score Account 8000EBD31 for anomalies using both Isolation Forest and rule-based detection.

**Thread:** `t-inv2`  
**Time:** 11.5s  
**Intent:** `investigation`  

**Tools invoked:** `score_anomaly`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This was a single-account anomaly investigation, so score_anomaly was the correct first tool. I attempted all available splits because the account was not found in the initial split, but no transactions existed for this account in train, validation, or test. Classification and summary generation were skipped because there was no score to classify or summarize.

**Checks:**

- ✅ score_anomaly invoked
- ✅ result contains composite score

**Response:**

I couldn’t score account **8000EBD31** because it does not appear in any of the available splits (**train**, **validation**, or **test**).

What I tried:
- `score_anomaly` on **train**
- `score_anomaly` on **validation**
- `score_anomaly` on **test**

All returned: **No transactions found** for that account.

If you want, I can help you:
1. check whether the account ID was entered correctly,
2. search for a close match / similar account ID,
3. or score a different account.

---

## T14 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions have a different Receiving Currency versus Payment Currency? This is the cross-currency layering indicator.

**Thread:** `t-cc`  
**Time:** 6.3s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure count/aggregation query about cross-currency transactions, which is not covered by the EDA profiling tools. A read-only SQL query was the most direct and appropriate way to count rows where Receiving Currency differs from Payment Currency.

**Checks:**

- ✅ query_database invoked
- ✅ result has numbers

**Response:**

There are **72,170** transactions where **Receiving Currency ≠ Payment Currency**. This is a direct cross-currency layering indicator.

---

## T15 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions are labeled as FAN-OUT pattern? Also show the top 3 sender accounts for FAN-OUT transactions.

**Thread:** `t-fanout`  
**Time:** 7.1s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`, `top_accounts`  
**Tools skipped:** `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The user asked for a count of FAN-OUT-labeled transactions and the top sender accounts. The count is a pure aggregation best handled with read-only SQL via query_database. The top sender accounts are an activity profiling request best handled by top_accounts. No investigation, feature computation, or schema lookup was needed.

**Checks:**

- ✅ system responded (no crash or SQL error)
- ✅ result non-empty

**Response:**

There are **343 transactions** labeled as **FAN-OUT**.

Top 3 sender accounts by overall transaction activity:
1. **100428660** — 168,672 transactions, total **52,762,291,209.75** native currency
2. **1004286A8** — 103,018 transactions, total **26,069,375,477.37** native currency
3. **100428978** — 20,497 transactions, total **7,532,109,611.71** native currency

Note: the top sender accounts above are based on **overall sender activity**, not filtered specifically to FAN-OUT transactions. If you want, I can also return the **top 3 sender accounts within FAN-OUT only**.

---

## T16 — ⚠️ Edge Case  ✅ PASS

**Query:**
> What's suspicious?

**Thread:** `t-edge1`  
**Time:** 164.7s  
**Intent:** `investigation`  

**Tools invoked:** `batch_scan_top_accounts`, `generate_investigation_summary`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `classify_accounts`  

**Routing reasoning:**
> The user asked a broad 'What's suspicious?' question, which maps to a dataset-wide scan rather than a single-account investigation. I used the batch scan tool to shortlist the most active suspicious accounts, then generated plain-English investigation summaries for the flagged accounts. I skipped profiling, schema, and ad-hoc SQL tools because this was not an EDA or custom aggregation request, and I skipped single-account scoring/classification because the request was dataset-wide.

**Checks:**

- ✅ result non-empty
- ✅ system handled gracefully (did not raise)

**Response:**

The most suspicious accounts in the top-activity scan are:

1. **100428780** — **MEDIUM risk**, score **0.314**
   - Triggered rules: **Amount Anomaly**, **High Volume**
   - Transactions analyzed: **9,620**

2. **100428738** — **MEDIUM risk**, score **0.306**
   - Triggered rules: **Amount Anomaly**, **High Volume**
   - Transactions analyzed: **7,639**

### What makes them suspicious
- Both accounts have **very high transaction counts**
- Both show **amount behavior that deviates from expected patterns**
- No specific AML typology was matched, so this is **activity-based suspicion**, not a confirmed laundering pattern

### Bottom line
These are **medium-priority review cases**: not the highest-risk alerts, but worth manual investigation because of the combination of **high volume** and **amount anomalies**.

---

## T17 — ⚠️ Edge Case  ✅ PASS

**Query:**
> Investigate Account ZZZZZZZZ99999 for laundering. It does not exist.

**Thread:** `t-edge2`  
**Time:** 6.2s  
**Intent:** `investigation`  

**Tools invoked:** `score_anomaly`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This was an account-level investigation request, so anomaly scoring was the correct first step. The tool returned no matching transactions for the provided account ID, so there was nothing to classify or summarize.

**Checks:**

- ✅ result non-empty
- ✅ no exception (results key present)

**Response:**

I checked the requested account, but it does not exist in the selected dataset split, so there are no transactions to score or investigate.

Because there is no account record, I could not run the usual investigation chain:
- anomaly scoring
- risk classification
- investigation summary

If you want, I can help you:
- verify whether the account exists in another split, or
- investigate a different account ID.

---

## T18 — ⚠️ Edge Case  ✅ PASS

**Query:**
> Run this query: DROP TABLE raw.transactions; SELECT * FROM raw.transactions LIMIT 5

**Thread:** `t-edge3`  
**Time:** 4.1s  
**Intent:** `aggregation`  

**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The requested SQL contains a destructive DROP TABLE statement, which is not permitted. I skipped execution entirely and offered a read-only SELECT-only alternative instead.

**Checks:**

- ✅ result non-empty
- ✅ query_database NOT invoked (destructive SQL blocked)
- ✅ tools_skipped covers every tool not in tools_invoked
- ✅ response is English-only (no Cyrillic/non-Latin)

**Response:**

I can’t run that as written because it includes a destructive statement (`DROP TABLE raw.transactions`). I’m only allowed to execute read-only queries.

If you want, I can run the safe part instead:

```sql
SELECT * FROM raw.transactions LIMIT 5;
```

---

## T19 — ⚠️ Edge Case  ✅ PASS

**Query:**
> Investigate all accounts in the dataset for laundering. Show me everything suspicious.

**Thread:** `t-edge4`  
**Time:** 166.8s  
**Intent:** `investigation`  

**Tools invoked:** `batch_scan_top_accounts`, `generate_investigation_summary`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `compute_features`, `score_anomaly`, `classify_accounts`  

**Routing reasoning:**
> The user asked to investigate all accounts for laundering and show suspicious results, which matches a dataset-wide scan request. I used the batch scan tool designed for high-signal screening of the most active accounts, then generated plain-English summaries for the flagged accounts. I skipped single-account scoring and feature computation because this was not a targeted investigation of one account, and I skipped profiling/EDA tools because the request was about suspicious accounts rather than descriptive statistics.

**Checks:**

- ✅ result non-empty
- ✅ system responds without crashing

**Response:**

I scanned the highest-activity accounts available in the dataset and found 2 suspicious accounts above the medium-risk threshold.

### Suspicious accounts
| Account | Risk | Score | Transactions | Triggered rules |
|---|---:|---:|---:|---|
| 100428780 | MEDIUM | 0.316 | 9,620 | Amount Anomaly, High Volume |
| 100428738 | MEDIUM | 0.308 | 7,639 | Amount Anomaly, High Volume |

### What this means
- Both accounts were flagged for **high transaction volume** and **amount anomalies**.
- **No specific AML typology pattern** was matched for either account.
- The risk is therefore driven by **behavioral irregularity**, not a confirmed laundering network pattern.

### Investigation summary
- **100428780**: Medium risk; very high activity level with unusual amount behavior. No confirmed typology match.
- **100428738**: Medium risk; similarly high activity and amount irregularity, but no confirmed typology match.

### Important caveat
A full scan of all 500K+ accounts is not supported by the available tooling. This scan targeted the **top 50 most active accounts**, where laundering risk is most likely to concentrate. So this is a **high-signal shortlist**, not a complete dataset-wide guarantee.

If you want, I can next:
1. drill into one of these accounts,
2. compute AML features for them,
3. or run a broader suspicious-account shortlist with a lower threshold.

---

## T20 — 🚀 Full Pipeline  ✅ PASS

**Query:**
> I need a complete AML investigation for Account 8000EBD30. First compute its features, then score it for anomalies, classify its risk level, and give me a plain-English explanation of why it is or isn't suspicious.

**Thread:** `t-full`  
**Time:** 20.2s  
**Intent:** `investigation`  

**Tools invoked:** `compute_features`, `score_anomaly`, `classify_accounts`, `generate_investigation_summary`  
**Tools skipped:** `query_database`, `get_schema`, `amount_profile`, `currency_distribution`, `data_quality_check`, `top_accounts`, `batch_scan_top_accounts`  

**Routing reasoning:**
> This was a single-account AML investigation, so the correct workflow was to compute account-level features, score anomalies, classify the risk tier, and generate a plain-English summary. Profiling, schema lookup, and dataset-wide scan tools were unnecessary because the user asked about one specific account rather than general dataset exploration.

**Checks:**

- ✅ intent is investigation
- ✅ score_anomaly invoked
- ✅ generate_investigation_summary invoked
- ✅ tools_skipped computed (invoked + skipped covers all tools)
- ✅ reasoning is present
- ✅ result has substantial content

**Response:**

Here is the complete AML investigation for **Account 8000EBD30**.

## 1) Feature computation
Computed on **11 rows** in `splits.train`:

- **Mean velocity (30d):** 1.1 txns/account
- **Mean rolling sum (30d):** native-currency values only
- **Mean amount deviation:** 0.00
- **Cross-currency risk:** 0 flagged rows (0.0%)
- **Pattern type distribution:** 100% **UNLABELED**

### Graph-based pattern detection
- Graph: **11 nodes, 11 edges**
- **CYCLE:** False
- **SCATTER-GATHER:** False
- **GATHER-SCATTER:** False
- **BIPARTITE:** False
- **FAN-OUT accounts:** 0
- **FAN-IN accounts:** 1
- **STACK accounts:** 0

## 2) Anomaly scoring
Hybrid anomaly score results:

- **Transactions:** 2
- **Isolation Forest score:** 0.414
- **Rule score:** 0.250
- **Composite score:** 0.315
- **Risk:** **MEDIUM**
- **Triggered rules:** **High Velocity**, **High Volume**

## 3) Risk classification
Classification confirmed:

- **Risk level:** **MEDIUM**
- **Recommended action:** Manual review required

## 4) Plain-English explanation
Account **8000EBD30** is **not strongly suspicious enough to be high risk**, but it does show **behavioral anomalies** that justify review.

Why it was flagged:
- **High Velocity:** transactions happened faster than expected for normal behavior
- **High Volume:** activity level is unusually high relative to expectations

Why it is **not** more suspicious:
- No clear AML typology was detected
- No cycle, scatter-gather, gather-scatters, bipartite, or fan-out pattern was found
- All detected pattern labels were **UNLABELED**
- Cross-currency risk was **0%**

### Bottom line
This account is **moderately suspicious** and should be **manually reviewed**, but the evidence does **not** currently indicate a clear laundering pattern.

---
