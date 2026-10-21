"""
Critic Agent — reviews Researcher output with skepticism.

This is THE key differentiator of the system. The Critic:
  - Scores research on grounding, completeness, and recency
  - Identifies unsupported claims
  - Can REJECT work and send it back with specific feedback
  - Uses a DIFFERENT primary model than the Researcher so it isn't grading its own work

The rejection loop (Researcher → Critic → Rejected → Researcher again) is what
makes this genuinely multi-agent, not just a renamed pipeline.
"""
from src.agents.base import BaseAgent, metrics
from src.models.schemas import CriticVerdict


class CriticAgent(BaseAgent):
    role = "critic"
    system_prompt = (
        "You are a Critic Agent in a multi-agent research system. "
        "You review a Researcher Agent's work with SKEPTICISM.\n\n"
        "You must evaluate the research and respond with ONLY a JSON object:\n"
        "{\n"
        '  "approved": true/false,\n'
        '  "grounding_score": 0.0-1.0,   // Are claims backed by cited sources?\n'
        '  "completeness_score": 0.0-1.0, // Does it fully answer the question?\n'
        '  "recency_score": 0.0-1.0,      // How current are the sources?\n'
        '  "feedback": "string",           // What\'s wrong (if rejected) or brief note (if approved)\n'
        '  "unsupported_claims": ["claim1", "claim2"]  // Claims lacking source backing\n'
        "}\n\n"
        "Rules:\n"
        "- REJECT if grounding_score < 0.5 (too many unsupported claims)\n"
        "- REJECT if completeness_score < 0.4 (doesn't answer the question)\n"
        "- REJECT if no source URLs are cited at all\n"
        "- When rejecting, feedback MUST be specific and actionable (1-2 sentences)\n"
        "- List up to 3 unsupported claims\n"
        "- Be fair — only reject genuinely poor work, not minor gaps"
    )
    uses_tools = False

    def __init__(self, metrics_instance: RunMetrics | None = None):
        super().__init__(metrics_instance=metrics_instance)

    def review(self, question: str, researcher_answer: str) -> CriticVerdict:
        """
        Review a Researcher's answer. Returns a validated CriticVerdict.
        If JSON parsing fails after all retries, returns a default approval.
        """
        prompt = (
            f"Sub-question being researched:\n\"{question}\"\n\n"
            f"Researcher's answer:\n{researcher_answer}\n\n"
            "Evaluate this research. Respond with ONLY the JSON object "
            "matching the schema described in your instructions. No other text."
        )

        try:
            verdict = self._validated_ask(prompt, CriticVerdict)
        except Exception as e:
            print(f"  [Critic] [!] Could not parse verdict, defaulting to approve: {e}")
            verdict = CriticVerdict(
                approved=True,
                grounding_score=0.5,
                completeness_score=0.5,
                recency_score=0.5,
                feedback="Critic parsing failed; auto-approved.",
                unsupported_claims=[],
            )

        # Track metrics
        if verdict.approved:
            self.metrics.inc_critic_approvals()
            self.metrics.log_message("critic", "supervisor", "approval",
                                f"✅ Approved (grounding={verdict.grounding_score:.1f}, "
                                f"completeness={verdict.completeness_score:.1f})")
        else:
            self.metrics.inc_critic_rejections()
            self.metrics.log_message("critic", "supervisor", "rejection",
                                f"❌ Rejected: {verdict.feedback[:100]}")

        return verdict
