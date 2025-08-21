"""
Critique node for tweets
"""
import json
from langchain_core.messages import HumanMessage, SystemMessage
from config import get_prompt, TweetAgentConfig, QUALITY_SCORE_THRESHOLD
from models import AgentState, CritiqueSchema
from .utils import last_ai_text, on_step_logger
from .error_handler import with_retry_and_timeout, validate_state_input
from .monitoring import track_request
from .input_sanitizer import sanitize_language, validate_and_sanitize_state
from .llm_provider import get_model_manager, ModelType

# Get model manager
config = TweetAgentConfig()
model_manager = get_model_manager(config)


@with_retry_and_timeout(config)
def tweet_critique(state: AgentState) -> dict:
    """
    Critique node for tweets with error handling and monitoring
    
    Args:
        state: Current agent state
        
    Returns:
        dict: Updates for the state (critique, needs revision, score)
    """
    with track_request("tweet_critique"):
        # Validation and sanitization of the input state
        if not validate_state_input(state):
            raise ValueError("Invalid agent state")
        
        # Sanitize the state
        state = validate_and_sanitize_state(state)
        
        lang = sanitize_language(state.get("language", "ru"))
        tweet = last_ai_text(state["messages"])

        sys_msg = SystemMessage(content=get_prompt(lang, "crit_sys"))
        user_msg = HumanMessage(content=get_prompt(lang, "crit_user").format(tweet=tweet))

        # Use LLMProvider for critique
        try:
            # Add instruction for structured answer
            structured_prompt = HumanMessage(content=f"""{user_msg.content}
            
Answer in JSON format:
{{
    "needs_revision": true/false,
    "issues": ["list of issues"],
    "tips": ["list of tips"],
    "score": 0.0-1.0
}}""")
            
            provider = model_manager.get_provider(ModelType.CRITIQUE)
            model_response = provider.invoke([sys_msg, structured_prompt])
            
            # Parse JSON answer
            try:
                response_data = json.loads(model_response.content)
                result = CritiqueSchema(**response_data)
            except (json.JSONDecodeError, ValueError) as parse_error:
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', model_response.content, re.DOTALL)
                if json_match:
                    try:
                        response_data = json.loads(json_match.group())
                        result = CritiqueSchema(**response_data)
                    except Exception:
                        raise parse_error
                else:
                    raise parse_error
                    
        except Exception:
            # Fallback for critique
            return {
                "messages": [SystemMessage(content="Критика недоступна из-за технических проблем")],
                "needs_revision": False,
                "score": 0.5,
                "critique_items": ["Техническая ошибка"]
            }

        # logic «needs revision»: either model said, or score below threshold
        needs_revision = result.needs_revision or (result.score < QUALITY_SCORE_THRESHOLD)

        # save candidate and update best*
        candidates = state.get("candidates", [])
        candidates.append((tweet, result.score))

        best_tweet, best_score = state.get("best_tweet"), state.get("best_score", -1.0)
        if result.score > best_score:
            best_tweet, best_score = tweet, result.score
        
        # clear text in history
        if not needs_revision:
            critique_text = f"Critique: ok, tweet is good. score={result.score:.2f}"
        else:
            issues_txt = "\n- ".join(result.issues) if result.issues else "no obvious issues, but improve quality"
            tips_txt = ("\nTips:\n- " + "\n- ".join(result.tips)) if result.tips else ""
            critique_text = f"Critique (score={result.score:.2f}):\n- {issues_txt}{tips_txt}"

        # Log state
        on_step_logger("critique", state)

        return {
            "messages": [SystemMessage(content=critique_text)],
            "needs_revision": needs_revision,
            "critique_items": result.issues or result.tips, # save for rewrite
            "score": result.score,
            "candidates": candidates,
            "best_tweet": best_tweet,
            "best_score": best_score,
        }