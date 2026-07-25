# Sentinel AML — End-to-End Test Results

**Run date:** 2026-07-25 23:51:42  
**Result:** 20/20 tests passed  

---

## Summary Table

| # | ID | Category | Status | Time | Tools Invoked |
|---|----|----|----|----|---|
| 01 | T01 | Aggregation | ✅ PASS | 4.6s | `query_database` |
| 02 | T02 | Aggregation | ✅ PASS | 6.2s | `get_schema`, `query_database` |
| 03 | T03 | Aggregation | ✅ PASS | 4.5s | `query_database` |
| 04 | T04 | Aggregation | ✅ PASS | 5.9s | `get_schema` |
| 05 | T05 | EDA | ✅ PASS | 7.2s | `get_schema`, `query_database` |
| 06 | T06 | EDA | ✅ PASS | 4.9s | `query_database` |
| 07 | T07 | EDA | ✅ PASS | 8.0s | `get_schema`, `query_database` |
| 08 | T08 | EDA | ✅ PASS | 4.5s | `query_database` |
| 09 | T09 | Features | ✅ PASS | 6.7s | `compute_features` |
| 10 | T10 | Investigation | ✅ PASS | 13.6s | `score_anomaly`, `classify_accounts`, `generate_investigation_summary` |
| 11 | T11 | Multi-turn | ✅ PASS | 5.3s | `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database` |
| 12 | T12 | Multi-turn | ✅ PASS | 11.1s | `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database` |
| 13 | T13 | Investigation | ✅ PASS | 7.3s | `score_anomaly` |
| 14 | T14 | Aggregation | ✅ PASS | 3.9s | `query_database` |
| 15 | T15 | Aggregation | ✅ PASS | 8.1s | `get_schema`, `query_database` |
| 16 | T16 | Edge Case | ✅ PASS | 8.3s | `batch_scan_top_accounts` |
| 17 | T17 | Edge Case | ✅ PASS | 8.8s | `score_anomaly` |
| 18 | T18 | Edge Case | ✅ PASS | 3.2s | — |
| 19 | T19 | Edge Case | ✅ PASS | 8.0s | `batch_scan_top_accounts` |
| 20 | T20 | Full Pipeline | ✅ PASS | 18.0s | `compute_features`, `score_anomaly`, `classify_accounts`, `generate_investigation_summary` |

---

## T01 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions are in the database?

**Thread:** `t-agg`  
**Time:** 4.6s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation question asking for a simple row count, so a read-only SQL query was sufficient. No schema lookup or AML investigation tools were needed.

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
**Time:** 6.2s  
**Intent:** `aggregation`  

**Tools invoked:** `get_schema`, `query_database`  
**Tools skipped:** `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation request asking for a total count and a categorical breakdown by payment format. I used get_schema first to confirm the exact column names, then query_database to run a read-only SQL aggregation. AML feature computation, anomaly scoring, classification, and narrative summary tools were unnecessary because no investigation or pattern detection was requested.

**Checks:**

- ✅ query_database invoked
- ✅ result has numbers

**Response:**

There are **4,483 laundering transactions** in total.

Breakdown by payment format:

- **ACH:** 4,483
- **Cheque:** 324
- **Credit Card:** 206
- **Cash:** 108
- **Bitcoin:** 56

Note: the percentages in the query output are the share of laundering transactions by format, but the total count shown in the result table is repeated on each row because of the grouped query. The true total is **4,483**.

---

## T03 — 🔢 Aggregation  ✅ PASS

**Query:**
> Count total transactions where the Amount Paid is over $10,000.

**Thread:** `t-agg3`  
**Time:** 4.5s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation/counting request, so a single read-only SQL query was sufficient. No schema lookup was needed because the column name was already specified, and no AML feature or anomaly tools were necessary.

**Checks:**

- ✅ query_database invoked
- ✅ result non-empty

**Response:**

There are **1,370,620** total transactions where **"Amount Paid" > $10,000**.

---

## T04 — 🔢 Aggregation  ✅ PASS

**Query:**
> What tables and columns are available in the database?

**Thread:** `t-schema`  
**Time:** 5.9s  
**Intent:** `profiling`  

**Tools invoked:** `get_schema`  
**Tools skipped:** `query_database`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The user asked for the available tables and columns, which is a schema inspection task. get_schema is the correct tool because it directly returns table and column definitions; no SQL aggregation or AML investigation tools were needed.

**Checks:**

- ✅ get_schema or query_database invoked
- ✅ result mentions transactions

**Response:**

Here’s the database schema:

### `raw`
- **accounts**
  - Bank Name (VARCHAR)
  - Bank ID (BIGINT)
  - Account Number (VARCHAR)
  - Entity ID (VARCHAR)
  - Entity Name (VARCHAR)

- **transactions**
  - Timestamp (TIMESTAMP)
  - From Bank (VARCHAR)
  - Account (VARCHAR)
  - To Bank (VARCHAR)
  - Account.1 (VARCHAR)
  - Amount Received (DOUBLE)
  - Receiving Currency (VARCHAR)
  - Amount Paid (DOUBLE)
  - Payment Currency (VARCHAR)
  - Payment Format (VARCHAR)
  - Is Laundering (BIGINT)
  - pattern_type (VARCHAR)

### `splits`
- **metadata**
  - train_row_cutoff (INTEGER)
  - val_row_cutoff (INTEGER)
  - train_start_ts (VARCHAR)
  - test_end_ts (VARCHAR)
  - train_ratio (DECIMAL(2,1))
  - val_ratio (DECIMAL(2,1))
  - test_ratio (DECIMAL(2,1))

- **train**
  - Timestamp (TIMESTAMP)
  - From Bank (VARCHAR)
  - Account (VARCHAR)
  - To Bank (VARCHAR)
  - Account.1 (VARCHAR)
  - Amount Received (DOUBLE)
  - Receiving Currency (VARCHAR)
  - Amount Paid (DOUBLE)
  - Payment Currency (VARCHAR)
  - Payment Format (VARCHAR)
  - Is Laundering (BIGINT)
  - pattern_type (VARCHAR)

- **validation**
  - Timestamp (TIMESTAMP)
  - From Bank (VARCHAR)
  - Account (VARCHAR)
  - To Bank (VARCHAR)
  - Account.1 (VARCHAR)
  - Amount Received (DOUBLE)
  - Receiving Currency (VARCHAR)
  - Amount Paid (DOUBLE)
  - Payment Currency (VARCHAR)
  - Payment Format (VARCHAR)
  - Is Laundering (BIGINT)
  - pattern_type (VARCHAR)

- **test**
  - Timestamp (TIMESTAMP)
  - From Bank (VARCHAR)
  - Account (VARCHAR)
  - To Bank (VARCHAR)
  - Account.1 (VARCHAR)
  - Amount Received (DOUBLE)
  - Receiving Currency (VARCHAR)
  - Amount Paid (DOUBLE)
  - Payment Format (VARCHAR)
  - Is Laundering (BIGINT)
  - pattern_type (VARCHAR)

---

## T05 — 📊 EDA  ✅ PASS

**Query:**
> What is the minimum, maximum, and average transaction amount per currency?

**Thread:** `t-eda1`  
**Time:** 7.2s  
**Intent:** `aggregation`  

**Tools invoked:** `get_schema`, `query_database`  
**Tools skipped:** `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation/profiling request asking for summary statistics by currency, so I used schema inspection to confirm the relevant columns and then a read-only SQL aggregation query. AML investigation and anomaly-scoring tools were unnecessary because no account-level investigation or pattern detection was requested.

**Checks:**

- ✅ query_database invoked
- ✅ result contains amounts

**Response:**

Here’s the minimum, maximum, and average transaction amount per currency, based on `"Amount Paid"`:

| Currency | Min Amount | Max Amount | Avg Amount | Txn Count |
|---|---:|---:|---:|---:|
| Australian Dollar | 0.01 | 2,474,350,163.85 | 342,938.77 | 136,769 |
| Bitcoin | 0.000001 | 135,890.107125 | 20.81 | 146,066 |
| Brazil Real | 0.01 | 149,963,208,139.35 | 4,383,740.47 | 70,703 |
| Canadian Dollar | 0.01 | 21,500,692,156.37 | 578,109.87 | 140,042 |
| Euro | 0.01 | 13,463,989,346.24 | 263,134.47 | 1,168,297 |
| Mexican Peso | 0.01 | 30,893,133,697.47 | 5,959,023.61 | 110,159 |
| Ruble | 0.01 | 626,035,501,453.45 | 43,185,445.67 | 155,178 |
| Rupee | 0.01 | 965,933,305,301.71 | 36,845,202.58 | 190,202 |
| Saudi Riyal | 0.01 | 3,725,980,237.05 | 715,956.33 | 89,014 |
| Shekel | 0.01 | 9,494,645,650.85 | 985,408.89 | 192,184 |
| Swiss Franc | 0.01 | 3,576,835,693.12 | 322,642.26 | 234,860 |
| UK Pound | 0.01 | 1,397,665,064.97 | 253,878.63 | 180,738 |
| US Dollar | 0.01 | 16,620,608,535.74 | 367,153.78 | 1,895,172 |
| Yen | 0.01 | 1,046,302,363,293.48 | 41,019,282.58 | 155,209 |
| Yuan | 0.01 | 5,243,592,783.03 | 1,643,783.10 | 213,752 |

---

## T06 — 📊 EDA  ✅ PASS

**Query:**
> Show me the currency distribution — which currencies are most common?

**Thread:** `t-eda2`  
**Time:** 4.9s  
**Intent:** `profiling`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation/profiling request asking for a currency breakdown, so a single read-only SQL query is sufficient. No schema lookup or AML anomaly tools were needed because there was no investigation or feature-engineering component.

**Checks:**

- ✅ query_database invoked
- ✅ result mentions a currency

**Response:**

Here’s the currency distribution by transaction count:

1. **US Dollar** — 1,895,172 transactions (**37.32%**)
2. **Euro** — 1,168,297 (**23.01%**)
3. **Swiss Franc** — 234,860 (**4.62%**)
4. **Yuan** — 213,752 (**4.21%**)
5. **Shekel** — 192,184 (**3.78%**)
6. **Rupee** — 190,202 (**3.75%**)
7. **UK Pound** — 180,738 (**3.56%**)
8. **Yen** — 155,209 (**3.06%**)
9. **Ruble** — 155,178 (**3.06%**)
10. **Bitcoin** — 146,066 (**2.88%**)
11. **Canadian Dollar** — 140,042 (**2.76%**)
12. **Australian Dollar** — 136,769 (**2.69%**)
13. **Mexican Peso** — 110,159 (**2.17%**)
14. **Saudi Riyal** — 89,014 (**1.75%**)
15. **Brazil Real** — 70,703 (**1.39%**)

The most common currencies are **US Dollar** and **Euro**, which together make up about **60.33%** of all transactions.

---

## T07 — 📊 EDA  ✅ PASS

**Query:**
> Check the data quality — are there any null or missing values in the transaction table?

**Thread:** `t-eda3`  
**Time:** 8.0s  
**Intent:** `profiling`  

**Tools invoked:** `get_schema`, `query_database`  
**Tools skipped:** `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This was a data quality profiling request focused on missing values in the transaction table. I first inspected the schema to confirm column names, then ran a read-only aggregation query to count nulls per column. No AML feature computation or anomaly scoring was needed because the user asked only about data completeness.

**Checks:**

- ✅ query_database invoked
- ✅ result mentions null or clean

**Response:**

I checked the `raw.transactions` table for nulls across all columns, and there are **no missing values** in any field.

Summary:
- `Timestamp`: 0
- `From Bank`: 0
- `Account`: 0
- `To Bank`: 0
- `Account.1`: 0
- `Amount Received`: 0
- `Receiving Currency`: 0
- `Amount Paid`: 0
- `Payment Currency`: 0
- `Payment Format`: 0
- `Is Laundering`: 0
- `pattern_type`: 0

So the transaction table appears complete with respect to null values.

---

## T08 — 📊 EDA  ✅ PASS

**Query:**
> Who are the top 10 most active sender accounts by transaction count?

**Thread:** `t-eda4`  
**Time:** 4.5s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation request asking for the top sender accounts by transaction count. A single read-only SQL query is sufficient, so no schema lookup or AML scoring tools were needed.

**Checks:**

- ✅ query_database invoked
- ✅ result non-empty

**Response:**

Top 10 most active sender accounts by transaction count:

1. 100428660 — 168,672
2. 1004286A8 — 103,018
3. 100428978 — 20,497
4. 1004286F0 — 18,663
5. 100428780 — 17,264
6. 1004289C0 — 16,794
7. 100428810 — 16,426
8. 1004287C8 — 14,174
9. 100428738 — 13,756
10. 100428A51 — 13,073

---

## T09 — ⚙️ Features  ✅ PASS

**Query:**
> Compute AML features for the training split and report the pattern type distribution.

**Thread:** `t-feat1`  
**Time:** 6.7s  
**Intent:** `features`  

**Tools invoked:** `compute_features`  
**Tools skipped:** `query_database`, `get_schema`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The request was specifically to compute AML features for the training split and report the pattern type distribution, which is exactly what the compute_features tool is designed for. No database aggregation, single-account investigation, or risk classification was needed.

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
- Mean velocity (30d): 1.5 txns/account
- Mean rolling sum (30d): $6,190,525.34
- Mean amount deviation: -0.00
- Cross-currency risk flagged rows: 0 (0.0%)

Graph-based detection summary:
- Graph size: 919 nodes, 737 edges
- SCATTER-GATHER detected: True
- FAN-OUT accounts: 18
- FAN-IN accounts: 4
- STACK accounts: 2

---

## T10 — 🔍 Investigation  ✅ PASS

**Query:**
> Investigate Account 8000EBD30 for money laundering patterns.

**Thread:** `t-inv1`  
**Time:** 13.6s  
**Intent:** `investigation`  

**Tools invoked:** `score_anomaly`, `classify_accounts`, `generate_investigation_summary`  
**Tools skipped:** `query_database`, `get_schema`, `compute_features`, `batch_scan_top_accounts`  

**Routing reasoning:**
> This was a single-account AML investigation, so the correct workflow was to score the account for anomalies, classify the resulting risk tier, and generate a plain-English investigation summary. I skipped database aggregation and feature computation tools because the request was not a general profiling query and did not require manual feature engineering or dataset-wide scanning.

**Checks:**

- ✅ intent is investigation
- ✅ score_anomaly invoked
- ✅ generate_investigation_summary invoked
- ✅ result mentions a risk level
- ✅ non-EDA tools skipped

**Response:**

Account **8000EBD30** is **LOW risk** for money laundering based on the current model output.

### What was found
- **Transactions analyzed:** 2
- **Composite anomaly score:** 0.286
- **Isolation Forest score:** 0.415
- **Rule-based score:** 0.200
- **Triggered rules:** High Velocity, High Volume
- **Matched AML patterns:** None identified

### Interpretation
The account shows some activity-based alerts, but the overall score stays below the medium-risk threshold. With only 2 transactions and no detected laundering typology, there is **no strong evidence of structured money laundering behavior** at this time.

### Recommended action
- **No immediate escalation**
- Continue routine monitoring
- Do a quick manual check if you want to confirm why the velocity/volume rules fired, especially since the reported total amount was $0.00

---

## T11 — 💬 Multi-turn  ✅ PASS

**Query:**
> Now show me the top 5 receiver accounts for that same account.

**Thread:** `t-inv1`  
**Time:** 5.3s  
**Intent:** `aggregation`  

**Tools invoked:** `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `batch_scan_top_accounts`  

**Routing reasoning:**
> This was a straightforward aggregation request asking for the top receiver accounts linked to a specific sender account. A read-only SQL query was sufficient, and no anomaly scoring, feature computation, or narrative investigation tools were needed.

**Checks:**

- ✅ result non-empty
- ✅ some tool invoked

**Response:**

Here are the top receiver accounts associated with **8000EBD30**:

| Receiver Account | Transaction Count | Total Amount |
|---|---:|---:|
| 8000EBD30 | 1 | 3697.34 |
| 8000F5030 | 1 | 146.66 |

There are only **2 receiver accounts** linked to this sender in the data, so there isn’t a full top 5 to display.

---

## T12 — 💬 Multi-turn  ✅ PASS

**Query:**
> Based on what you found, generate a formal AML investigation summary for the account.

**Thread:** `t-inv1`  
**Time:** 11.1s  
**Intent:** `explanation`  

**Tools invoked:** `score_anomaly`, `classify_accounts`, `generate_investigation_summary`, `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `batch_scan_top_accounts`  

**Routing reasoning:**
> The user requested a formal AML investigation summary based on previously gathered findings, so the appropriate tool was the narrative summary generator. I skipped database and scoring tools because no new analysis was required; the task was to convert existing results into a formal report.

**Checks:**

- ✅ generate_investigation_summary invoked
- ✅ result has substantial content

**Response:**

# AML Investigation Summary

## Risk Verdict: LOW
The account **8000EBD30** is assessed as **low risk** based on the composite score of **0.286**, which is below the medium-risk threshold. While the account triggered a small number of activity-based alerts, the overall transaction profile is limited and does not show a clear pattern consistent with known AML typologies.

## Triggered Rules and Business Meaning
- **High Velocity**  
  Indicates funds moved through the account quickly over a short period. In business terms, this can suggest rapid pass-through activity, but in this case the activity volume is very limited.

- **High Volume**  
  Indicates the account processed a relatively large dollar amount compared with expected behavior. Here, the total amount is **$3,844.00**, which is notable but based on only two transactions.

## Matched AML Pattern Types
- **None identified**  
  No ground-truth AML typology was matched. There is no evidence of structured laundering behavior such as fan-out, fan-in, cycle, stack, scatter-gather, gather-scatter, or bipartite activity.

## Key Statistics
- **Transactions analyzed:** 2
- **Total transaction amount:** **$3,844.00**
- **Velocity:** Elevated relative to expected behavior, but observed across only two transactions

## Recommended Next Steps
Given the **low-risk** assessment:
1. **No immediate escalation required** based on the current data.
2. **Continue routine monitoring** for additional activity that may establish a pattern.
3. **Review future transactions** for repetition, increased frequency, or links to higher-risk counterparties.
4. **Reassess if activity expands**, especially if the account begins showing sustained high velocity, higher volumes, or typology-consistent behavior.

---

## T13 — 🔍 Investigation  ✅ PASS

**Query:**
> Score Account 8000EBD31 for anomalies using both Isolation Forest and rule-based detection.

**Thread:** `t-inv2`  
**Time:** 7.3s  
**Intent:** `investigation`  

**Tools invoked:** `score_anomaly`  
**Tools skipped:** `query_database`, `get_schema`, `compute_features`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This was a single-account anomaly investigation, so the correct first step was to run the anomaly scorer. Classification and narrative summary were skipped because the account had no matching transactions in any split, leaving no score or triggered rules to classify or explain.

**Checks:**

- ✅ score_anomaly invoked
- ✅ result contains composite score

**Response:**

I couldn’t score Account `8000EBD31` because no transactions were found for that account in any split (`train`, `validation`, or `test`).

If you want, I can:
- check whether the account ID is mistyped,
- search for a close match,
- or score a different account.

---

## T14 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions have a different Receiving Currency versus Payment Currency? This is the cross-currency layering indicator.

**Thread:** `t-cc`  
**Time:** 3.9s  
**Intent:** `aggregation`  

**Tools invoked:** `query_database`  
**Tools skipped:** `get_schema`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This is a pure aggregation/profiling question asking for a count of transactions matching a currency mismatch condition. A direct read-only SQL query is sufficient; no schema lookup or AML scoring/pattern tools were needed.

**Checks:**

- ✅ query_database invoked
- ✅ result has numbers

**Response:**

There are **72,170 transactions** where **Receiving Currency** differs from **Payment Currency**. This is a classic **cross-currency layering indicator**.

---

## T15 — 🔢 Aggregation  ✅ PASS

**Query:**
> How many transactions are labeled as FAN-OUT pattern? Also show the top 3 sender accounts for FAN-OUT transactions.

**Thread:** `t-fanout`  
**Time:** 8.1s  
**Intent:** `aggregation`  

**Tools invoked:** `get_schema`, `query_database`  
**Tools skipped:** `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> This was a pure aggregation/profiling request: count transactions with a specific pattern label and list the top sender accounts among those transactions. I used get_schema first to confirm the relevant table and column names, then query_database to run read-only SQL. ML/anomaly tools were skipped because no feature computation or account-level investigation was needed.

**Checks:**

- ✅ some tool invoked
- ✅ result non-empty

**Response:**

There are **343 transactions** labeled as **FAN-OUT**.

Top 3 sender accounts for FAN-OUT transactions:
1. **800737690** — 16 transactions
2. **80452D470** — 16 transactions
3. **805DB7F20** — 16 transactions

---

## T16 — ⚠️ Edge Case  ✅ PASS

**Query:**
> What's suspicious?

**Thread:** `t-edge1`  
**Time:** 8.3s  
**Intent:** `explanation`  

**Tools invoked:** `batch_scan_top_accounts`  
**Tools skipped:** `query_database`, `get_schema`, `compute_features`, `score_anomaly`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The user asked a broad 'What's suspicious?' question, which maps to a dataset-wide scan. I used the batch scan tool to efficiently inspect the highest-activity accounts for suspicious behavior. No further tools were needed because the scan returned no accounts above the threshold, and the request did not specify a particular account or require schema/SQL profiling.

**Checks:**

- ✅ result non-empty
- ✅ system handled gracefully (did not raise)

**Response:**

I scanned the top 20 most active accounts in the training split for suspicious activity and found **no accounts above the medium-risk threshold**.

Summary:
- **Suspicious accounts found:** 0
- **Threshold used:** composite score ≥ 0.3
- **Scope:** top 20 by transaction volume in `splits.train`

If you want, I can:
- scan more accounts with a lower threshold,
- investigate a specific account,
- or profile the dataset for unusual patterns like high-value transfers, cycles, or fan-in/fan-out behavior.

---

## T17 — ⚠️ Edge Case  ✅ PASS

**Query:**
> Investigate Account ZZZZZZZZ99999 for laundering. It does not exist.

**Thread:** `t-edge2`  
**Time:** 8.8s  
**Intent:** `investigation`  

**Tools invoked:** `score_anomaly`  
**Tools skipped:** `query_database`, `get_schema`, `compute_features`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The user requested a single-account laundering investigation, so the correct first step was to score the specified account. The account was not found in any split, so downstream classification and summary generation were unnecessary and skipped.

**Checks:**

- ✅ result non-empty
- ✅ no exception (results key present)

**Response:**

I checked the account across train, validation, and test splits, and there are no transactions for **ZZZZZZZZ99999**. Since the account does not exist in the dataset, I can’t score it for laundering or generate an AML investigation summary.

If you want, I can:
- investigate a valid account ID,
- scan the most suspicious active accounts in the dataset, or
- help you find accounts with laundering-like patterns.

---

## T18 — ⚠️ Edge Case  ✅ PASS

**Query:**
> Run this query: DROP TABLE raw.transactions; SELECT * FROM raw.transactions LIMIT 5

**Thread:** `t-edge3`  
**Time:** 3.2s  
**Intent:** `aggregation`  

**Tools skipped:** `query_database`, `get_schema`, `compute_features`, `score_anomaly`, `batch_scan_top_accounts`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The requested SQL includes a destructive DROP TABLE statement, which is blocked by policy and by the read-only database tool. I can only execute the non-destructive SELECT portion if the user confirms or requests it separately.

**Checks:**

- ✅ result non-empty
- ✅ query_database NOT invoked (destructive SQL blocked)
- ✅ tools_skipped covers every tool not in tools_invoked
- ✅ response is English-only (no Cyrillic/non-Latin)

**Response:**

I can’t run that as written because it contains a destructive `DROP TABLE` statement, and the database tool only allows read-only SQL.

If you want, I can run the safe part instead:
```sql
SELECT * FROM raw.transactions LIMIT 5
```

---

## T19 — ⚠️ Edge Case  ✅ PASS

**Query:**
> Investigate all accounts in the dataset for laundering. Show me everything suspicious.

**Thread:** `t-edge4`  
**Time:** 8.0s  
**Intent:** `investigation`  

**Tools invoked:** `batch_scan_top_accounts`  
**Tools skipped:** `query_database`, `get_schema`, `compute_features`, `score_anomaly`, `classify_accounts`, `generate_investigation_summary`  

**Routing reasoning:**
> The request asked to investigate the dataset for suspicious laundering activity across accounts, which maps to a dataset-wide scan. The batch scan tool is the appropriate high-signal shortcut for this task. I skipped direct SQL because this is not a simple aggregation/profiling query, and I skipped single-account investigation tools because no specific account was provided.

**Checks:**

- ✅ result non-empty
- ✅ system responds without crashing

**Response:**

I scanned the top 50 most active accounts in the training split for suspicious laundering behavior using the hybrid anomaly detector. No accounts exceeded the composite score threshold of 0.3, so nothing was flagged in this high-activity shortlist.

Important caveat: a full dataset-wide scan over all accounts is not supported by the available tooling. This scan is a high-signal approximation focused on the most active accounts, where laundering patterns are often concentrated.

If you want, I can next:
- lower the threshold to surface weaker signals,
- scan a different split (`validation` or `test`),
- or investigate specific accounts one by one.

---

## T20 — 🚀 Full Pipeline  ✅ PASS

**Query:**
> I need a complete AML investigation for Account 8000EBD30. First compute its features, then score it for anomalies, classify its risk level, and give me a plain-English explanation of why it is or isn't suspicious.

**Thread:** `t-full`  
**Time:** 18.0s  
**Intent:** `investigation`  

**Tools invoked:** `compute_features`, `score_anomaly`, `classify_accounts`, `generate_investigation_summary`  
**Tools skipped:** `query_database`, `get_schema`, `batch_scan_top_accounts`  

**Routing reasoning:**
> This was a single-account AML investigation, so the correct workflow was to compute account-level features, score the account with the hybrid anomaly model, classify the resulting score into a risk tier, and generate a plain-English explanation. Database aggregation tools were unnecessary because the user did not ask for a general profile or summary table, and dataset-wide scanning was not needed because the request focused on one specific account.

**Checks:**

- ✅ intent is investigation
- ✅ score_anomaly invoked
- ✅ generate_investigation_summary invoked
- ✅ tools_skipped computed (invoked + skipped covers all tools)
- ✅ reasoning is present
- ✅ result has substantial content

**Response:**

Here’s the complete AML investigation for **Account 8000EBD30**.

### 1) Feature computation
Computed features for the account on the **train** split with graph-based pattern detection enabled.

Key outputs:
- **Transactions analyzed:** 2
- **Graph pattern detected:** **SCATTER-GATHER**
- **Cycle detected:** No
- **BIPARTITE detected:** No
- **FAN-OUT / FAN-IN / STACK:** Present in the broader graph context, but not enough to elevate this account on their own
- **Cross-currency risk:** 0 flagged rows

### 2) Anomaly scoring
Hybrid anomaly scoring returned:

- **Isolation Forest score:** 0.415
- **Rule-based score:** 0.200
- **Composite score:** **0.286**
- **Triggered rules:** **High Velocity, High Volume**
- **Risk from scorer:** **LOW**

### 3) Risk classification
Using the classification thresholds:
- **LOW < 0.3**
- **MEDIUM < 0.7**
- **HIGH >= 0.7**

This account was classified as:

- **Risk level:** **LOW**
- **Recommended action:** No action required; continue routine monitoring

### 4) Plain-English AML assessment
This account has a couple of behavioral alerts:
- **High Velocity** suggests transactions happened quickly relative to expected behavior.
- **High Volume** suggests activity exceeded normal expectations.

It also matched a **SCATTER-GATHER** pattern, which can sometimes indicate layering behavior. However, the overall picture is weak:
- only **2 transactions**
- **composite score below the medium-risk threshold**
- no strong corroborating indicators like cycles, cross-currency activity, or broader suspicious structure

### Bottom line
**8000EBD30 is not currently suspicious enough to escalate.**  
There are some mild warning signs, but the evidence is limited and the overall anomaly score remains low. I’d recommend **routine monitoring only** unless additional activity appears.

---
