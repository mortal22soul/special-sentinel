"""Parse HI-Small_Patterns.txt laundering blocks into a labeled transaction CSV.

Format overview
---------------
The file interleaves marker lines with CSV transaction rows:

    BEGIN LAUNDERING ATTEMPT - <PATTERN>: <optional description>
    Timestamp,From Bank,Account,To Bank,Account,Amount Received,...
    ...
    END LAUNDERING ATTEMPT - <PATTERN>

Each block's transaction rows inherit the `<PATTERN>` label.
All laundering rows in this file carry `Is Laundering = 1`.

Outputs
-------
1. A ``pattern_labels.csv`` with every laundering transaction plus a
   ``pattern_type`` column.
2. A ``joined_labeled.csv`` that merges ``pattern_labels.csv`` onto the
   full ``HI-Small_Trans.csv`` (rows without a pattern label get
   ``UNLABELED``).

Validation
----------
The script fails loudly when the parsed block count or pattern-type
counts don't match the expected 370 blocks.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

PATTERNS_FILE = Path("data/HI-Small_Patterns.txt")
TRANS_FILE = Path("data/HI-Small_Trans.csv")
OUT_LABELS = Path("data/pattern_labels.csv")
OUT_JOINED = Path("data/joined_labeled.csv")

EXPECTED_BLOCKS = 370  # from dataset audit / implementation plan

BEGIN_RE = re.compile(r"^BEGIN LAUNDERING ATTEMPT\s*-\s*(\S+)", re.IGNORECASE)
END_RE = re.compile(r"^END LAUNDERING ATTEMPT\s*-\s*(\S+)", re.IGNORECASE)

# ── Helpers ───────────────────────────────────────────────────────────────────


def parse_patterns(path: Path) -> tuple[list[dict], Counter]:
    """Return (rows, counts) from the patterns file.

    Each row dict has the CSV fields plus a ``pattern_type`` key.
    Raises ``ValueError`` on validation failure.
    """
    rows: list[dict] = []
    block_counts: Counter = Counter()
    current_pattern: str | None = None
    in_block = False
    block_row_counts: Counter = Counter()

    with path.open(encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n\r")

            # ── Block markers ─────────────────────────────────────────────
            begin_match = BEGIN_RE.match(line)
            if begin_match:
                raw = begin_match.group(1).upper()
                current_pattern = raw.rstrip(":")
                in_block = True
                block_counts[current_pattern] += 1
                continue

            end_match = END_RE.match(line)
            if end_match:
                if not in_block:
                    raise ValueError(
                        f"Unexpected END marker at line {lineno} (no active block)"
                    )
                in_block = False
                continue

            # ── Data rows (only inside a block) ────────────────────────────
            if in_block and current_pattern is not None and line.strip():
                # The transaction rows follow the same CSV header format as
                # HI-Small_Trans.csv but without the header row repeated.
                reader = csv.reader([line])
                fields = next(reader)

                if len(fields) < 11:
                    raise ValueError(
                        f"Line {lineno}: expected 11 CSV columns, got {len(fields)}: {line!r}"
                    )

                row = {
                    "Timestamp": fields[0],
                    "From Bank": fields[1],
                    "Account": fields[2],
                    "To Bank": fields[3],
                    "Account.1": fields[4],
                    "Amount Received": float(fields[5]),
                    "Receiving Currency": fields[6],
                    "Amount Paid": float(fields[7]),
                    "Payment Currency": fields[8],
                    "Payment Format": fields[9],
                    "Is Laundering": int(fields[10]),
                    "pattern_type": current_pattern,
                }
                rows.append(row)
                block_row_counts[current_pattern] += 1

    if in_block:
        raise ValueError("File ended while inside an unclosed block")

    return rows, block_counts


def write_labels(rows: list[dict], dest: Path) -> None:
    """Write pattern-labeled rows to a CSV."""
    fieldnames = [
        "Timestamp", "From Bank", "Account", "To Bank", "Account.1",
        "Amount Received", "Receiving Currency", "Amount Paid",
        "Payment Currency", "Payment Format", "Is Laundering",
        "pattern_type",
    ]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def join_with_full_transactions(labels_path: Path, trans_path: Path, dest: Path) -> None:
    """Merge labeled laundering rows onto the full transaction CSV.

    Rows present in the labels file get their ``pattern_type``.
    All other rows get ``UNLABELED`` (even when ``Is Laundering = 1`` —
    those are the ~1,600 unlabeled positives referenced in CLAUDE.md).

    The full CSV has duplicate column names (both from- and to-account
    are called ``Account``), so we work with column indices rather than
    DictReader field names.
    """
    # Build a lookup keyed by (Timestamp, From Bank, From Account, To Bank, To Account)
    label_lookup: dict[tuple[str, str, str, str, str], str] = {}

    with labels_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (
                row["Timestamp"],
                row["From Bank"],
                row["Account"],
                row["To Bank"],
                row["Account.1"],
            )
            label_lookup[key] = row["pattern_type"]

    with trans_path.open(encoding="utf-8") as fh_in, dest.open("w", newline="", encoding="utf-8") as fh_out:
        reader = csv.reader(fh_in)
        header = next(reader)
        # Duplicate header handling: rename the second "Account" to "Account.1"
        # so the output CSV has a distinct column name for the to-account.
        renamed_header = []
        seen_account = 0
        for col in header:
            if col == "Account":
                seen_account += 1
                renamed_header.append("Account" if seen_account == 1 else "Account.1")
            else:
                renamed_header.append(col)
        out_header = renamed_header + ["pattern_type"]
        writer = csv.writer(fh_out)
        writer.writerow(out_header)

        # Indices for the trailing label columns
        idx_ts = renamed_header.index("Timestamp")
        idx_from_bank = renamed_header.index("From Bank")
        idx_from_acct = renamed_header.index("Account")
        idx_to_bank = renamed_header.index("To Bank")
        idx_to_acct = renamed_header.index("Account.1")

        for fields in reader:
            key = (
                fields[idx_ts],
                fields[idx_from_bank],
                fields[idx_from_acct],
                fields[idx_to_bank],
                fields[idx_to_acct],
            )
            pattern = label_lookup.get(key, "UNLABELED")
            writer.writerow(list(fields) + [pattern])


def main() -> None:
    if not PATTERNS_FILE.exists():
        sys.exit(f"ERROR: {PATTERNS_FILE} not found. Place HI-Small_Patterns.txt in data/.")
    if not TRANS_FILE.exists():
        sys.exit(f"ERROR: {TRANS_FILE} not found. Place HI-Small_Trans.csv in data/.")

    print("=" * 60)
    print("Parsing", PATTERNS_FILE)
    print("=" * 60)

    rows, block_counts = parse_patterns(PATTERNS_FILE)

    total_blocks = sum(block_counts.values())
    print(f"\nFound {total_blocks} laundering blocks:")
    for pattern, count in sorted(block_counts.items()):
        print(f"  {pattern:20s} {count:>5}")

    # ── Validation ────────────────────────────────────────────────────────
    if total_blocks != EXPECTED_BLOCKS:
        raise ValueError(
            f"Block count mismatch: expected {EXPECTED_BLOCKS}, got {total_blocks}"
        )

    print(f"\nTotal laundering rows: {len(rows)}")

    # Confirm every laundering row has a pattern label
    unlabeled = [r for r in rows if not r["pattern_type"]]
    if unlabeled:
        raise ValueError(f"{len(unlabeled)} laundering rows have no pattern_type!")

    # ── Write labeled CSV ────────────────────────────────────────────────
    write_labels(rows, OUT_LABELS)
    print(f"\nWritten: {OUT_LABELS}  ({len(rows)} rows)")

    # ── Join with full transactions ──────────────────────────────────────
    print(f"\nJoining with {TRANS_FILE} …")
    join_with_full_transactions(OUT_LABELS, TRANS_FILE, OUT_JOINED)
    print(f"Written: {OUT_JOINED}")


if __name__ == "__main__":
    main()
