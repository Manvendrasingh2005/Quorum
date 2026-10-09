"""
Writer Agent — synthesizes Critic-approved findings into a final report.

This agent only receives APPROVED research — work that has passed
the Critic's quality review. It merges overlapping points and
preserves citations.
"""
from src.agents.base import BaseAgent, metrics


class WriterAgent(BaseAgent):
    role = "writer"
    system_prompt = (
        "You are a Writer Agent in a multi-agent research system. "
        "You receive Critic-approved research findings and synthesize them "
        "into a single, well-organized research report.\n\n"
        "Rules:\n"
        "- Use clear headings and subheadings (## and ###)\n"
        "- Do NOT repeat overlapping points — merge them intelligently\n"
        "- Preserve ALL source URLs as inline citations\n"
        "- Start with a brief executive summary\n"
        "- End with key takeaways or conclusions\n"
        "- Use professional, clear language\n"
        "- Include specific facts, numbers, and dates from the findings"
    )
    uses_tools = False

    def synthesize(self, topic: str, findings: dict[str, str]) -> str:
        """Write the final report from approved findings."""
        findings_text = "\n\n---\n\n".join(
            f"**Sub-question:** {q}\n\n**Approved findings:**\n{a}"
            for q, a in findings.items()
        )

        prompt = (
            f"Write a comprehensive, well-organized research report on:\n"
            f"\"{topic}\"\n\n"
            f"Based on these Critic-approved research findings:\n\n"
            f"{findings_text}\n\n"
            "Structure it with an executive summary, organized sections with "
            "headings, and a conclusion. Merge overlapping points. "
            "Preserve all source URL citations."
        )

        metrics.log_message("supervisor", "writer", "task",
                            f"Synthesize report from {len(findings)} findings")

        response = self._ask(prompt)
        report = response.text

        metrics.log_message("writer", "supervisor", "result",
                            f"Report complete ({len(report)} chars)")

        return report
