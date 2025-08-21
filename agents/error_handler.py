"""
Module for error handling and resilience
"""
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps
from config import TweetAgentConfig
from .monitoring import get_correlation_id, get_metrics_collector, update_request_tokens

# Logging setup
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base API error"""
    pass

class TimeoutError(APIError):
    """Timeout error"""
    pass

class ValidationError(Exception):
    """Validation error"""
    pass


def with_retry_and_timeout(config: TweetAgentConfig = None):
    """
    Decorator for adding retry logic and error handling with monitoring
    """
    if config is None:
        config = TweetAgentConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            correlation_id = get_correlation_id()
            metrics_collector = get_metrics_collector()
            
            # Get correlation_id for logging
            log_extra = {"correlation_id": correlation_id} if correlation_id else {}
            
            for attempt in range(config.max_retries + 1):  # +1 for first attempt
                try:
                    # Log attempt if it's not the first one
                    if attempt > 0:
                        logger.info(
                            f"Попытка {attempt + 1}/{config.max_retries + 1} для функции {func.__name__}",
                            extra=log_extra
                        )
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # If successful - return result
                    return result
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Error in {func.__name__}: {str(e)}",
                        extra={**log_extra, "error": str(e), "attempt": attempt + 1}
                    )
                    
                    # If this is the last attempt - don't wait
                    if attempt == config.max_retries:
                        break
                    
                    # Calculate delay
                    if config.exponential_backoff:
                        delay = config.retry_delay * (2 ** attempt)
                    else:
                        delay = config.retry_delay
                    
                    logger.info(
                        f"Waiting {delay} seconds before next attempt...",
                        extra={**log_extra, "delay_seconds": delay}
                    )
                    time.sleep(delay)
            
            # If all attempts failed - handle error
            if config.fallback_enabled:
                logger.error(
                    f"All attempts failed for {func.__name__}. Using fallback.",
                    extra={**log_extra, "total_attempts": config.max_retries + 1}
                )
                return create_fallback_response(func.__name__, config)
            else:
                logger.error(
                    f"All attempts failed for {func.__name__}. Raising exception.",
                    extra={**log_extra, "total_attempts": config.max_retries + 1}
                )
                raise last_exception
        
        return wrapper
    return decorator


def create_fallback_response(func_name: str, config: TweetAgentConfig) -> dict:
    """
    Create fallback response depending on function type
    """
    if "generation" in func_name or "rewrite" in func_name:
        from langchain_core.messages import AIMessage
        fallback_content = config.fallback_message
        return {"messages": [AIMessage(content=fallback_content)]}
    
    elif "critique" in func_name:
        from langchain_core.messages import SystemMessage
        return {
            "messages": [SystemMessage(content="Критика недоступна из-за технических проблем")],
            "needs_revision": False,  # Don't require revision on fallback
            "score": 0.5,  # Average score
            "critique_items": ["Technical error"]
        }
    
    else:
        return {"error": "Unknown error"}


def validate_state_input(state: dict) -> bool:
    """
    Validation of the agent state
    """
    try:
        from models import validate_agent_state
        return validate_agent_state(state)
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False


def validate_llm_response(response: Any) -> bool:
    """
    Validation of the LLM response
    """
    try:
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, str) and content.strip():
                return True
        return False
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False


def safe_llm_invoke(llm, messages, config: TweetAgentConfig = None):
    """
    Safe LLM call with error handling and metrics collection
    """
    if config is None:
        config = TweetAgentConfig()
    
    try:
        # Validate input messages
        if not messages or not isinstance(messages, list):
            raise ValidationError("Invalid input messages")
        
        # Call LLM
        response = llm.invoke(messages)
        
        # Validate response
        if not validate_llm_response(response):
            raise ValidationError("Invalid response from LLM")
        
        # Extract token usage metrics if available
        tokens_used = extract_token_usage(response)
        
        # Update metrics if correlation_id and tokens are available
        correlation_id = get_correlation_id()
        if correlation_id and tokens_used:
            update_request_tokens(correlation_id, tokens_used)
        
        return response
    
    except Exception as e:
        correlation_id = get_correlation_id()
        log_extra = {"correlation_id": correlation_id} if correlation_id else {}
        logger.error(f"Error calling LLM: {e}", extra=log_extra)
        raise APIError(f"LLM API error: {e}")


def extract_token_usage(response) -> Optional[int]:
    """
    Extract token usage information from LLM response
    """
    try:
        # Check different possible attributes for tokens
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            if hasattr(usage, 'total_tokens'):
                return usage.total_tokens
        
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if 'token_usage' in metadata:
                token_usage = metadata['token_usage']
                if 'total_tokens' in token_usage:
                    return token_usage['total_tokens']
        
        # OpenAI specific - check additional_kwargs
        if hasattr(response, 'additional_kwargs'):
            if 'usage' in response.additional_kwargs:
                usage = response.additional_kwargs['usage']
                if 'total_tokens' in usage:
                    return usage['total_tokens']
                    
        return None
    except Exception as e:
        logger.debug(f"Failed to extract token usage: {e}")
        return None