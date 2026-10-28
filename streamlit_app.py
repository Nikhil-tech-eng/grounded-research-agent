from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from research_agent.agent import ResearchAgent
from research_agent.config import Settings
from research_agent.llm import OpenAIStructuredLLM
from research_agent.models import Confidence, FinalAnswer
from research_agent.tools import HttpResearchTools

st.set_page_config(
    page_title="Atlas Research Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          :root { --ink:#18333c; --muted:#5d737b; --mint:#dff7ec; --sky:#e7f3ff;
                  --peach:#fff0e5; --line:#dce9e8; --accent:#167b72; --paper:#fbfdfc; }
          .stApp { background: linear-gradient(130deg, #f7fcfa 0%, #f4f9ff 48%, #fffaf4 100%); color: var(--ink); }
          [data-testid="stSidebar"] { background: rgba(255,255,255,.82); border-right:1px solid var(--line); }
          .hero { padding:2.2rem 0 1.4rem; animation: rise .55s ease-out; }
          .eyebrow { color:var(--accent); font-weight:750; font-size:.8rem; letter-spacing:.12em; text-transform:uppercase; }
          .hero h1 { font-size:3rem; line-height:1.05; margin:.35rem 0 .65rem; letter-spacing:-.06em; color:var(--ink); }
          .hero p { color:var(--muted); font-size:1.08rem; max-width:700px; }
          .soft-card { background:rgba(255,255,255,.88); border:1px solid var(--line); border-radius:18px; padding:1.15rem 1.25rem; min-height:130px; box-shadow:0 10px 35px rgba(37,93,90,.06); }
          .soft-card h3 { margin:0 0 .5rem; color:var(--ink); font-size:1rem; }
          .soft-card p { color:var(--muted); margin:0; font-size:.91rem; }
          .step { display:flex; gap:.7rem; align-items:flex-start; padding:.65rem 0; border-bottom:1px solid #edf3f1; }
          .step:last-child { border:0; }
          .step-number { flex:0 0 1.7rem; height:1.7rem; border-radius:50%; background:var(--mint); color:var(--accent); font-weight:800; text-align:center; line-height:1.7rem; }
          .source-card { background:#fff; border-left:4px solid #72b8ad; border-radius:10px; padding:.8rem 1rem; margin:.55rem 0; box-shadow:0 3px 12px rgba(37,93,90,.05); }
          .metric-label { color:var(--muted); font-size:.8rem; }
          .stButton > button { background:var(--accent); color:white; border:0; border-radius:10px; font-weight:700; padding:.65rem 1.2rem; transition:transform .18s ease, box-shadow .18s ease; }
          .stButton > button:hover { background:#0e665f; transform:translateY(-2px); box-shadow:0 8px 18px rgba(22,123,114,.2); }
          @keyframes rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
          @media (prefers-reduced-motion: reduce) { .hero { animation:none; } .stButton > button { transition:none; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_example() -> FinalAnswer:
    data = json.loads((Path(__file__).parent / "examples" / "sample_success.json").read_text())
    return FinalAnswer.model_validate(data)


def build_agent() -> ResearchAgent:
    settings = Settings.from_env()
    return ResearchAgent(
        llm=OpenAIStructuredLLM(settings.openai_api_key, settings.model),
        tools=HttpResearchTools(settings.timeout_seconds, settings.tavily_api_key),
        max_sources=settings.max_sources,
    )


def confidence_badge(confidence: Confidence) -> str:
    colors = {Confidence.HIGH: "🟢", Confidence.MEDIUM: "🟡", Confidence.LOW: "🟠"}
    return f"{colors[confidence]} {confidence.value.title()} confidence"


def render_result(result: FinalAnswer) -> None:
    st.divider()
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("Research brief")
        st.caption(result.user_question)
    with top_right:
        st.markdown(f"#### {confidence_badge(result.confidence_level)}")

    st.info(result.short_answer, icon="💡")
    tabs = st.tabs(["✦ Findings", "◌ Research plan", "⌁ Sources", "⚑ Reliability"])

    with tabs[0]:
        if result.key_findings:
            for index, finding in enumerate(result.key_findings, start=1):
                st.markdown(f"**{index}. {finding.claim}**")
                st.write(finding.evidence)
                st.caption("Sources: " + " · ".join(str(url) for url in finding.source_urls))
        else:
            st.warning("No findings passed citation validation. The response stays intentionally conservative.")

    with tabs[1]:
        if result.plan.assumptions:
            st.caption("Assumptions: " + " · ".join(result.plan.assumptions))
        for step in result.plan.steps:
            st.markdown(
                f"<div class='step'><span class='step-number'>{step.id}</span><div><b>{step.objective}</b><br>"
                f"<span class='metric-label'>{step.tool.value} · {step.rationale}</span><br>"
                f"<code>{step.query}</code></div></div>",
                unsafe_allow_html=True,
            )

    with tabs[2]:
        for source in result.sources_used:
            st.markdown(
                f"<div class='source-card'><b>{source.title}</b><br><span class='metric-label'>"
                f"{source.publisher or 'Unknown publisher'} · {source.tool.value} · score {source.combined_score}</span><br>"
                f"{source.snippet[:320]}<br><a href='{source.url}' target='_blank'>Open source ↗</a></div>",
                unsafe_allow_html=True,
            )
        if not result.sources_used:
            st.warning("No usable sources were retrieved.")

    with tabs[3]:
        metrics = result.metrics
        one, two, three, four, five = st.columns(5)
        one.metric("Latency", f"{metrics.get('latency_ms', 0):,} ms")
        two.metric("Candidates", metrics.get("sources_gathered", metrics.get("source_count", 0)))
        three.metric("Sources kept", metrics.get("source_count", 0))
        four.metric("Filtered out", metrics.get("sources_filtered_out", 0))
        five.metric("Tool failures", metrics.get("tool_failure_count", 0))
        if result.failures:
            st.warning("Some workflow steps failed; the answer reflects partial evidence.")
            st.dataframe([failure.model_dump() for failure in result.failures], use_container_width=True)
        st.markdown("**Limitations & assumptions**")
        for item in result.limitations_or_assumptions:
            st.markdown(f"- {item}")
        st.markdown("**Suggested next steps**")
        for item in result.suggested_next_steps:
            st.markdown(f"- {item}")

    st.download_button(
        "Download full research JSON",
        json.dumps(result.model_dump(mode="json"), indent=2),
        file_name="research-result.json",
        mime="application/json",
    )


def main() -> None:
    inject_styles()
    with st.sidebar:
        st.markdown("## ✦ Atlas")
        st.caption("Production-oriented AI research agent")
        st.divider()
        st.markdown("**Assignment evidence**")
        for item in [
            "✓ Planner → executor workflow",
            "✓ 3 retrieval tools",
            "✓ Source filtering & citations",
            "✓ Structured typed output",
            "✓ Retries, fallback & safe failures",
            "✓ Evaluation-ready metrics",
        ]:
            st.markdown(item)
        st.divider()
        st.markdown("**Safety by design**")
        st.caption("Prompt-injection marking · SSRF guard · citation allow-list · bounded retrieval")
        st.divider()
        st.caption("Tip: use the demo result without credentials, or configure `.env` for a live run.")

    st.markdown(
        """<section class='hero'><div class='eyebrow'>Evidence-first research</div>
        <h1>Answers you can inspect.</h1>
        <p>Atlas plans a research path, gathers and filters evidence, then produces a source-grounded brief with calibrated confidence.</p></section>""",
        unsafe_allow_html=True,
    )
    cards = st.columns(3)
    for column, title, body in zip(cards, ["① Plan deliberately", "② Verify evidence", "③ Report honestly"], ["A bounded plan makes tool decisions visible.", "Sources are ranked, deduplicated, and cited.", "Failures and limits remain part of the answer."]):
        with column:
            st.markdown(f"<div class='soft-card'><h3>{title}</h3><p>{body}</p></div>", unsafe_allow_html=True)

    st.write("")
    defaults = [
        "Compare Qdrant, Weaviate, and Milvus for a small RAG startup.",
        "Research the pros and cons of multi-agent architecture for customer support automation.",
        "Compare approaches to adding memory in an AI support agent.",
    ]
    question = st.text_area("What would you like to research?", value=defaults[0], height=96, max_chars=2000)
    run_col, demo_col, _ = st.columns([1, 1, 5])
    with run_col:
        run_live = st.button("Run live research", use_container_width=True)
    with demo_col:
        show_demo = st.button("View demo result", use_container_width=True)

    if show_demo:
        st.session_state.result = load_example()
        st.session_state.notice = "Showing a labeled representative result. Run live research for current evidence."
    if run_live:
        try:
            with st.status("Researching with a bounded workflow…", expanded=True) as status:
                st.write("Creating the plan and selecting tools")
                agent = build_agent()
                st.write("Gathering, filtering, and validating sources")
                st.session_state.result = agent.run(question)
                status.update(label="Research brief ready", state="complete", expanded=False)
            st.session_state.notice = None
        except Exception as exc:  # noqa: BLE001 - UI must render a safe error for provider/tool failures.
            st.error(f"Live run could not start: {exc}")
            st.caption("Add OPENAI_API_KEY to `.env`, then restart Streamlit. You can still use the demo result.")

    if st.session_state.get("notice"):
        st.info(st.session_state.notice, icon="💡")
    if result := st.session_state.get("result"):
        render_result(result)


if __name__ == "__main__":
    main()
