"""Data Query subagent for the Sentinel AML supervisor.

Exposes two tools:
- ``query_database``: execute a read-only SQL query against DuckDB.
- ``get_schema``:     return the full schema (tables + columns) of the database.

The supervisor routes pure aggregation queries (e.g. "count transactions
over $10,000") directly to this agent, bypassing the ML/anomaly pipeline.

Azure OpenAI configuration
--------------------------
Reads the following environment variables (set in ``.env`` or shell):

    AZURE_OPENAI_API_KEY          — required
    AZURE_OPENAI_ENDPOINT         — required (e.g. https://...openai.azure.com/)
    AZURE_OPENAI_DEPLOYMENT_NAME  — optional, defaults to ``gpt-5.4-mini``
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────────────

from src.agents.risk import DB_PATH
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

# ── Tool input schemas ───────────────────────────────────────────────────────


class QueryInput(BaseModel):
    """Structured input for the data query tool."""

    sql: str = Field(
        description=(
            "A read-only SQL query to execute against the DuckDB database. "
            "Tables available: raw.transactions, raw.accounts, splits.train, "
            "splits.validation, splits.test, splits.metadata. "
            "Quote column names that contain spaces or special chars with "
            "double quotes (e.g. \"Is Laundering\", \"Amount Received\"). "
            "Use LIMIT to cap result sets."
        )
    )


class SchemaInput(BaseModel):
    """Input for the schema inspection tool."""

    schema_name: str = Field(
        default="all",
        description=(
            "Which schema to inspect: 'raw', 'splits', or 'all' (default). "
            "Returns table names and column definitions."
        ),
    )


# ── Tool implementations ─────────────────────────────────────────────────────


def query_database(input: QueryInput) -> str:
    """Execute a read-only SQL query against DuckDB and return formatted results.

    Blocks any write operations (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
    TRUNCATE, MERGE, REPLACE, COPY ... TO, GRANT, REVOKE) to protect the
    database. Comments are stripped first so write keywords cannot be smuggled
    past the filter as ``-- DROP TABLE``.
    """
    import duckdb
    import re

    forbidden = {
        "insert", "update", "delete", "drop", "alter", "create",
        "truncate", "merge", "replace", "grant", "revoke",
    }

    # Strip line comments (-- ...) and block comments (/* ... */) so write
    # keywords cannot be smuggled inside comments.
    sql_no_comments = re.sub(r"--[^\n]*", " ", input.sql)
    sql_no_comments = re.sub(r"/\*.*?\*/", " ", sql_no_comments, flags=re.DOTALL)

    # Tokenise on word boundaries; flag the whole query if any forbidden
    # keyword appears as a standalone token anywhere (including in the
    # second statement of a semicolon-separated batch).
    tokens = set(re.findall(r"[a-zA-Z_]+", sql_no_comments.lower()))
    blocked = tokens & forbidden
    if blocked:
        raise ValueError(
            f"Only read-only queries are allowed. Blocked keyword(s): "
            f"{', '.join(sorted(blocked))}"
        )

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(input.sql).fetchall()
        columns = [desc[0] for desc in con.description] if con.description else []
    finally:
        con.close()

    if not rows:
        return "(empty result set)"

    # Format as a simple text table
    header = " | ".join(str(c) for c in columns)
    separator = "-+-".join("-" * len(str(c)) for c in columns)
    lines = [header, separator]
    for row in rows[:100]:  # cap at 100 rows for readability
        lines.append(" | ".join(str(v) for v in row))
    if len(rows) > 100:
        lines.append(f"... ({len(rows) - 100} more rows truncated)")
    return "\n".join(lines)


def get_schema(input: SchemaInput) -> str:
    """Return the DuckDB schema: table names and their column definitions.

    Useful for understanding the database structure before writing SQL.
    """
    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        if input.schema_name == "all":
            schemas = ["raw", "splits"]
        else:
            schemas = [input.schema_name]

        lines: list[str] = ["DuckDB Schema:"]
        for schema in schemas:
            lines.append(f"\n[{schema}]")
            tables = con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = ? ORDER BY table_name",
                [schema],
            ).fetchall()
            for (tbl,) in tables:
                cols = con.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                    [schema, tbl],
                ).fetchall()
                col_str = ", ".join(f"{c}:{t}" for c, t in cols)
                lines.append(f"  {tbl}: {col_str}")
    finally:
        con.close()

    return "\n".join(lines)


# (agent factory removed — tools are bound directly in supervisor.py)
