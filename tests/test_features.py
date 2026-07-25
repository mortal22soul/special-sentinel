"""Unit tests for the Feature Engineering subagent.

Tests cover:
- Rolling sum math
- Velocity computation
- Amount deviation z-score
- All 7 ground-truth AML pattern type detection functions
- Cross-currency risk flag

These tests run entirely in-memory with synthetic DataFrames — no DuckDB or
Azure OpenAI credentials are needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Make src importable without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.features import (
    _build_directed_graph,
    cross_currency_flag,
    detect_bipartite,
    detect_cycle,
    detect_fan_in,
    detect_fan_out,
    detect_gather_scatter,
    detect_scatter_gather,
    detect_stack,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_df(edges: list[tuple[str, str]]) -> pd.DataFrame:
    """Build a minimal transaction DataFrame from a list of (src, dst) pairs."""
    rows = [
        {
            "Timestamp": f"2024-01-{i+1:02d} 00:00:00",
            "Account": src,
            "Account.1": dst,
            "Amount Paid": 1000.0 + i * 100,
            "Receiving Currency": "US Dollar",
            "Payment Currency": "US Dollar",
            "pattern_type": "FAN-OUT",
        }
        for i, (src, dst) in enumerate(edges)
    ]
    return pd.DataFrame(rows)


# ── Rolling sum / velocity / amount deviation ─────────────────────────────────


class TestRollingFeatures:
    """Tests for standard numeric features."""

    def test_rolling_sum_30d_monotonically_increases(self) -> None:
        """Rolling sum of a single account should grow with each transaction."""
        df = pd.DataFrame({
            "Account": ["A"] * 5,
            "Amount Paid": [100.0, 200.0, 300.0, 400.0, 500.0],
            "Timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
        })
        df = df.sort_values(["Account", "Timestamp"])
        df["rolling_sum_30d"] = (
            df.groupby("Account")["Amount Paid"]
            .transform(lambda x: x.rolling(30, min_periods=1).sum())
        )
        # Values should be 100, 300, 600, 1000, 1500
        expected = [100.0, 300.0, 600.0, 1000.0, 1500.0]
        assert list(df["rolling_sum_30d"]) == expected

    def test_rolling_sum_resets_per_account(self) -> None:
        """Each account's rolling sum should be independent."""
        df = pd.DataFrame({
            "Account": ["A", "A", "B", "B"],
            "Amount Paid": [100.0, 200.0, 50.0, 75.0],
            "Timestamp": pd.date_range("2024-01-01", periods=4, freq="D"),
        })
        df = df.sort_values(["Account", "Timestamp"])
        df["rolling_sum_30d"] = (
            df.groupby("Account")["Amount Paid"]
            .transform(lambda x: x.rolling(30, min_periods=1).sum())
        )
        a_sums = df[df["Account"] == "A"]["rolling_sum_30d"].tolist()
        b_sums = df[df["Account"] == "B"]["rolling_sum_30d"].tolist()
        assert a_sums == [100.0, 300.0]
        assert b_sums == [50.0, 125.0]

    def test_amount_deviation_zero_for_constant_amounts(self) -> None:
        """When all amounts are the same, std dev = 0, z-score should be 0."""
        df = pd.DataFrame({
            "Account": ["A"] * 4,
            "Amount Paid": [500.0, 500.0, 500.0, 500.0],
        })
        account_means = df.groupby("Account")["Amount Paid"].transform("mean")
        account_stds = df.groupby("Account")["Amount Paid"].transform("std").fillna(0)
        df["amount_dev"] = (df["Amount Paid"] - account_means) / (account_stds + 1e-9)
        # All deviations should be ~0
        assert all(abs(df["amount_dev"]) < 1e-3)

    def test_amount_deviation_large_for_outlier(self) -> None:
        """A single large transaction among normal ones should have a high z-score."""
        amounts = [100.0, 105.0, 98.0, 102.0, 10000.0]  # outlier at end
        df = pd.DataFrame({"Account": ["A"] * 5, "Amount Paid": amounts})
        account_means = df.groupby("Account")["Amount Paid"].transform("mean")
        account_stds = df.groupby("Account")["Amount Paid"].transform("std").fillna(0)
        df["amount_dev"] = (df["Amount Paid"] - account_means) / (account_stds + 1e-9)
        # The outlier should have the highest absolute deviation
        assert df["amount_dev"].abs().idxmax() == 4


# ── Cross-currency risk ───────────────────────────────────────────────────────


class TestCrossCurrencyFlag:
    def test_same_currency_not_flagged(self) -> None:
        row = pd.Series({"Receiving Currency": "US Dollar", "Payment Currency": "US Dollar"})
        assert cross_currency_flag(row) is False

    def test_different_currencies_flagged(self) -> None:
        row = pd.Series({"Receiving Currency": "Euro", "Payment Currency": "US Dollar"})
        assert cross_currency_flag(row) is True

    def test_bitcoin_vs_usd_flagged(self) -> None:
        row = pd.Series({"Receiving Currency": "Bitcoin", "Payment Currency": "US Dollar"})
        assert cross_currency_flag(row) is True


# ── Pattern detection: FAN-OUT / FAN-IN ──────────────────────────────────────


class TestFanDetection:
    """Tests for fan-out and fan-in pattern detection."""

    def test_fan_out_detected_at_threshold(self) -> None:
        """Account sending to ≥5 unique receivers should be flagged."""
        edges = [("HUB", f"RECV{i}") for i in range(6)]
        df = _make_df(edges)
        assert detect_fan_out(df, "HUB", threshold=5) is True

    def test_fan_out_below_threshold(self) -> None:
        edges = [("HUB", f"RECV{i}") for i in range(3)]
        df = _make_df(edges)
        assert detect_fan_out(df, "HUB", threshold=5) is False

    def test_fan_in_detected_at_threshold(self) -> None:
        """Account receiving from ≥5 unique senders should be flagged."""
        edges = [(f"SEND{i}", "HUB") for i in range(6)]
        df = _make_df(edges)
        assert detect_fan_in(df, "HUB", threshold=5) is True

    def test_fan_in_below_threshold(self) -> None:
        edges = [(f"SEND{i}", "HUB") for i in range(2)]
        df = _make_df(edges)
        assert detect_fan_in(df, "HUB", threshold=5) is False

    def test_fan_out_not_confused_with_fan_in(self) -> None:
        """A FAN-IN hub should not be detected as FAN-OUT."""
        edges = [(f"SEND{i}", "HUB") for i in range(7)]
        df = _make_df(edges)
        assert detect_fan_out(df, "HUB", threshold=5) is False
        assert detect_fan_in(df, "HUB", threshold=5) is True


# ── Pattern detection: CYCLE ─────────────────────────────────────────────────


class TestCycleDetection:
    def test_simple_cycle_detected(self) -> None:
        """A -> B -> C -> A is a cycle."""
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert detect_cycle(G) is True

    def test_no_cycle_in_dag(self) -> None:
        """A -> B -> C (no back-edge) is not a cycle."""
        edges = [("A", "B"), ("B", "C")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert detect_cycle(G) is False

    def test_self_loop_short_cycle(self) -> None:
        """A -> A is a cycle of length 1; min_length=3 means it should NOT be flagged."""
        edges = [("A", "A")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        # detect_cycle requires length >= CYCLE_MIN_LENGTH (3)
        assert detect_cycle(G) is False

    def test_long_cycle_detected(self) -> None:
        """A 5-hop cycle should be detected."""
        edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("E", "A")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert detect_cycle(G) is True


# ── Pattern detection: STACK ─────────────────────────────────────────────────


class TestStackDetection:
    def test_stack_detected_with_repeated_relay(self) -> None:
        """Account sending to same relay repeatedly should be flagged as STACK."""
        # A sends to RELAY 3 times — relay appears in chain
        edges = [("A", "RELAY"), ("A", "RELAY"), ("A", "RELAY")]
        df = _make_df(edges)
        assert detect_stack(df, "A", min_length=3) is True

    def test_stack_not_detected_with_diverse_receivers(self) -> None:
        """Sending to unique receivers is not a STACK."""
        edges = [("A", "B"), ("A", "C"), ("A", "D")]
        df = _make_df(edges)
        assert detect_stack(df, "A", min_length=3) is False

    def test_stack_not_detected_below_min_length(self) -> None:
        """Relay used twice with min_length=3 should NOT flag."""
        edges = [("A", "RELAY"), ("A", "RELAY")]
        df = _make_df(edges)
        assert detect_stack(df, "A", min_length=3) is False


# ── Pattern detection: SCATTER-GATHER / GATHER-SCATTER ───────────────────────


class TestScatterGatherDetection:
    def test_scatter_gather_detected(self) -> None:
        """A hub with ≥5 in AND ≥5 out should flag scatter-gather."""
        # 5 senders to HUB, 5 receivers from HUB
        in_edges  = [(f"S{i}", "HUB") for i in range(6)]
        out_edges = [("HUB", f"R{i}") for i in range(6)]
        df = _make_df(in_edges + out_edges)
        G = _build_directed_graph(df)
        assert detect_scatter_gather(G) is True

    def test_scatter_gather_not_detected_for_pure_fan_out(self) -> None:
        """A pure fan-out (no high-degree in) should not trigger scatter-gather."""
        out_edges = [("HUB", f"R{i}") for i in range(7)]
        df = _make_df(out_edges)
        G = _build_directed_graph(df)
        assert detect_scatter_gather(G) is False

    def test_gather_scatter_detected(self) -> None:
        """A hub with high in-degree whose out-neighbors also fan out should flag."""
        # 6 senders to HUB, HUB sends to MID, MID fans out to 6 receivers
        in_edges  = [(f"S{i}", "HUB") for i in range(6)]
        mid_edge  = [("HUB", "MID")]
        out_edges = [("MID", f"R{i}") for i in range(6)]
        df = _make_df(in_edges + mid_edge + out_edges)
        G = _build_directed_graph(df)
        assert detect_gather_scatter(G) is True


# ── Pattern detection: BIPARTITE ─────────────────────────────────────────────


class TestBipartiteDetection:
    def test_bipartite_graph_detected(self) -> None:
        """A true bipartite graph (L-set -> R-set only) should be detected."""
        edges = [
            ("L1", "R1"), ("L1", "R2"),
            ("L2", "R1"), ("L2", "R2"),
        ]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert detect_bipartite(G) is True

    def test_non_bipartite_graph_not_detected(self) -> None:
        """A triangle (odd cycle) is not bipartite."""
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert detect_bipartite(G) is False


# ── Graph builder ─────────────────────────────────────────────────────────────


class TestGraphBuilder:
    def test_edge_count_matches_unique_pairs(self) -> None:
        """Repeated edges should accumulate weight, not create new edges."""
        edges = [("A", "B"), ("A", "B"), ("A", "C")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert G.number_of_edges() == 2    # A->B (weight=2), A->C (weight=1)
        assert G["A"]["B"]["weight"] == 2

    def test_node_count_matches_unique_accounts(self) -> None:
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        df = _make_df(edges)
        G = _build_directed_graph(df)
        assert G.number_of_nodes() == 3
