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
from pathlib import Path
from src.orchestrator.supervisor import Supervisor
from src.agents.base import metrics
from src.memory import get_recent_reports

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🤖",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    .agent-card {
        padding: 12px 16px;
        border-radius: 10px;
        margin: 6px 0;
        font-size: 14px;
        line-height: 1.5;
    }

    .agent-planner {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-left: 4px solid #00d2ff;
        color: #e0e0e0;
    }

    .agent-researcher {
        background: linear-gradient(135deg, #1a2e1a 0%, #163e22 100%);
        border-left: 4px solid #00ff88;
        color: #e0e0e0;
    }

    .agent-critic-approve {
        background: linear-gradient(135deg, #1a2e2e 0%, #163e3e 100%);
        border-left: 4px solid #00ffcc;
        color: #e0e0e0;
    }

    .agent-critic-reject {
        background: linear-gradient(135deg, #2e1a1a 0%, #3e1616 100%);
        border-left: 4px solid #ff4444;
        color: #e0e0e0;
    }

    .agent-writer {
        background: linear-gradient(135deg, #2e2e1a 0%, #3e3616 100%);
        border-left: 4px solid #ffcc00;
        color: #e0e0e0;
    }

    .agent-supervisor {
        background: linear-gradient(135deg, #2e1a2e 0%, #3e163e 100%);
        border-left: 4px solid #cc00ff;
        color: #e0e0e0;
    }

    .metric-card {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #00d2ff;
    }

    .metric-label {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .score-bar {
        height: 8px;
        border-radius: 4px;
        background: #333;
        overflow: hidden;
        margin: 4px 0;
    }

    .score-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🤖 Multi-Agent Research System")
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


    # ── Execution ─────────────────────────────────────────────────────────────────
    if run_button:
        # Status container for real-time agent activity
        agent_log = st.container()
        status_logs: list[str] = []

        def on_status(msg: str):
            """Callback for real-time agent status updates."""
            status_logs.append(msg)

        status = st.status("🤖 Initializing multi-agent pipeline...", expanded=True)

        with status:
            supervisor = Supervisor(on_status=on_status)

            # Run the pipeline
            if use_async:
                status.update(label="⚡ Running concurrent multi-agent pipeline...")
                result = supervisor.run_async(topic)
            else:
                status.update(label="🔄 Running sequential multi-agent pipeline...")
                result = supervisor.run(topic)

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