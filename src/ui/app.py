"""Sentinel AML Detection — Streamlit Chat Dashboard.

Primary user interface for the Sentinel AML system.

Features
--------
- Chat input for natural-language AML investigation queries
- Visual execution trace (which agents were called and why)
- Data tables rendered from Data Query agent results
- Risk gauge (High / Medium / Low colour-coded indicator)
- Network graph (pyvis) for fan-out / cycle visualisation
- Transaction timeline chart (Altair)
- Explainability panel showing the plain-English AML Investigation Summary

Usage
-----
    uv run streamlit run src/ui/app.py
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ── Bootstrap ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from langgraph.checkpoint.memory import MemorySaver
from src.supervisor import run_supervisor

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sentinel AML",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "checkpointer" not in st.session_state:
    st.session_state.checkpointer = MemorySaver()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "ui-session-1"
if "turn_counter" not in st.session_state:
    st.session_state.turn_counter = 0

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=72)
    st.title("Sentinel AML")
    st.caption("AI-powered Anti-Money Laundering Detection")
    st.divider()

    st.subheader("Session")
    st.write(f"Thread: `{st.session_state.thread_id}`")
    st.write(f"Turns:  {st.session_state.turn_counter}")

    if st.button("🔄 New Session", width="stretch"):
        st.session_state.messages = []
        st.session_state.checkpointer = MemorySaver()
        st.session_state.turn_counter = 0
        st.session_state.thread_id = f"ui-session-{id(object())}"
        st.rerun()

    st.divider()
    st.subheader("Example Queries")
    examples = [
        "Investigate Account 8000EBD30 for laundering patterns",
        "Count total transactions over $10,000",
        "Show the currency distribution",
        "Check data quality — any missing values?",
        "Compute features for Account 8000EBD30",
        "What is the amount distribution on the training split?",
        "Show me the top 10 sender accounts",
    ]
    for ex in examples:
        if st.button(ex, width="stretch", key=f"ex_{ex[:20]}"):
            st.session_state["_prefill"] = ex

    st.divider()
    st.caption("Dataset: IBM HI-Small (5M transactions)")
    st.caption("LLM: Azure OpenAI GPT-5.4-mini")

# ── Risk level extraction ─────────────────────────────────────────────────────

# AML pattern keywords that must NOT be mistaken for risk-level labels.
# e.g. "SCATTER-GATHER" contains no risk word; but "HIGH RISK" or "Risk level: HIGH" do.
_RISK_LEVEL_RE = re.compile(
    r"(?:risk\s+level\s*[:=]\s*|risk\s*[:=]\s*|\boverall\s+risk\s*[:=]\s*)"
    r"(HIGH|MEDIUM|LOW)\b",
    re.IGNORECASE,
)
_RISK_VERDICT_RE = re.compile(
    r"\b(HIGH|MEDIUM|LOW)\s+RISK\b",
    re.IGNORECASE,
)


def extract_risk_level(result_text: str) -> str | None:
    """Extract the actual risk verdict from the result text.

    Uses anchored patterns — "Risk level: HIGH", "HIGH RISK" — so that
    pattern names like SCATTER-GATHER or section headers containing the
    word HIGH in other contexts don't trigger a false positive.
    Returns 'HIGH', 'MEDIUM', 'LOW', or None.
    """
    # Prefer "Risk level: X" phrasing (most unambiguous)
    m = _RISK_LEVEL_RE.search(result_text)
    if m:
        return m.group(1).upper()
    # Fall back to "X RISK" phrasing
    m = _RISK_VERDICT_RE.search(result_text)
    if m:
        return m.group(1).upper()
    return None


# ── Account ID extraction ─────────────────────────────────────────────────────

# Real IBM HI-Small account IDs are hex strings like 8000EBD30 — at least 7
# uppercase hex chars. This excludes common English words, AML pattern names
# (FAN-OUT, CYCLE, HIGH, etc.) and single-word tokens.
_ACCOUNT_ID_RE = re.compile(r"\b([0-9A-F]{7,})\b")


def extract_account_id(query: str) -> str | None:
    """Extract the first plausible account ID from the query text."""
    m = _ACCOUNT_ID_RE.search(query.upper())
    return m.group(1) if m else None


# ── Helper renderers ──────────────────────────────────────────────────────────


def render_risk_gauge(risk_level: str) -> None:
    """Render a colour-coded risk badge."""
    colours = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#27ae60"}
    icons = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    level = risk_level.upper()
    colour = colours.get(level, "#95a5a6")
    icon = icons.get(level, "⚪")

    st.markdown(
        f"""
        <div style="
            background:{colour}22;
            border:2px solid {colour};
            border-radius:8px;
            padding:12px 20px;
            text-align:center;
            margin:8px 0;
        ">
            <span style="font-size:2rem;">{icon}</span>
            <span style="font-size:1.5rem; font-weight:bold; color:{colour}; margin-left:8px;">
                {level} RISK
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_execution_trace(meta: dict) -> None:
    """Render the agent execution trace panel."""
    with st.expander("🔍 Execution Trace", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Intent detected**")
            st.code(meta.get("intent", "unknown"), language=None)
            st.markdown("**Reasoning**")
            st.info(meta.get("reasoning", "—") or "—")

        with col2:
            invoked = meta.get("tools_invoked", [])
            skipped = meta.get("tools_skipped", [])

            st.markdown("**Tools invoked**")
            for t in invoked:
                st.markdown(f"  ✅ `{t}`")
            if not invoked:
                st.markdown("  _none_")

            st.markdown("**Tools skipped**")
            for t in skipped:
                st.markdown(f"  ⏭️ `{t}`")
            if not skipped:
                st.markdown("  _none_")

        plan = meta.get("execution_plan", [])
        if plan:
            st.markdown("**Execution plan**")
            for i, step in enumerate(plan, 1):
                st.markdown(f"  {i}. `{step}`")


def _try_parse_table(text: str) -> pd.DataFrame | None:
    """Attempt to parse a pipe-delimited text table into a DataFrame."""
    lines = [
        ln
        for ln in text.strip().splitlines()
        if "|" in ln and not re.match(r"^[\-\+\s\|]+$", ln)
    ]
    if len(lines) < 2:
        return None
    try:
        header = [h.strip() for h in lines[0].split("|") if h.strip()]
        rows = []
        for line in lines[1:]:
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) == len(header):
                rows.append(cols)
        if rows:
            return pd.DataFrame(rows, columns=header)
    except Exception:
        pass
    return None


def render_data_table(result_text: str) -> None:
    """If the result contains a pipe-delimited table, render it as a dataframe."""
    df = _try_parse_table(result_text)
    if df is not None and not df.empty:
        with st.expander("📊 Data Table", expanded=True):
            st.dataframe(df, width="stretch")


def render_network_graph(result_text: str, account_id: str | None = None) -> None:
    """Build and render a pyvis network graph from account pairs in the result.

    Only uses real account IDs (7+ uppercase hex chars) — never AML keyword tokens
    like SCATTER, GATHER, HIGH, FAN, etc.
    """
    # Look for explicit "A -> B" edge notation first
    edges = re.findall(r"([0-9A-F]{7,})\s*[-–>]+\s*([0-9A-F]{7,})", result_text.upper())

    # Fall back: find all account-like tokens and connect them to the queried account
    if not edges and account_id:
        candidates = list(
            dict.fromkeys(
                m
                for m in _ACCOUNT_ID_RE.findall(result_text.upper())
                if m != account_id
            )
        )[:15]
        if candidates:
            edges = [(account_id, c) for c in candidates]

    if not edges:
        return

    try:
        from pyvis.network import Network

        net = Network(
            height="450px",
            width="100%",
            bgcolor="#0e1117",
            font_color=True,
            directed=True,
            notebook=False,
        )
        net.barnes_hut(spring_length=120, spring_strength=0.05)

        seen: set[str] = set()
        for src, dst in edges[:50]:
            for node in (src, dst):
                if node not in seen:
                    is_focus = node == account_id
                    net.add_node(
                        node,
                        label=node[:12],
                        color="#e74c3c" if is_focus else "#3498db",
                        size=22 if is_focus else 14,
                    )
                    seen.add(node)
            net.add_edge(src, dst, color="#95a5a6", arrows="to")

        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as f:
            tmp_path = f.name
        net.save_graph(tmp_path)
        html_content = Path(tmp_path).read_text(encoding="utf-8")
        os.unlink(tmp_path)

        with st.expander("🕸️ Network Graph", expanded=True):
            st.html(html_content)

    except Exception as exc:
        st.caption(f"Network graph unavailable: {exc}")


def render_timeline(result_text: str) -> None:
    """Render a transaction timeline if ≥3 ISO timestamps are present."""
    ts_pattern = re.compile(r"(\d{4}[/\-]\d{2}[/\-]\d{2}[\sT]\d{2}:\d{2})")
    timestamps = ts_pattern.findall(result_text)
    if len(timestamps) < 3:
        return

    try:
        dates = pd.to_datetime(timestamps, errors="coerce").dropna()
        if len(dates) < 3:
            return
        df = pd.DataFrame({"date": dates, "count": 1})
        df_agg = df.groupby(df["date"].dt.date).count().reset_index()
        df_agg.columns = ["date", "count"]
        df_agg["date"] = pd.to_datetime(df_agg["date"])

        chart = (
            alt.Chart(df_agg)
            .mark_area(opacity=0.7, color="#3498db")
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("count:Q", title="Transactions"),
                tooltip=["date:T", "count:Q"],
            )
            .properties(title="Transaction Timeline", height=200)
        )
        with st.expander("📅 Transaction Timeline", expanded=False):
            st.altair_chart(chart, width="stretch")
    except Exception:
        pass


def render_explainability_panel(
    result_text: str, is_investigation: bool = False
) -> None:
    """Display the AML Investigation Summary panel.

    Only shown for investigation queries where generate_investigation_summary
    was invoked. Does NOT duplicate the main answer — it surfaces the structured
    report in a dedicated collapsible panel only when the content warrants it
    (i.e. when the LLM produced a formal investigation summary).
    """
    if not is_investigation:
        return

    # The explain agent reliably produces sections like ## Result / ## Interpretation
    # or explicit risk level lines. Only expand the panel when those markers are present.
    has_structured_summary = any(
        kw in result_text
        for kw in [
            "## Result",
            "## Interpretation",
            "## Recommendation",
            "AML Investigation Summary",
            "Risk Verdict",
            "Triggered Rules",
            "Triggered rules",
        ]
    )
    if not has_structured_summary:
        return

    with st.expander(
        "🔎 Explainability Panel — AML Investigation Summary", expanded=True
    ):
        st.markdown(result_text)


# ── Panel orchestration ───────────────────────────────────────────────────────


def render_all_panels(answer: str, meta: dict, query: str) -> None:
    """Render all result panels for a single assistant response."""
    tools_invoked = set(meta.get("tools_invoked", []))
    is_investigation = bool(
        tools_invoked
        & {"score_anomaly", "classify_accounts", "generate_investigation_summary"}
    )

    render_execution_trace(meta)

    # Risk gauge — only shown for investigation queries, using anchored extraction
    if is_investigation:
        risk = extract_risk_level(answer)
        if risk:
            render_risk_gauge(risk)

    # Explainability panel — only for investigation queries, avoids duplication
    render_explainability_panel(answer, is_investigation=is_investigation)

    # Data table — shown when aggregation/EDA tools returned tabular data
    render_data_table(answer)

    # Network graph — only when a real account ID was queried
    account_id = extract_account_id(query)
    if account_id:
        render_network_graph(answer, account_id)

    render_timeline(answer)


# ── Main chat interface ───────────────────────────────────────────────────────

st.title("🛡️ Sentinel AML — Investigation Dashboard")
st.caption("Ask anything about transactions, accounts, or laundering patterns.")

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("meta"):
            render_all_panels(
                answer=msg["meta"].get("results", ""),
                meta=msg["meta"],
                query=msg.get("query", ""),
            )

# Handle pre-fill from sidebar example buttons
prefill = st.session_state.pop("_prefill", None)

# Chat input
user_query = st.chat_input(
    "e.g. Investigate Account 8000EBD30 for laundering patterns…"
)
if not user_query and prefill:
    user_query = prefill

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Routing query through AML agents…"):
            try:
                result = run_supervisor(
                    user_query,
                    thread_id=st.session_state.thread_id,
                    checkpointer=st.session_state.checkpointer,
                )
                st.session_state.turn_counter += 1

                meta = {
                    "intent": result.get("intent", "unknown"),
                    "execution_plan": result.get("execution_plan", []),
                    "tools_invoked": result.get("tools_invoked", []),
                    "tools_skipped": result.get("tools_skipped", []),
                    "reasoning": result.get("reasoning", ""),
                    "results": result.get("results", ""),
                }

                answer = result.get("results", "_No response from supervisor._")

                # For investigation queries the explainability panel already renders
                # the full structured summary — show a brief inline header only.
                tools_invoked = set(meta.get("tools_invoked", []))
                is_investigation = bool(
                    tools_invoked
                    & {
                        "score_anomaly",
                        "classify_accounts",
                        "generate_investigation_summary",
                    }
                )
                if is_investigation:
                    # Show just the risk verdict line and first paragraph inline;
                    # the full report lives in the Explainability Panel below.
                    risk = extract_risk_level(answer)
                    if risk:
                        # Pull the first substantive paragraph as a summary lead
                        first_para = next(
                            (
                                p.strip()
                                for p in answer.split("\n\n")
                                if p.strip() and not p.startswith("#")
                            ),
                            answer[:300],
                        )
                        st.markdown(first_para)
                    else:
                        st.markdown(answer)
                else:
                    st.markdown(answer)

                render_all_panels(answer, meta, user_query)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "meta": meta,
                        "query": user_query,
                    }
                )

            except Exception as exc:
                error_msg = f"⚠️ Error processing query: {exc}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_msg,
                        "meta": None,
                        "query": user_query,
                    }
                )
