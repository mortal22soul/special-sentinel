"""DuckDB ingestion pipeline for the HI-Small AML dataset.

Creates an in-process DuckDB database, loads the full 5M-row transaction
CSV and accounts CSV, performs a chronological train/val/test split, and
persists the split boundaries as DuckDB metadata so every downstream
agent references the same consistent data slices.

Usage
-----
    uv run python src/data/ingest.py

The resulting database lives at ``data/sentinel.duckdb``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

# ── Configuration ────────────────────────────────────────────────────────────

DB_PATH = Path("data/sentinel.duckdb")
TRANS_PATH = Path("data/joined_labeled.csv")
ACCOUNTS_PATH = Path("data/HI-Small_accounts.csv")

TRAIN_RATIO = 0.60
VAL_RATIO = 0.20
TEST_RATIO = 0.20  # remainder; must sum to 1.0 with the above

# ── Helpers ───────────────────────────────────────────────────────────────────


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open (or create) the DuckDB database file."""
    return duckdb.connect(str(db_path))


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the top-level schema namespace."""
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS splits")


def ingest_transactions(con: duckdb.DuckDBPyConnection, trans_path: Path) -> None:
    """Load the joined labeled transaction CSV via ``read_csv_auto``.

    ``read_csv_auto`` streams from disk and auto-infers types, which
    avoids loading the full 5M-row file into Python memory.
    """
    print(f"Ingesting {trans_path} ...")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.transactions AS
        SELECT * FROM read_csv_auto('{trans_path.as_posix()}', all_varchar=false)
    """)
    count = con.execute("SELECT COUNT(*) FROM raw.transactions").fetchone()[0]
    print(f"  -> {count:,} rows loaded into raw.transactions")


def ingest_accounts(con: duckdb.DuckDBPyConnection, accounts_path: Path) -> None:
    """Load the accounts metadata CSV."""
    print(f"Ingesting {accounts_path} ...")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.accounts AS
        SELECT * FROM read_csv_auto('{accounts_path.as_posix()}', all_varchar=false)
    """)
    count = con.execute("SELECT COUNT(*) FROM raw.accounts").fetchone()[0]
    print(f"  -> {count:,} rows loaded into raw.accounts")


def create_split(con: duckdb.DuckDBPyConnection) -> None:
    """Chronologically split transactions into train / val / test.

    The split uses the ``Timestamp`` column ordering.  A row's split
    assignment is deterministic: its position in the sorted timestamp
    sequence determines which bucket it falls into.

    Split boundaries are stored as DuckDB metadata (duckdb.tables()
    settings) so all downstream agents can query them consistently.
    """
    print("Computing chronological train/val/test split ...")

    # Find the timestamp boundaries
    result = con.execute("""
        SELECT
            MIN("Timestamp") AS min_ts,
            MAX("Timestamp") AS max_ts,
            COUNT(*)      AS total
        FROM raw.transactions
    """).fetchone()

    min_ts, max_ts, total = result
    print(f"  Range: {min_ts} -> {max_ts}  ({total:,} rows)")

    train_end_idx = int(total * TRAIN_RATIO)
    val_end_idx = train_end_idx + int(total * VAL_RATIO)

    # Use row_number over ordered timestamps to assign splits.
    # Ties (same timestamp) get distributed across splits to avoid
    # leaking future data into the training set.
    con.execute("""
        CREATE OR REPLACE TABLE splits.split_view AS
        SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY "Timestamp") AS _row_num
        FROM raw.transactions
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE splits.train AS
        SELECT * EXCLUDE (_row_num)
        FROM splits.split_view
        WHERE _row_num <= {train_end_idx}
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE splits.validation AS
        SELECT * EXCLUDE (_row_num)
        FROM splits.split_view
        WHERE _row_num > {train_end_idx} AND _row_num <= {val_end_idx}
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE splits.test AS
        SELECT * EXCLUDE (_row_num)
        FROM splits.split_view
        WHERE _row_num > {val_end_idx}
    """)

    con.execute("DROP TABLE splits.split_view")

    train_count = con.execute("SELECT COUNT(*) FROM splits.train").fetchone()[0]
    val_count = con.execute("SELECT COUNT(*) FROM splits.validation").fetchone()[0]
    test_count = con.execute("SELECT COUNT(*) FROM splits.test").fetchone()[0]

    print(f"  train:      {train_count:,} rows ({train_count/total:.0%})")
    print(f"  validation: {val_count:,} rows ({val_count/total:.0%})")
    print(f"  test:       {test_count:,} rows ({test_count/total:.0%})")

    # ── Persist split boundaries as DuckDB metadata ────────────────────────
    con.execute(f"""
        CREATE OR REPLACE TABLE splits.metadata AS
        SELECT
            {train_end_idx}        AS train_row_cutoff,
            {val_end_idx}          AS val_row_cutoff,
            '{min_ts}'             AS train_start_ts,
            '{max_ts}'             AS test_end_ts,
            {TRAIN_RATIO}          AS train_ratio,
            {VAL_RATIO}            AS val_ratio,
            {TEST_RATIO}           AS test_ratio
    """)
    print("  Split boundaries stored in splits.metadata")


def create_indexes(con: duckdb.DuckDBPyConnection) -> None:
    """Create indexes to speed up account lookups and joins."""
    print("Creating indexes ...")
    # Accounts: index on Account Number for fast lookups
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_acct
        ON raw.accounts ("Account Number")
    """)
    # Transactions: index on From Account and To Account for graph traversal
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_trans_from_acct
        ON raw.transactions ("Account")
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_trans_to_acct
        ON raw.transactions ("Account.1")
    """)
    print("  Indexes created")


def main() -> None:
    if not TRANS_PATH.exists():
        sys.exit(f"ERROR: {TRANS_PATH} not found. Run parse_patterns.py first.")
    if not ACCOUNTS_PATH.exists():
        sys.exit(f"ERROR: {ACCOUNTS_PATH} not found. Place HI-Small_accounts.csv in data/.")

    con = get_connection(DB_PATH)
    try:
        create_schema(con)
        ingest_transactions(con, TRANS_PATH)
        ingest_accounts(con, ACCOUNTS_PATH)
        create_split(con)
        create_indexes(con)

        print(f"\nDatabase written to {DB_PATH}")

        # Quick sanity check
        laundering_total = con.execute(
            'SELECT COUNT(*) FROM raw.transactions WHERE "Is Laundering" = 1'
        ).fetchone()[0]
        print(f"Total laundering rows in DB: {laundering_total:,}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
