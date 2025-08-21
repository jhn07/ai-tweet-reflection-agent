"""
Rewrite node for tweets
"""
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import get_prompt, TweetAgentConfig
from models import AgentState
from .utils import last_ai_text, on_step_logger
from .error_handler import with_retry_and_timeout, validate_state_input
from .monitoring import track_request
from .input_sanitizer import sanitize_language, validate_and_sanitize_state
from .llm_provider import get_model_manager, ModelType

# Get model manager
config = TweetAgentConfig()
model_manager = get_model_manager(config)


@with_retry_and_timeout(config)
def tweet_rewrite(state: AgentState) -> dict:
    """
    Rewrite node for tweets with error handling and monitoring
    
    Args:
        state: Current agent state
        
    Returns:
        dict: Updates for the state (rewritten tweet, increased iteration)
    """
    with track_request("tweet_rewrite"):
        # Validation and sanitization of the input state
        if not validate_state_input(state):
            raise ValueError("Invalid agent state")
        
        # Sanitize the state
        state = validate_and_sanitize_state(state)
        
        # Take the last tweet and list of critique items
        lang = sanitize_language(state.get("language", "ru"))
        tweet = last_ai_text(state["messages"])
        issues = state.get("critique_items", [])

        sys_msg = SystemMessage(content=get_prompt(lang, "rewrite_sys"))
        user_msg = HumanMessage(content=get_prompt(lang, "rewrite_user").format(tweet=tweet, issues="\n- ".join(issues)))

        # Use LLMProvider for rewriting
        provider = model_manager.get_provider(ModelType.REWRITE)
        model_response = provider.invoke([sys_msg, user_msg])
        
        # Convert response to AIMessage
        text = model_response.content.strip()
        
        # Trim to 280 characters if needed
        if len(text) > 280:
            text = text[:277] + "..."
            
        resp = AIMessage(content=text)

        # Log state
        on_step_logger("rewrite", state)

        return {
            "messages": [resp],
            "iter": state["iter"] + 1, # count rewrite as a new attempt
            # critique_items will be left as is; the next node will check everything again
        }