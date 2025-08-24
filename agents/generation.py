"""
Tweet generation node
"""
from langchain_core.messages import HumanMessage, SystemMessage
from config import get_prompt, TweetAgentConfig
from models import AgentState
from .utils import on_step_logger
from .error_handler import with_retry_and_timeout, validate_state_input
from .monitoring import track_request
from .input_sanitizer import sanitize_topic, sanitize_language, validate_and_sanitize_state
from .llm_provider import get_model_manager, ModelType

# Get model manager
config = TweetAgentConfig()
model_manager = get_model_manager(config)


@with_retry_and_timeout(config)
def tweet_generation(state: AgentState) -> dict:
    """
    Tweet generation node with error handling and monitoring
    
    Args:
        state: Current agent state
        
    Returns:
        dict: Updates for the state (new messages, increased iteration)
    """
    with track_request("tweet_generation"):
        # Validation and sanitization of the input state
        if not validate_state_input(state):
            raise ValueError("Invalid agent state")
        
        # Sanitize the state
        state = validate_and_sanitize_state(state)
        
        lang = sanitize_language(state.get("language", "ru"))
        raw_topic = next(
            (m.content for m in state["messages"] if isinstance(m, HumanMessage)),
            "AI Productivity"
        )
        
        # Sanitize the topic
        topic = sanitize_topic(raw_topic)

        sys_msg = SystemMessage(content=get_prompt(lang, "gen_sys"))
        user_msg = HumanMessage(content=get_prompt(lang, "gen_user").format(topic=topic))

        # Use LLMProvider for generation
        provider = model_manager.get_provider(ModelType.GENERATION)
        model_response = provider.invoke([sys_msg, user_msg])
        
        # Convert response to AIMessage
        resp = model_response.to_ai_message()

        # Log state
        on_step_logger("generation", state)

        return {
            "messages": [resp],        # add_messages will add this to history
            "iter": state["iter"] + 1, # increase iteration counter
            # Add step tracking
            "steps": state.get("steps", []) + [{
                "type": "generation",
                "title": "Tweet Generation",
                "content": resp.content[:100] + "..." if len(resp.content) > 100 else resp.content,
                "score": None,
                "issues": None,
                "tips": None
            }]
        }