"""
Planner Agent — decomposes a research topic into focused sub-questions.

This agent is CONSTRAINED: it cannot answer questions, only decompose them.
Uses Pydantic validation to ensure output is a valid list of sub-questions.
"""
from src.agents.base import BaseAgent, metrics
from src.models.schemas import SubQuestionPlan
from src.config import MAX_SUBQUESTIONS


class PlannerAgent(BaseAgent):
    role = "planner"
    system_prompt = (
        "You are a Planning Agent in a multi-agent research system. "
        "Your ONLY job is to break a broad research topic into focused, "
        "non-overlapping sub-questions. You do NOT answer questions yourself. "
        "You do NOT search the web. You ONLY decompose topics.\n\n"
        "Rules:\n"
        "- Each sub-question should target a distinct aspect of the topic\n"
        "- Sub-questions should not overlap or repeat\n"
        "- Together they should give a complete picture of the topic\n"
        f"- Output exactly {MAX_SUBQUESTIONS} sub-questions"
    )
    uses_tools = False

    def plan(self, topic: str, base64_image: str | None = None) -> list[str]:
        """Break a topic into sub-questions. Returns validated list."""
        
        img_instruction = ""
        if base64_image:
            img_instruction = "IMPORTANT: An image has been provided. Extract handwritten or computerized text from it, and incorporate it into the topic. "
            if not topic:
                topic = "Determine the research topic purely from the contents of the attached image."
        
        prompt = (
            f"Break this research topic into exactly {MAX_SUBQUESTIONS} focused "
            f"sub-questions that together give a complete picture.\n\n"
            f"{img_instruction}"
            f"Topic: \"{topic}\"\n\n"
            "Respond with ONLY a JSON object in this exact format:\n"
            '{"sub_questions": ["question 1", "question 2", "question 3", "question 4"]}\n\n'
            "No other text, no markdown, just the JSON object."
        )

        try:
            result = self._validated_ask(prompt, SubQuestionPlan, image_data=base64_image)
            questions = result.sub_questions[:MAX_SUBQUESTIONS]
        except ValueError:
            # If validation completely fails, fall back to using topic directly
            print(f"  [Planner] [!] Validation failed, using topic as single question.")
            questions = [topic]

        metrics.subquestions = len(questions)
        metrics.log_message("planner", "supervisor", "result",
                            f"Decomposed into {len(questions)} sub-questions")

        return questions
