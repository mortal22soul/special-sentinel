"""EDA (Exploratory Data Analysis) subagent for the Sentinel AML supervisor.

Provides profiling tools that answer questions about transaction distributions,
currency usage, data quality, and account activity volumes.

All tools execute read-only DuckDB queries and return formatted summaries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field, SecretStr

# ── Configuration ────────────────────────────────────────────────────────────

DB_PATH = Path("data/sentinel.duckdb")
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")


# ── Tool input schemas ───────────────────────────────────────────────────────


class AmountProfileInput(BaseModel):
    split: str = Field(
        default="transactions",
        description="Which table to profile: 'transactions' (full), 'train', 'validation', or 'test'",
    )


class CurrencyDistributionInput(BaseModel):
    currency_col: str = Field(
        default="Receiving Currency",
        description="Currency column to profile: 'Receiving Currency' or 'Payment Currency'",
    )


class DataQualityInput(BaseModel):
    pass


class TopAccountsInput(BaseModel):
    direction: str = Field(
        default="both",
        description="'sender' for From Account, 'receiver' for To Account, 'both' for combined",
    )
    limit: int = Field(default=10, description="Number of top accounts to return")


# ── Tool implementations ─────────────────────────────────────────────────────


def amount_profile(input: AmountProfileInput) -> str:
    """Return min, max, mean, median, and std dev of transaction amounts.

    Reports per-currency statistics to avoid misleading aggregates caused by
    mixing nominally large currencies (Yen, Rupee, Ruble) with USD/EUR.
    The IBM HI-Small dataset stores amounts in native currency units without
    normalisation, so cross-currency aggregates are intentionally NOT shown.
    """
    import duckdb

    table = (
        "raw.transactions" if input.split == "transactions" else f"splits.{input.split}"
    )
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        # Overall laundering count (currency-agnostic)
        overview = con.execute(f"""
            SELECT
                COUNT(*)                                           AS total_txns,
                COUNT(*) FILTER (WHERE "Is Laundering" = 1)       AS laundering_count,
                COUNT(DISTINCT "Payment Currency")                 AS distinct_currencies
            FROM {table}
        """).fetchone()

        if overview is None:
            overview = (0, 0, 0)

        # Per-currency stats — amounts only make sense within the same currency
        rows = con.execute(f"""
            SELECT
                "Payment Currency"                AS currency,
                COUNT(*)                          AS txn_count,
                MIN("Amount Paid")                AS min_amount,
                MAX("Amount Paid")                AS max_amount,
                AVG("Amount Paid")                AS mean_amount,
                MEDIAN("Amount Paid")             AS median_amount,
                STDDEV("Amount Paid")             AS std_amount
            FROM {table}
            GROUP BY "Payment Currency"
            ORDER BY txn_count DESC
        """).fetchall()
    finally:
        con.close()

    total_txns, laundering_count, distinct_currencies = overview
    lines = [
        f"Amount Profile ({table}):",
        f"  Total transactions: {total_txns:,}",
        f"  Laundering rows:    {laundering_count:,}",
        f"  Currencies present: {distinct_currencies}",
        "",
        "  NOTE: Amounts are in native currency units (no FX normalisation).",
        "  Cross-currency aggregates are misleading — stats shown per currency.",
        "",
        f"  {'Currency':<20} {'Count':>10}  {'Min':>15}  {'Max':>20}  {'Mean':>15}  {'Median':>12}",
        f"  {'-'*20} {'-'*10}  {'-'*15}  {'-'*20}  {'-'*15}  {'-'*12}",
    ]
    for r in rows:
        currency, cnt, mn, mx, mean, median, std = r
        lines.append(
            f"  {str(currency):<20} {cnt:>10,}  {mn:>15,.2f}  {mx:>20,.2f}  {mean:>15,.2f}  {median:>12,.2f}"
        )
    return "\n".join(lines)


def currency_distribution(input: CurrencyDistributionInput) -> str:
    """Return counts and percentages for each currency."""
    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(f"""
            SELECT
                "{input.currency_col}" AS currency,
                COUNT(*)   AS count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
            FROM raw.transactions
            GROUP BY 1
            ORDER BY count DESC
        """).fetchall()
    finally:
        con.close()

    lines = [f"Currency Distribution ({input.currency_col}):"]
    for currency, count, pct in rows:
        lines.append(f"  {currency}: {count:,} ({pct}%)")
    return "\n".join(lines)


def data_quality_check(_: DataQualityInput = DataQualityInput()) -> str:
    """Check for nulls, missing values, and data anomalies."""
    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        results = []
        for col in [
            "Timestamp",
            "From Bank",
            "Account",
            "To Bank",
            "Account.1",
            "Amount Received",
            "Receiving Currency",
            "Amount Paid",
            "Payment Currency",
            "Payment Format",
            "Is Laundering",
        ]:
            row = con.execute(
                f'SELECT COUNT(*) FROM raw.transactions WHERE "{col}" IS NULL'
            ).fetchone()
            null_count = row[0] if row is not None else 0
            results.append((col, null_count))
    finally:
        con.close()

    lines = ["Data Quality Check (null counts):"]
    any_nulls = False
    for col, count in results:
        status = f"{count:,} nulls" if count > 0 else "clean"
        lines.append(f"  {col}: {status}")
        if count > 0:
            any_nulls = True
    if not any_nulls:
        lines.append("  All columns clean — no null values found.")
    return "\n".join(lines)


def top_accounts(input: TopAccountsInput) -> str:
    """Return the most active accounts by transaction count."""
    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        if input.direction in ("sender", "both"):
            sender_rows = con.execute(
                """
                SELECT "Account" AS account, COUNT(*) AS txn_count,
                       SUM("Amount Paid") AS total_amount
                FROM raw.transactions
                GROUP BY 1
                ORDER BY txn_count DESC
                LIMIT ?
            """,
                [input.limit],
            ).fetchall()
        else:
            sender_rows = []

        if input.direction in ("receiver", "both"):
            receiver_rows = con.execute(
                """
                SELECT "Account.1" AS account, COUNT(*) AS txn_count,
                       SUM("Amount Paid") AS total_amount
                FROM raw.transactions
                GROUP BY 1
                ORDER BY txn_count DESC
                LIMIT ?
            """,
                [input.limit],
            ).fetchall()
        else:
            receiver_rows = []
    finally:
        con.close()

    lines = [f"Top {input.limit} Accounts ({input.direction}):"]
    if input.direction in ("sender", "both"):
        lines.append("  [Senders]")
        for acct, count, total in sender_rows:
            lines.append(f"    {acct}: {count:,} txns, ${total:,.2f} total")
    if input.direction in ("receiver", "both"):
        lines.append("  [Receivers]")
        for acct, count, total in receiver_rows:
            lines.append(f"    {acct}: {count:,} txns, ${total:,.2f} total")
    return "\n".join(lines)
