from typing import Annotated, NotRequired, List, Tuple
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, field_validator
from langgraph.graph.message import add_messages


class CritiqueSchema(BaseModel):
    """Schema for tweet critique"""
    needs_revision: bool = Field(..., description="Needs revision of the tweet")
    issues: List[str] = Field(default_factory=list, description="List of issues")
    tips: List[str] = Field(default_factory=list, description="Short tips on how to fix")
    score: float = Field(ge=0.0, le=1.0, description="Tweet quality score")

    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        """Ensure score is within the correct range"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score must be between 0.0 and 1.0')
        return v

    @field_validator('issues', 'tips')
    @classmethod
    def validate_lists_not_empty(cls, v):
        """Ensure lists are not empty"""
        if isinstance(v, list):
            return [item.strip() for item in v if item.strip()]
        return v


class AgentState(TypedDict):
    """State of the agent for LangGraph"""
    # History of messages. Use add_messages reducer for clean merge.
    messages: Annotated[list, add_messages]
    # Flag, needs revision of the tweet after critique
    needs_revision: bool
    # Current iteration (for protection from infinite loop)
    iter: int
    # Optional limit of iterations (can be overridden at start)
    max_iters: NotRequired[int]
    # List of critique items
    critique_items: NotRequired[List[str]]
    
    # Additional fields
    language: NotRequired[str]                        # "ru" or "en"
    score: NotRequired[float]                         # last score
    best_tweet: NotRequired[str]                      # best version by score
    best_score: NotRequired[float]                    # maximum score
    candidates: NotRequired[List[Tuple[str, float]]]  # (tweet, score)
    stop_reason: NotRequired[str]                     # accepted | max_iters


def validate_agent_state(state: AgentState) -> bool:
    """Validation of the agent state"""
    try:
        # Check required fields
        if not isinstance(state.get("messages"), list):
            return False
        if not isinstance(state.get("needs_revision"), bool):
            return False
        if not isinstance(state.get("iter"), int) or state.get("iter") < 0:
            return False
            
        # Check optional fields if they exist
        if "score" in state:
            score = state["score"]
            if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
                return False
                
        if "language" in state:
            if state["language"] not in ["ru", "en"]:
                return False
                
        return True
    except Exception:
        return False