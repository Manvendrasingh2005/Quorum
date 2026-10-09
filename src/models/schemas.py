"""
Pydantic schemas for all agent inputs and outputs.

Every LLM response is validated against these schemas. If validation fails,
the agent retries with an error-correction prompt. This is a real production
pattern — not just "calling an API".
"""
from pydantic import BaseModel, Field


class SubQuestionPlan(BaseModel):
    """Output of the Planner Agent."""
    sub_questions: list[str] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Focused, non-overlapping sub-questions that together cover the topic.",
    )


class CriticVerdict(BaseModel):
    """Output of the Critic Agent.
    
    The Critic scores the Researcher's work on multiple axes and either
    approves or rejects with specific, actionable feedback.
    """
    approved: bool = Field(
        ...,
        description="Whether the research passes quality review.",
    )
    grounding_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0-1: Are claims backed by cited sources?",
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0-1: Does the answer fully address the question?",
    )
    recency_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0-1: How current/recent are the sources?",
    )
    feedback: str = Field(
        ...,
        description="If rejected: exactly what's wrong. If approved: brief note.",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Exact claims from the research that lack source backing.",
    )


class ResearchFinding(BaseModel):
    """Validated output from a single Researcher Agent run."""
    question: str = Field(..., description="The sub-question that was researched.")
    answer: str = Field(..., description="The research findings with citations.")
    sources: list[str] = Field(
        default_factory=list,
        description="URLs cited in the answer.",
    )
    critic_attempts: int = Field(
        default=1,
        description="How many Critic review rounds this took.",
    )
    critic_scores: CriticVerdict | None = Field(
        default=None,
        description="Final Critic verdict (the approving one, or last if force-accepted).",
    )


class AgentMessage(BaseModel):
    """Represents a message passed between agents via the Supervisor."""
    sender: str = Field(..., description="Agent role that sent this message.")
    receiver: str = Field(..., description="Agent role this message is for.")
    message_type: str = Field(
        ...,
        description="Type: 'task', 'result', 'feedback', 'approval', 'rejection'.",
    )
    content: str = Field(..., description="The actual message content.")
    metadata: dict = Field(default_factory=dict, description="Any extra structured data.")


class ResearchReport(BaseModel):
    """Final output of the entire multi-agent pipeline."""
    topic: str
    report: str = Field(..., description="The final synthesized report.")
    findings: list[ResearchFinding] = Field(
        default_factory=list,
        description="Individual research findings that went into the report.",
    )
    metrics: dict = Field(default_factory=dict, description="Run metrics snapshot.")

class EvaluationScore(BaseModel):
    """Output of the LLM-as-judge Evaluator."""
    factual_accuracy: int = Field(..., ge=1, le=10, description="1-10 score for factual correctness.")
    citation_quality: int = Field(..., ge=1, le=10, description="1-10 score for presence and quality of citations.")
    recency: int = Field(..., ge=1, le=10, description="1-10 score for how up-to-date the information is.")
    completeness: int = Field(..., ge=1, le=10, description="1-10 score for thoroughness.")
    reasoning: str = Field(..., description="Explanation for the given scores.")

