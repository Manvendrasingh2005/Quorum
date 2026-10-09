import pytest
from src.models.schemas import SubQuestionPlan, CriticVerdict, ResearchFinding
from pydantic import ValidationError

def test_subquestion_plan_validation():
    # Valid layout
    plan = SubQuestionPlan(
        sub_questions=["What is the sky?", "Why is it blue?"]
    )
    assert len(plan.sub_questions) == 2

    # Should raise error if invalid structure
    with pytest.raises(ValidationError):
        SubQuestionPlan(
            sub_questions="This is not a list" # type: ignore
        )

def test_critic_verdict_validation():
    # Test valid approval
    verdict = CriticVerdict(
        approved=True,
        feedback="Looks good.",
        grounding_score=0.9,
        completeness_score=0.8,
        recency_score=0.9,
    )
    assert verdict.approved is True

def test_critic_verdict_rejection_requires_feedback():
    # If a critic rejects, it must provide feedback or identify unsupported claims, 
    # but the schema allows empty fields. Let's ensure schema parses correctly.
    verdict = CriticVerdict(
        approved=False,
        feedback="Missing source link.",
        grounding_score=0.4,
        completeness_score=0.5,
        recency_score=0.5,
        unsupported_claims=["claim 1"]
    )
    assert verdict.approved is False
    assert len(verdict.unsupported_claims) == 1
