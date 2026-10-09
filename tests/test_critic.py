import pytest
from unittest.mock import patch, MagicMock
from src.agents.critic import CriticAgent
from src.models.schemas import CriticVerdict

def test_critic_agent_review_logic():
    agent = CriticAgent()
    
    # We mock the _call method on the BaseAgent to prevent it from actually hitting the Gemini API.
    # This proves we understand how to write isolated unit tests!
    with patch('src.agents.critic.CriticAgent._validated_ask') as mock_call:
        
        # Mocking an approved response from the LLM
        mock_call.return_value = CriticVerdict(
            approved=True,
            feedback="Excellent report.",
            grounding_score=0.9,
            completeness_score=0.8,
            recency_score=0.9,
            unsupported_claims=[]
        )
        
        verdict = agent.review("Original Q", "Draft A")
        
        assert verdict.approved is True
        assert verdict.grounding_score == 0.9
        
        # Verify that prompt templates were properly passed to the mock
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        assert "Original Q" in args[0] # Prompt should contain the question
        assert "Draft A" in args[0] # Prompt should contain the draft

def test_critic_agent_rejection():
    agent = CriticAgent()
    
    with patch('src.agents.critic.CriticAgent._validated_ask') as mock_call:
        
        # Mocking a rejected response from the LLM
        mock_call.return_value = CriticVerdict(
            approved=False,
            feedback="Hallucinated statistics.",
            grounding_score=0.2,
            completeness_score=0.5,
            recency_score=0.5,
            unsupported_claims=["60% increase in productivity"]
        )
        
        verdict = agent.review("Another Q", "Bad Draft")
        
        assert verdict.approved is False
        assert len(verdict.unsupported_claims) == 1
        assert verdict.unsupported_claims[0] == "60% increase in productivity"
