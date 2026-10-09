"""
Multi-Agent Research System — Streamlit UI.

Shows real-time agent activity: which agent is working, Critic approvals/rejections,
structured metrics, and the final synthesized report.
Also includes an Evaluation Dashboard to compare Baseline vs Multi-Agent.

Run: streamlit run app.py
"""
import streamlit as st
import json
import pandas as pd
import time
from pathlib import Path
from src.orchestrator.supervisor import Supervisor
from src.agents.base import metrics
from src.memory import get_recent_reports

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quorum",
    page_icon="🤖",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Global Body and Font */
    html, body, [class*="css"]  {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Hide Streamlit Junk */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Background and Glassmorphism */
    .stApp {
        background: radial-gradient(circle at 15% 50%, #0d1117, #010409);
        color: #c9d1d9;
    }
    
    /* Push content up to remove empty space */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Style Text Input (Search Bar) */
    .stTextInput > div > div > input {
        border-radius: 20px;
        border: 1px solid #30363d;
        background-color: rgba(22, 27, 34, 0.7);
        color: #f0f6fc;
        padding: 12px 20px;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .stTextInput > div > div > input:focus {
        border-color: #58a6ff;
        box-shadow: 0 0 15px rgba(88, 166, 255, 0.3);
    }
    
    /* Style Primary Button */
    .stButton > button {
        background: linear-gradient(135deg, #6e40c9 0%, #1f6feb 100%);
        color: white;
        border: none;
        border-radius: 20px;
        font-size: 16px;
        font-weight: 600;
        padding: 2px 24px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(31, 111, 235, 0.4);
        color: white;
        border: none;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(13, 17, 23, 0.8) !important;
        backdrop-filter: blur(10px) !important;
        border-right: 1px solid #30363d;
    }

    /* Agent log entry animations */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .agent-card {
        padding: 14px 18px;
        border-radius: 12px;
        margin: 8px 0;
        font-size: 15px;
        line-height: 1.6;
        animation: fadeInUp 0.4s ease forwards;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        backdrop-filter: blur(5px);
    }

    /* specific agent card styles... */
    .agent-planner { background: rgba(0, 210, 255, 0.1); border-left: 4px solid #00d2ff; color: #c9d1d9; }
    .agent-researcher { background: rgba(0, 255, 136, 0.1); border-left: 4px solid #00ff88; color: #c9d1d9; }
    .agent-critic-approve { background: rgba(0, 255, 204, 0.1); border-left: 4px solid #00ffcc; color: #c9d1d9; }
    .agent-critic-reject { background: rgba(255, 68, 68, 0.1); border-left: 4px solid #ff4444; color: #ffcccc; }
    .agent-writer { background: rgba(255, 204, 0, 0.1); border-left: 4px solid #ffcc00; color: #c9d1d9; }
    .agent-supervisor { background: rgba(204, 0, 255, 0.1); border-left: 4px solid #cc00ff; color: #c9d1d9; }

    /* Metric Cards */
    .metric-card {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        backdrop-filter: blur(5px);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        border-color: #58a6ff;
    }

    .metric-value {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #58a6ff 0%, #3fb950 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }

    .metric-label {
        font-size: 11px;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    /* Critic Score Bars */
    .score-bar {
        height: 6px;
        border-radius: 3px;
        background: #21262d;
        overflow: hidden;
        margin: 6px 0;
    }
    .score-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
    }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🤖 Quorum")
st.markdown(
    "*Four AI agents — **Planner**, **Researcher**, **Critic**, **Writer** — "
    "collaborate to produce quality-reviewed research reports.*"
)

tab_run, tab_eval = st.tabs(["🚀 Run Pipeline", "📊 Evaluation Dashboard"])

# ── Sidebar: Past Research ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 Past Research")
    st.markdown("Loaded from SQLite memory.")
    past_reports = get_recent_reports(limit=5)
    
    if not past_reports:
        st.info("No past research found.")
    else:
        for r in past_reports:
            with st.expander(f"{r['topic'][:40]}..."):
                st.caption(f"Date: {r['created_at'][:10]}")
                # We can load the json back into a pydantic object but here we just render the text
                st.markdown(f"**Metrics:** {r['data'].get('metrics', {}).get('total_time', 0)}s run")
                st.markdown(r['report_text'][:300] + "...")

with tab_run:
    # ── Architecture Diagram (collapsed) ─────────────────────────────────────────
    with st.expander("📐 System Architecture", expanded=False):
        st.markdown("""
        ```
        ┌─────────────────────────────────────────────────┐
        │                  SUPERVISOR                      │
        │              (Pure Python — no LLM)              │
        ├─────────────────────────────────────────────────┤
        │                                                  │
        │   User Query                                     │
        │       │                                          │
        │       ▼                                          │
        │   🧠 PLANNER AGENT                               │
        │       │  Decomposes into sub-questions            │
        │       ▼                                          │
        │   🔍 RESEARCHER AGENTS (concurrent)              │
        │       │  Web search + draft answers               │
        │       ▼                                          │
        │   ⚖️  CRITIC AGENT                                │
        │       │  Review + score + approve/reject           │
        │       │                                          │
        │       ├── ✅ Approved → Writer                    │
        │       └── ❌ Rejected → Back to Researcher        │
        │                        (with specific feedback)   │
        │       ▼                                          │
        │   ✍️  WRITER AGENT                                │
        │       │  Synthesize final report                  │
        │       ▼                                          │
        │   📊 Final Report + Metrics                      │
        └─────────────────────────────────────────────────┘
        ```
        """)

    st.markdown("---")

    # ── Input ─────────────────────────────────────────────────────────────────────
    col_input, col_mode = st.columns([4, 1])
    with col_input:
        topic = st.text_input(
            "Research Topic",
            placeholder="e.g. Compare RAG vs fine-tuning for customer support chatbots",
        )
    with col_mode:
        use_async = st.toggle("⚡ Concurrent", value=True,
                               help="Run researchers concurrently (faster)")

    run_button = st.button("🚀 Start Research", type="primary", disabled=not topic, use_container_width=True)


    # ── State Machine ─────────────────────────────────────────────────────────────
    if "workflow_stage" not in st.session_state:
        st.session_state.workflow_stage = "idle"
        st.session_state.plan = []
        st.session_state.result = None

    if run_button:
        st.session_state.workflow_stage = "planning"
        st.session_state.topic = topic
        if "report_streamed" in st.session_state:
            del st.session_state["report_streamed"]

    # ── Execution ─────────────────────────────────────────────────────────────────
    if st.session_state.workflow_stage == "planning":
        status = st.status("🧠 Planner Agent is breaking down the topic...", expanded=True)
        supervisor = Supervisor(on_status=lambda msg: status.write(msg))
        st.session_state.plan = supervisor.plan_research(st.session_state.topic)
        st.session_state.workflow_stage = "review_plan"
        status.update(label="✅ Planning complete! Waiting for your review.", state="complete", expanded=False)
        st.rerun()

    if st.session_state.workflow_stage == "review_plan":
        st.markdown("### 📝 Human-in-the-Loop: Review Research Plan")
        st.info("The Planner has decomposed your topic. You can edit, delete, or rewrite these sub-questions before the Researchers begin.")
        
        edited_plan = []
        for i, q in enumerate(st.session_state.plan):
            val = st.text_input(f"Sub-question {i+1}", value=q, key=f"q_{i}")
            if val.strip():
                edited_plan.append(val.strip())
                
        new_q = st.text_input("Add a new sub-question (optional)", placeholder="Type a custom question here...", key="q_new")
        if new_q.strip():
            edited_plan.append(new_q.strip())
            
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🚀 Approve & Start Research", type="primary", use_container_width=True):
                st.session_state.plan = edited_plan
                st.session_state.workflow_stage = "researching"
                st.rerun()

    if st.session_state.workflow_stage == "researching":
        agent_log = st.container()
        status_logs: list[str] = []

        def on_status(msg: str):
            status_logs.append(msg)

        status = st.status("🔍 Researchers are gathering data...", expanded=True)

        with status:
            supervisor = Supervisor(on_status=on_status)
            
            if use_async:
                result = supervisor.execute_research_async(st.session_state.topic, st.session_state.plan)
            else:
                # We can handle sequential here if we want, but let's stick to async for the new UI since it's the premium feature.
                # Actually, backward support:
                result = supervisor.execute_research_async(st.session_state.topic, st.session_state.plan)

            # Show agent activity log
            st.markdown("### 📋 Agent Activity Log")
            for msg in metrics.agent_messages:
                time_str = f"{msg['time']:.1f}s"
                sender = msg['sender']
                summary = msg['summary']

                if sender == "planner":
                    css_class = "agent-planner"
                    icon = "🧠"
                elif sender == "researcher":
                    css_class = "agent-researcher"
                    icon = "🔍"
                elif sender == "critic" and msg['type'] == "approval":
                    css_class = "agent-critic-approve"
                    icon = "✅"
                elif sender == "critic" and msg['type'] == "rejection":
                    css_class = "agent-critic-reject"
                    icon = "❌"
                elif sender == "writer":
                    css_class = "agent-writer"
                    icon = "✍️"
                else:
                    css_class = "agent-supervisor"
                    icon = "📡"

                st.markdown(
                    f'<div class="agent-card {css_class}">'
                    f'<b>[{time_str}]</b> {icon} <b>{sender.upper()}</b>: {summary}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        status.update(label="✅ Research complete!", state="complete", expanded=False)
        st.session_state.result = result
        st.session_state.workflow_stage = "complete"
        st.rerun()

    if st.session_state.workflow_stage == "complete":
        result = st.session_state.result

        # ── Metrics Dashboard ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Run Metrics")

        m = result.metrics
        cols = st.columns(7)
        metric_items = [
            ("⏱️ Time", f"{m.get('total_time', 0)}s"),
            ("🤖 Model Calls", m.get("model_calls", 0)),
            ("🔍 Searches", m.get("search_calls", 0)),
            ("✨ Memory", m.get("memory_hits", 0)),
            ("✅ Approvals", m.get("critic_approvals", 0)),
            ("❌ Rejections", m.get("critic_rejections", 0)),
            ("🔄 Retries", m.get("schema_retries", 0)),
        ]
        for col, (label, value) in zip(cols, metric_items):
            with col:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value">{value}</div>'
                    f'<div class="metric-label">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── Critic Scores per Finding ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### ⚖️ Critic Scores by Sub-question")

        for finding in result.findings:
            if finding.critic_scores:
                v = finding.critic_scores
                with st.expander(
                    f"{'✅' if v.approved else '❌'} {finding.question[:80]}... "
                    f"(attempts: {finding.critic_attempts})",
                    expanded=False,
                ):
                    score_cols = st.columns(3)
                    for col, (name, score) in zip(
                        score_cols,
                        [
                            ("Grounding", v.grounding_score),
                            ("Completeness", v.completeness_score),
                            ("Recency", v.recency_score),
                        ],
                    ):
                        with col:
                            color = "#00ff88" if score >= 0.7 else "#ffcc00" if score >= 0.5 else "#ff4444"
                            st.markdown(f"**{name}**: {score:.0%}")
                            st.markdown(
                                f'<div class="score-bar">'
                                f'<div class="score-fill" style="width:{score*100}%;background:{color};"></div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    st.markdown(f"**Feedback:** {v.feedback}")
                    if v.unsupported_claims:
                        st.warning(f"⚠️ Unsupported claims: {', '.join(v.unsupported_claims)}")

        # ── Model Usage ───────────────────────────────────────────────────────────
        with st.expander("🤖 Model Usage by Agent Role"):
            model_usage = m.get("model_usage_by_role", {})
            if model_usage:
                for role, models in model_usage.items():
                    st.markdown(f"**{role.upper()}**: {models}")

        # ── Final Report ──────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📝 Research Report")
        
        if "report_streamed" not in st.session_state:
            def stream_data():
                for word in result.report.split(" "):
                    yield word + " "
                    time.sleep(0.02)
            st.write_stream(stream_data)
            st.session_state.report_streamed = True
        else:
            st.markdown(result.report)

with tab_eval:
    st.markdown("### 📊 Evaluation Results: Baseline vs Multi-Agent")
    st.markdown("Comparing a single standard Gemini prompt against the full multi-agent pipeline.")
    
    eval_file = Path("evaluation_results.json")
    if eval_file.exists():
        with open(eval_file, "r") as f:
            eval_data = json.load(f)
            
        if not eval_data:
            st.info("No evaluation data found yet. Run the evaluator script to populate!")
        else:
            # Reformat data for pandas
            rows = []
            for item in eval_data:
                topic = item["topic"]
                base_scores = item["baseline"]["scores"]
                ma_scores = item["multiagent"]["scores"]
                
                rows.append({"Topic": topic, "System": "Baseline", "Factual Accuracy": base_scores["factual_accuracy"], "Citation Quality": base_scores["citation_quality"], "Completeness": base_scores["completeness"], "Recency": base_scores["recency"]})
                rows.append({"Topic": topic, "System": "Multi-Agent", "Factual Accuracy": ma_scores["factual_accuracy"], "Citation Quality": ma_scores["citation_quality"], "Completeness": ma_scores["completeness"], "Recency": ma_scores["recency"]})
                
            df = pd.DataFrame(rows)
            
            # Averages
            avg_df = df.groupby("System").mean().reset_index()
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("#### Average Scores (1-10)")
                st.dataframe(avg_df, hide_index=True)
                
            with col2:
                st.markdown("#### Chart Comparison")
                st.bar_chart(avg_df.set_index("System").T, height=300)
                
            st.markdown("#### Individual Queries")
            for item in eval_data:
                with st.expander(item["topic"]):
                    b_scores = item["baseline"]["scores"]
                    ma_scores = item["multiagent"]["scores"]
                    
                    st.markdown("**Baseline Scores:**")
                    st.json(b_scores)
                    st.markdown("**Multi-Agent Scores:**")
                    st.json(ma_scores)
                    
    else:
        st.info("No evaluation data found. Run `python -m src.evaluation.evaluator` to generate results.")