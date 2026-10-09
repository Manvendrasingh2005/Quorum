"""
LLM-as-judge for evaluating agent outputs.

Uses the Gemini model to grade research reports on a 1-10 scale
across 4 metrics: factual accuracy, citation quality, recency, and completeness.
"""
from src.agents.base import BaseAgent
from src.models.schemas import EvaluationScore


class LLMJudge(BaseAgent):
    role = "judge"
    system_prompt = (
        "You are an impartial expert judge evaluating an AI-generated research report. "
        "You will score the report on four metrics using a scale of 1 to 10.\n\n"
        "1. factual_accuracy: Are the claims factually correct and hallucination-free?\n"
        "2. citation_quality: Are sources URLs present, relevant, and properly used?\n"
        "3. recency: Does the information reflect the most recent developments?\n"
        "4. completeness: Does the report cover the requested topic comprehensively?\n\n"
        "Only outputs valid JSON matching the required EvaluationScore schema."
    )
    uses_tools = False

    def evaluate(self, topic: str, report: str) -> EvaluationScore:
        """Score a report based on the topic."""
        prompt = (
            f"Topic: \"{topic}\"\n\n"
            f"Report to evaluate:\n"
            f"{'='*40}\n"
            f"{report}\n"
            f"{'='*40}\n\n"
            "Evaluate the report strictly using the criteria defined in your instructions. "
            "Output ONLY the required JSON."
        )

        try:
            return self._validated_ask(prompt, EvaluationScore)
        except ValueError as e:
            print(f"  [Judge] ⚠️ Validation failed: {e}")
            # Fallback if the judge fails to provide valid JSON
            return EvaluationScore(
                factual_accuracy=1,
                citation_quality=1,
                recency=1,
                completeness=1,
                reasoning="Judge failed to return valid JSON."
            )
