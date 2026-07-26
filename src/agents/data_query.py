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
import re
from typing import Literal

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

    schema_name: Literal["raw", "splits", "all"] = Field(
        default="all",
        description=(
            "Which schema to inspect: 'raw', 'splits', or 'all' (default). "
            "Returns table names and column definitions."
        ),
    )


# ── Tool implementations ─────────────────────────────────────────────────────


def query_database(input: QueryInput) -> str:
    """Execute a read-only SQL query against DuckDB and return formatted results.

    Only one SELECT or WITH query is permitted. Results are capped in the
    database before they are materialised in Python.
    """
    import duckdb
    # Strip comments before validating a single query expression.
    sql_no_comments = re.sub(r"--[^\n]*", " ", input.sql)
    sql_no_comments = re.sub(r"/\*.*?\*/", " ", sql_no_comments, flags=re.DOTALL)
    sql = sql_no_comments.strip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if not sql or ";" in sql or not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ValueError("Only one read-only SELECT or WITH query is allowed.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(f"SELECT * FROM ({sql}) AS sentinel_result LIMIT 100").fetchall()
        columns = [desc[0] for desc in con.description] if con.description else []
    finally:
        con.close()

    if not rows:
        return "(empty result set)"

    # Format as a simple text table
    header = " | ".join(str(c) for c in columns)
    separator = "-+-".join("-" * len(str(c)) for c in columns)
    lines = [header, separator]
    for row in rows:
        lines.append(" | ".join(str(v) for v in row))
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
