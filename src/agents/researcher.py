"""
Researcher Agent — searches the web and drafts answers to sub-questions.

This agent HAS tool access (search_web) and runs a multi-step tool-calling loop.
If it receives Critic feedback, it revises its research to address it.
"""
from src.agents.base import BaseAgent, metrics


class ResearcherAgent(BaseAgent):
    role = "researcher"
    system_prompt = (
        "You are a Researcher Agent in a multi-agent research system. "
        "Your job is to use the search_web tool to find current, factual "
        "information and produce a thorough answer to the given sub-question.\n\n"
        "Rules:\n"
        "- ALWAYS search the web before answering — never answer from memory alone\n"
        "- ALWAYS cite source URLs inline (e.g., [Source Title](URL))\n"
        "- Include specific facts, numbers, and dates when available\n"
        "- If you are revising after Critic feedback, address that feedback directly\n"
        "- Be thorough but focused on answering the specific question asked"
    )
    uses_tools = True

    def research(
        self,
        question: str,
        critic_feedback: str | None = None,
    ) -> str:
        """Research a sub-question. Optionally incorporates Critic feedback."""
        if critic_feedback:
            prompt = (
                f"{question}\n\n"
                f"⚠️ Your previous answer was REJECTED by the Critic Agent:\n"
                f"\"{critic_feedback}\"\n\n"
                "You MUST address this feedback in your revised research. "
                "Search again if needed to find better sources."
            )
            metrics.log_message("supervisor", "researcher", "feedback",
                                f"Revision requested: {critic_feedback[:100]}...")
            answer = self._ask_with_tools(prompt)
        else:
            # Only check memory on initial attempts, not when revising based on critic feedback
            from src.memory import memory
            
            cached_answer = memory.check_memory(question)
            if cached_answer:
                metrics.memory_hits += 1
                metrics.log_message("researcher", "supervisor", "result",
                                    "✨ Memory Hit! Retrieved past verified research.")
                return f"[MEMORY CACHE_HIT]\n{cached_answer}"

            prompt = question
            metrics.log_message("supervisor", "researcher", "task", question[:100])
            answer = self._ask_with_tools(prompt)

        metrics.log_message("researcher", "supervisor", "result",
                            f"Completed research ({len(answer)} chars)")

        return answer
