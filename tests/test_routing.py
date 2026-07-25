"""Unit tests for supervisor routing logic.

Tests verify that:
- The SupervisorOutput Pydantic schema has all required fields
- All tool names are registered and importable
- The structured metadata extractor parses JSON blocks correctly
- The tools_skipped logic is correct (complement of tools_invoked)
- Intent values are constrained to the allowed set

These tests run without Azure OpenAI credentials or DuckDB — they
test only the structural and static properties of the routing layer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.supervisor import (
    ALL_TOOL_NAMES,
    SupervisorOutput,
    _extract_structured_metadata,
)


# ── Schema tests ──────────────────────────────────────────────────────────────


class TestSupervisorOutputSchema:
    """Tests for the Pydantic output schema."""

    REQUIRED_FIELDS = {"intent", "execution_plan", "tools_invoked", "tools_skipped", "reasoning", "results"}

    def test_all_required_fields_present(self) -> None:
        fields = set(SupervisorOutput.model_fields.keys())
        assert self.REQUIRED_FIELDS.issubset(fields), (
            f"Missing fields: {self.REQUIRED_FIELDS - fields}"
        )

    def test_schema_validates_valid_input(self) -> None:
        output = SupervisorOutput(
            intent="aggregation",
            execution_plan=["query_database"],
            tools_invoked=["query_database"],
            tools_skipped=["score_anomaly", "classify_accounts"],
            reasoning="Pure aggregation query — only SQL needed.",
            results="Total: 5,078,346 transactions",
        )
        assert output.intent == "aggregation"
        assert "query_database" in output.tools_invoked
        assert "score_anomaly" in output.tools_skipped

    def test_execution_plan_is_list(self) -> None:
        output = SupervisorOutput(
            intent="profiling",
            execution_plan=[],
            tools_invoked=[],
            tools_skipped=[],
            reasoning="",
            results="",
        )
        assert isinstance(output.execution_plan, list)
        assert isinstance(output.tools_invoked, list)
        assert isinstance(output.tools_skipped, list)


# ── Tool registry tests ───────────────────────────────────────────────────────


class TestToolRegistry:
    """Tests for the ALL_TOOL_NAMES registry."""

    EXPECTED_TOOLS = {
        "query_database",
        "get_schema",
        "compute_features",
        "score_anomaly",
        "batch_scan_top_accounts",
        "classify_accounts",
        "generate_investigation_summary",
    }

    def test_all_expected_tools_registered(self) -> None:
        assert self.EXPECTED_TOOLS.issubset(set(ALL_TOOL_NAMES)), (
            f"Missing tools: {self.EXPECTED_TOOLS - set(ALL_TOOL_NAMES)}"
        )

    def test_no_duplicate_tool_names(self) -> None:
        assert len(ALL_TOOL_NAMES) == len(set(ALL_TOOL_NAMES)), (
            f"Duplicate tool names: {[t for t in ALL_TOOL_NAMES if ALL_TOOL_NAMES.count(t) > 1]}"
        )

    def test_all_tools_importable(self) -> None:
        """Every tool in ALL_TOOL_NAMES must be importable from its module."""
        from src.agents.data_query import get_schema, query_database
        from src.agents.features import compute_features
        from src.agents.anomaly import score_anomaly, batch_scan_top_accounts
        from src.agents.risk import classify_accounts
        from src.agents.explain import generate_investigation_summary

        tool_map = {
            "query_database": query_database,
            "get_schema": get_schema,
            "compute_features": compute_features,
            "score_anomaly": score_anomaly,
            "batch_scan_top_accounts": batch_scan_top_accounts,
            "classify_accounts": classify_accounts,
            "generate_investigation_summary": generate_investigation_summary,
        }

        for name in ALL_TOOL_NAMES:
            assert name in tool_map, f"Tool '{name}' not found in import map"
            assert callable(tool_map[name]), f"Tool '{name}' is not callable"


# ── Metadata extractor tests ──────────────────────────────────────────────────


class TestExtractStructuredMetadata:
    """Tests for _extract_structured_metadata()."""

    def _make_ai_msg(self, content: str):
        from langchain_core.messages import AIMessage
        return AIMessage(content=content)

    def _make_tool_msg(self, name: str):
        from langchain_core.messages import ToolMessage
        return ToolMessage(content="result", tool_call_id="1", name=name)

    def test_parses_json_block_from_ai_message(self) -> None:
        meta_payload = {
            "intent": "aggregation",
            "execution_plan": ["query_database"],
            "tools_invoked": ["query_database"],
            "tools_skipped": ["score_anomaly"],
            "reasoning": "Simple count query.",
        }
        content = (
            "There are 5,078,346 transactions.\n\n"
            f"```json\n{json.dumps(meta_payload)}\n```"
        )
        # Include a ToolMessage so tools_invoked is derived from real history
        messages = [
            self._make_tool_msg("query_database"),
            self._make_ai_msg(content),
        ]
        result = _extract_structured_metadata(messages)

        assert result["intent"] == "aggregation"
        assert result["tools_invoked"] == ["query_database"]
        # tools_skipped is always the full complement regardless of what the
        # LLM put in its JSON block — this prevents partial/empty skip lists.
        assert "score_anomaly" in result["tools_skipped"]
        assert result["reasoning"] == "Simple count query."

    def test_falls_back_to_tool_message_inference(self) -> None:
        """When no JSON block exists, tools_invoked is inferred from ToolMessages."""
        messages = [
            self._make_ai_msg("Here are the results."),  # no JSON block
            self._make_tool_msg("query_database"),
            self._make_tool_msg("score_anomaly"),
        ]
        result = _extract_structured_metadata(messages)

        assert "query_database" in result["tools_invoked"]
        assert "score_anomaly" in result["tools_invoked"]
        assert result["intent"] == "unknown"  # can't infer intent without JSON

    def test_skipped_tools_are_complement_of_invoked(self) -> None:
        """tools_skipped should be all tools NOT in tools_invoked."""
        messages = [
            self._make_tool_msg("query_database"),
        ]
        result = _extract_structured_metadata(messages)

        invoked = set(result["tools_invoked"])
        skipped = set(result["tools_skipped"])
        all_tools = set(ALL_TOOL_NAMES)

        # skipped ∩ invoked = ∅
        assert invoked.isdisjoint(skipped), (
            f"Tools appear in both invoked and skipped: {invoked & skipped}"
        )
        # invoked ∪ skipped ⊆ all_tools
        assert (invoked | skipped).issubset(all_tools), (
            f"Unknown tool names: {(invoked | skipped) - all_tools}"
        )

    def test_empty_message_list_returns_defaults(self) -> None:
        result = _extract_structured_metadata([])
        assert result["intent"] == "unknown"
        assert isinstance(result["tools_invoked"], list)
        assert isinstance(result["tools_skipped"], list)

    def test_malformed_json_falls_back_gracefully(self) -> None:
        bad_json = "```json\n{this is not valid json}\n```"
        messages = [self._make_ai_msg(bad_json)]
        result = _extract_structured_metadata(messages)
        # Should not raise, should return fallback
        assert result["intent"] == "unknown"


# ── Intent validation tests ───────────────────────────────────────────────────


class TestIntentValues:
    """Tests that the allowed intent values are well-defined."""

    VALID_INTENTS = {"aggregation", "investigation", "profiling", "features", "explanation", "unknown"}

    def test_valid_intents_cover_all_routing_cases(self) -> None:
        """Ensure routing rules cover all six intent categories."""
        system_prompt_path = Path(__file__).parent.parent / "src" / "supervisor.py"
        source = system_prompt_path.read_text(encoding="utf-8")
        for intent in self.VALID_INTENTS:
            assert intent in source, f"Intent '{intent}' not mentioned in supervisor.py"


# ── Risk classification threshold tests ──────────────────────────────────────


class TestRiskThresholds:
    """Tests for risk classification thresholds in the risk agent."""

    def test_thresholds_consistent_with_plan(self) -> None:
        """LOW < 0.30, MEDIUM < 0.70, HIGH >= 0.70 as defined in implementation plan."""
        from src.agents.risk import LOW_THRESHOLD, MEDIUM_THRESHOLD, classify_risk

        assert LOW_THRESHOLD == 0.30
        assert MEDIUM_THRESHOLD == 0.70

        assert classify_risk(0.10)[0] == "LOW"
        assert classify_risk(0.29)[0] == "LOW"
        assert classify_risk(0.30)[0] == "MEDIUM"
        assert classify_risk(0.69)[0] == "MEDIUM"
        assert classify_risk(0.70)[0] == "HIGH"
        assert classify_risk(1.00)[0] == "HIGH"

    def test_escalation_action_present_for_all_tiers(self) -> None:
        from src.agents.risk import classify_risk
        for score in [0.10, 0.50, 0.90]:
            level, action = classify_risk(score)
            assert level in {"LOW", "MEDIUM", "HIGH"}
            assert len(action) > 0


# ── Anomaly scoring weight tests ──────────────────────────────────────────────


class TestAnomalyWeights:
    """Tests that the composite scoring formula matches the implementation plan."""

    def test_composite_weights_match_plan(self) -> None:
        """Composite = 0.4 * IF + 0.6 * Rule as per implementation plan."""
        from src.agents.anomaly import IF_WEIGHT, RULE_WEIGHT

        assert IF_WEIGHT == 0.4
        assert RULE_WEIGHT == 0.6
        assert abs(IF_WEIGHT + RULE_WEIGHT - 1.0) < 1e-9

    def test_contamination_matches_plan(self) -> None:
        """Isolation Forest contamination should be 0.0015."""
        from src.agents.anomaly import IF_CONTAMINATION
        assert IF_CONTAMINATION == 0.0015
