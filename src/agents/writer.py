"""
Writer Agent — synthesizes Critic-approved findings into a final report.

This agent only receives APPROVED research — work that has passed
the Critic's quality review. It merges overlapping points and
preserves citations.
"""
from typing import Callable
from src.agents.base import BaseAgent, RunMetrics, metrics


class WriterAgent(BaseAgent):
    role = "writer"
    system_prompt = (
        "You are a Writer Agent in a multi-agent research system. "
        "You receive Critic-approved research findings and synthesize them "
        "into a CONCISE, well-organized research report.\n\n"
        "Rules:\n"
        "- Keep the report CONCISE — aim for 600-800 words, NOT a lengthy essay\n"
        "- Use clear headings (## and ###)\n"
        "- Do NOT repeat overlapping points — merge them\n"
        "- Preserve source URLs as inline citations\n"
        "- Start with a 2-3 sentence executive summary\n"
        "- End with 3-5 bullet-point key takeaways\n"
        "- Include specific facts, numbers, and dates\n"
        "- Be direct and information-dense — no filler or verbose transitions"
    )
    uses_tools = False
    max_output_tokens = 1500  # Cap generation to prevent 3000+ word essays

    def __init__(self, metrics_instance: RunMetrics | None = None):
        super().__init__(metrics_instance=metrics_instance)

    def _build_prompt(self, topic: str, findings: dict[str, str]) -> str:
        MAX_FINDING_CHARS = 1500
        findings_text = "\n\n---\n\n".join(
            f"**Sub-question:** {q}\n\n**Key findings:**\n{a[:MAX_FINDING_CHARS]}"
            for q, a in findings.items()
        )

        return (
            f"Write a CONCISE research report (600-800 words) on:\n"
            f"\"{topic}\"\n\n"
            f"Based on these Critic-approved research findings:\n\n"
            f"{findings_text}\n\n"
            "Structure: brief executive summary, organized sections with "
            "headings, and bullet-point conclusions. Merge overlapping points. "
            "Preserve source URL citations. Be direct and dense."
        )

    def synthesize(self, topic: str, findings: dict[str, str]) -> str:
        """Write the final report from approved findings synchronously."""
        prompt = self._build_prompt(topic, findings)

        self.metrics.log_message("supervisor", "writer", "task",
                            f"Synthesize report from {len(findings)} findings")

        response = self._ask(prompt)
        report = response.text

        self.metrics.log_message("writer", "supervisor", "result",
                            f"Report complete ({len(report)} chars)")

        return report

    def synthesize_stream(
        self,
        topic: str,
        findings: dict[str, str],
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """Stream the final report token-by-token with real-time chunk callbacks."""
        prompt = self._build_prompt(topic, findings)

        self.metrics.log_message("supervisor", "writer", "task",
                            f"Live streaming report from {len(findings)} findings")

        accumulated = []
        try:
            stream = self._ask_stream(prompt)
            for chunk in stream:
                text_part = chunk.text or ""
                if text_part:
                    accumulated.append(text_part)
                    if on_chunk:
                        on_chunk(text_part)
            report = "".join(accumulated)
        except Exception as e:
            print(f"  [Writer] [!] Stream failed, falling back to sync call: {e}")
            report = self.synthesize(topic, findings)

        self.metrics.log_message("writer", "supervisor", "result",
                            f"Report complete ({len(report)} chars)")

        return report

