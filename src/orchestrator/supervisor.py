"""
Supervisor — orchestrates the multi-agent research pipeline.

This is PURE PYTHON — no LLM calls. It routes messages between agents,
manages state, and enforces limits. Knowing when NOT to use an LLM
is itself a good engineering signal.

Supports both sequential and async concurrent execution of Researchers.
"""
import asyncio
import concurrent.futures
from typing import Callable

from src.agents.base import metrics
from src.agents.planner import PlannerAgent
from src.agents.researcher import ResearcherAgent
from src.agents.critic import CriticAgent
from src.agents.writer import WriterAgent
from src.models.schemas import ResearchFinding, CriticVerdict, ResearchReport
from src.config import MAX_CRITIC_RETRIES
from src.memory import memory, save_report


class Supervisor:
    """
    Pure-Python orchestrator. Routes work between agents, enforces
    retry limits, and manages the research pipeline.
    """

    def __init__(self, on_status: Callable[[str], None] | None = None):
        """
        Args:
            on_status: Optional callback for status updates (used by Streamlit UI).
                       Called with a status string whenever something notable happens.
        """
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.critic = CriticAgent()
        self.writer = WriterAgent()
        self._status = on_status or (lambda msg: print(msg))

    def _log(self, msg: str):
        """Print and optionally callback with status."""
        print(msg)
        self._status(msg)

    def _research_with_critic_loop(
        self,
        question: str,
        question_index: int,
        total_questions: int,
    ) -> ResearchFinding:
        """
        Research a single sub-question with the Critic feedback loop.

        Flow: Researcher → Critic → (if rejected) → Researcher again → Critic again
              Max MAX_CRITIC_RETRIES rejections before force-accepting.
        """
        feedback: str | None = None
        last_verdict: CriticVerdict | None = None

        for attempt in range(MAX_CRITIC_RETRIES + 1):
            # Researcher step
            self._log(
                f"[Supervisor] Sub-question {question_index}/{total_questions} "
                f"→ Researcher (attempt {attempt + 1})"
            )
            answer = self.researcher.research(question, critic_feedback=feedback)

            # Critic step
            self._log(f"[Supervisor] → Critic reviewing...")
            verdict = self.critic.review(question, answer)
            last_verdict = verdict

            if verdict.approved:
                self._log(
                    f"[Critic] ✅ APPROVED "
                    f"(grounding={verdict.grounding_score:.1f}, "
                    f"completeness={verdict.completeness_score:.1f}, "
                    f"recency={verdict.recency_score:.1f})"
                )
                
                # STORE IN VECTOR DATABASE (If NOT a memory cache hit)
                if not answer.startswith("[MEMORY CACHE_HIT]"):
                    memory.store_memory(question, answer, topic="memory_check")

                return ResearchFinding(
                    question=question,
                    answer=answer,
                    sources=[],  # extracted from answer text
                    critic_attempts=attempt + 1,
                    critic_scores=verdict,
                )
            else:
                feedback = verdict.feedback
                self._log(
                    f"[Critic] ❌ REJECTED: {feedback}"
                )
                if attempt == MAX_CRITIC_RETRIES:
                    self._log(
                        f"[Supervisor] ⚠️ Max retries ({MAX_CRITIC_RETRIES}) reached. "
                        f"Force-accepting best-effort answer."
                    )

        # Force-accept after exhausting retries
        return ResearchFinding(
            question=question,
            answer=answer,
            sources=[],
            critic_attempts=MAX_CRITIC_RETRIES + 1,
            critic_scores=last_verdict,
        )

    def run(self, topic: str) -> ResearchReport:
        """
        Run the full multi-agent pipeline SEQUENTIALLY.
        Use run_async() for concurrent researchers.
        """
        metrics.start()
        self._log(f"\n{'═' * 50}")
        self._log(f"[Supervisor] Starting research: {topic}")
        self._log(f"{'═' * 50}\n")

        # Step 1: Plan
        self._log("[Supervisor] → Planner Agent")
        subquestions = self.planner.plan(topic)
        for i, q in enumerate(subquestions, 1):
            self._log(f"  {i}. {q}")

        # Step 2: Research + Critic loop (sequential)
        findings: list[ResearchFinding] = []
        approved_findings: dict[str, str] = {}

        for i, q in enumerate(subquestions, 1):
            self._log(f"\n{'─' * 40}")
            finding = self._research_with_critic_loop(q, i, len(subquestions))
            findings.append(finding)
            approved_findings[q] = finding.answer

        # Step 3: Write
        self._log(f"\n{'─' * 40}")
        self._log(f"[Supervisor] → Writer Agent (synthesizing {len(findings)} findings)")
        report = self.writer.synthesize(topic, approved_findings)

        self._log(f"\n{'═' * 50}")
        self._log(f"[Supervisor] ✅ Research complete!")
        self._log(metrics.summary())

        final_report = ResearchReport(
            topic=topic,
            report=report,
            findings=findings,
            metrics=metrics.to_dict(),
        )
        
        # PERSIST SESSION
        save_report(topic, report, final_report.model_dump())

        return final_report

    def plan_research(self, topic: str, base64_image: str | None = None) -> list[str]:
        metrics.start()
        self._log(f"\n{'═' * 50}")
        self._log(f"[Supervisor] Starting research planning: {topic or 'Analyzing image...'}")
        self._log(f"{'═' * 50}\n")
        self._log("[Supervisor] → Planner Agent")
        subquestions = self.planner.plan(topic, base64_image)
        for i, q in enumerate(subquestions, 1):
            self._log(f"  {i}. {q}")
        return subquestions

    def execute_research_async(self, topic: str, subquestions: list[str]) -> ResearchReport:
        # Step 2: Research + Critic loop (concurrent)
        self._log(f"\n[Supervisor] Dispatching {len(subquestions)} researchers concurrently...")

        findings: list[ResearchFinding] = []
        approved_findings: dict[str, str] = {}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(subquestions)
        ) as executor:
            future_to_question = {
                executor.submit(
                    self._research_with_critic_loop, q, i, len(subquestions)
                ): q
                for i, q in enumerate(subquestions, 1)
            }

            for future in concurrent.futures.as_completed(future_to_question):
                q = future_to_question[future]
                try:
                    finding = future.result()
                    findings.append(finding)
                    approved_findings[q] = finding.answer
                except Exception as e:
                    self._log(f"[Supervisor] ❌ Research failed for: {q[:50]}... — {e}")
                    approved_findings[q] = f"Research failed: {e}"
                    findings.append(ResearchFinding(
                        question=q,
                        answer=f"Research failed: {e}",
                        critic_attempts=0,
                    ))

        # Step 3: Write
        self._log(f"\n{'─' * 40}")
        self._log(f"[Supervisor] → Writer Agent (synthesizing {len(findings)} findings)")
        report = self.writer.synthesize(topic, approved_findings)

        self._log(f"\n{'═' * 50}")
        self._log(f"[Supervisor] ✅ ASYNC research complete!")
        self._log(metrics.summary())

        final_report = ResearchReport(
            topic=topic,
            report=report,
            findings=findings,
            metrics=metrics.to_dict(),
        )
        
        # PERSIST SESSION
        save_report(topic, report, final_report.model_dump())

        return final_report

    def run_async(self, topic: str) -> ResearchReport:
        """
        Run the pipeline with CONCURRENT researchers entirely.
        This provides backward compatibility with scripts not using HITL.
        """
        subquestions = self.plan_research(topic)
        return self.execute_research_async(topic, subquestions)


# ── CLI Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    topic = input("Enter a research topic: ")
    use_async = input("Use async/concurrent mode? (y/n): ").strip().lower() == "y"

    supervisor = Supervisor()
    if use_async:
        result = supervisor.run_async(topic)
    else:
        result = supervisor.run(topic)

    print("\n" + result.report)
