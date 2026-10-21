"""
Planner Agent — decomposes a research topic into focused sub-questions.

This agent is CONSTRAINED: it cannot answer questions, only decompose them.
Uses Pydantic validation to ensure output is a valid list of sub-questions.
"""
from src.agents.base import BaseAgent, RunMetrics, metrics
from src.models.schemas import SubQuestionPlan
from src.config import MAX_SUBQUESTIONS, DEPTH_PRESETS


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
        "- Output exactly the requested number of sub-questions"
    )
    uses_tools = False

    def __init__(self, metrics_instance: RunMetrics | None = None):
        super().__init__(metrics_instance=metrics_instance)

    def plan(self, topic: str, base64_image: str | None = None, depth: str = "standard") -> list[str]:
        """Break a topic into sub-questions based on selected research depth."""
        preset = DEPTH_PRESETS.get(depth, DEPTH_PRESETS["standard"])
        target_count = preset.get("subquestions", MAX_SUBQUESTIONS)

        img_instruction = ""
        if base64_image:
            img_instruction = "IMPORTANT: An image has been provided. Extract handwritten or computerized text from it, and incorporate it into the topic. "
            if not topic:
                topic = "Determine the research topic purely from the contents of the attached image."

        prompt = (
            f"Break this research topic into exactly {target_count} focused "
            f"sub-questions ({preset.get('label', 'Standard')}) that together give a complete picture.\n\n"
            f"{img_instruction}"
            f"Topic: \"{topic}\"\n\n"
            "Respond with ONLY a JSON object in this exact format:\n"
            '{"sub_questions": ["question 1", "question 2", ...]}\n\n'
            "No other text, no markdown, just the JSON object."
        )

        try:
            result = self._validated_ask(prompt, SubQuestionPlan, image_data=base64_image)
            questions = result.sub_questions[:target_count]
        except Exception as e:
            # Fallback decomposition to ensure deep research NEVER stalls on network blips
            print(f"  [Planner] [!] Decomposition failed ({e}), generating deterministic subquestions.")
            clean_topic = topic.strip() if topic else "Current research topic"
            if target_count == 1:
                questions = [f"Core breakthroughs, current operational status, and latest benchmarks for {clean_topic}"]
            elif target_count <= 3:
                questions = [
                    f"Current technological architecture and latest milestone breakthroughs in {clean_topic}",
                    f"Leading commercial developers, pilot projects, and market deployment timelines for {clean_topic}",
                    f"Key economic, regulatory, and engineering bottlenecks facing {clean_topic}",
                ][:target_count]
            else:
                questions = [
                    f"Current technological architecture and scientific breakthroughs in {clean_topic}",
                    f"Leading private companies, pilot plants, and deployment status for {clean_topic}",
                    f"Regulatory framework, safety licensing, and government policy governing {clean_topic}",
                    f"Primary supply chain, materials, and economic cost bottlenecks for {clean_topic}",
                    f"Projected commercial viability, grid integration, and competitive outlook for {clean_topic}",
                ][:target_count]

        self.metrics.set_subquestions(len(questions))
        self.metrics.log_message("planner", "supervisor", "result",
                            f"Decomposed into {len(questions)} sub-questions ({depth} mode)")

        return questions

