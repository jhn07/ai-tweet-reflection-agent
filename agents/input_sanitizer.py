"""
Module for sanitizing user input data
"""
import re
import html
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SanitizationConfig:
    """Configuration for sanitizing input data"""
    max_length: int = 500
    min_length: int = 5
    allowed_languages: List[str] = None
    blocked_patterns: List[str] = None
    remove_html: bool = True
    remove_sql_keywords: bool = True
    remove_script_tags: bool = True
    
    def __post_init__(self):
        if self.allowed_languages is None:
            self.allowed_languages = ['ru', 'en']
        if self.blocked_patterns is None:
            self.blocked_patterns = [
                r'<script.*?</script>',  # Script tags
                r'javascript:',          # JavaScript URLs
                r'on\w+\s*=',           # Event handlers
                r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b',  # SQL keywords
            ]


class InputSanitizer:
    """Class for sanitizing user input data"""
    
    def __init__(self, config: SanitizationConfig = None):
        self.config = config or SanitizationConfig()
    
    def sanitize_topic(self, topic: str) -> str:
        """
        Sanitize the topic for a tweet
        
        Args:
            topic: Original topic from user
            
        Returns:
            str: Cleaned and safe topic
            
        Raises:
            ValueError: If topic is not valid
        """
        if not topic or not isinstance(topic, str):
            raise ValueError("Topic must be a non-empty string")
        
        original_topic = topic
        
        # 1. Basic cleanup
        topic = self._basic_cleanup(topic)
        
        # 2. Check length
        if len(topic) > self.config.max_length:
            topic = topic[:self.config.max_length].strip()
            logger.info(f"Topic truncated to {self.config.max_length} characters")
        
        if len(topic) < self.config.min_length:
            raise ValueError(f"Topic is too short (minimum {self.config.min_length} characters)")
        
        # 3. Remove HTML if needed
        if self.config.remove_html:
            topic = self._remove_html(topic)
        
        # 4. Check for blocked patterns
        topic = self._remove_blocked_patterns(topic)
        
        # 5. Additional security
        topic = self._security_sanitization(topic)
        
        # 6. Final validation
        if not topic.strip():
            raise ValueError("Topic cannot be empty after sanitization")
        
        # Log if there was a significant modification
        if original_topic.strip() != topic.strip():
            logger.info(f"Topic was sanitized: '{original_topic[:50]}...' -> '{topic[:50]}...'")
        
        return topic.strip()
    
    def sanitize_language(self, language: str) -> str:
        """
        Sanitize the language parameter
        
        Args:
            language: Language code
            
        Returns:
            str: Validated language code
        """
        if not language or not isinstance(language, str):
            return "ru"  # Default
        
        language = language.lower().strip()
        
        if language not in self.config.allowed_languages:
            logger.warning(f"Unsupported language: {language}, using 'ru'")
            return "ru"
        
        return language
    
    def _basic_cleanup(self, text: str) -> str:
        """Basic text cleanup"""
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters except basic ones
        text = re.sub(r'[^\w\s\-.,!?;:()\[\]{}"\'/№@#$%^&*+=<>|\\`~]', '', text)
        
        return text.strip()
    
    def _remove_html(self, text: str) -> str:
        """Remove HTML tags and decode HTML entities"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        return text
    
    def _remove_blocked_patterns(self, text: str) -> str:
        """Remove blocked patterns"""
        for pattern in self.config.blocked_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def _security_sanitization(self, text: str) -> str:
        """Additional security sanitization"""
        # Remove potentially dangerous sequences
        dangerous_patterns = [
            r'\.\./',           # Directory traversal
            r'__[a-zA-Z]+__',   # Python magic methods
            r'\$\{.*?\}',       # Template injection
            r'\{\{.*?\}\}',     # Template injection
            r'<%.*?%>',         # Server-side includes
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text)
        
        # Limit the number of special characters
        if len(re.findall(r'[<>{}$%]', text)) > 5:
            text = re.sub(r'[<>{}$%]', '', text)
            logger.warning("Removed excessive special characters")
        
        return text
    
    def validate_state_input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validation and sanitization of the input state
        
        Args:
            state: Agent state
            
        Returns:
            Dict: Sanitized state
        """
        sanitized_state = state.copy()
        
        # Sanitize the language
        if 'language' in sanitized_state:
            sanitized_state['language'] = self.sanitize_language(
                sanitized_state['language']
            )
        
        # Sanitize the messages
        if 'messages' in sanitized_state:
            sanitized_messages = []
            for msg in sanitized_state['messages']:
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    # Sanitize the message content (more gently than the topic)
                    sanitized_content = self._basic_cleanup(msg.content)
                    if self.config.remove_html:
                        sanitized_content = self._remove_html(sanitized_content)
                    
                    # Create a new message with sanitized content
                    new_msg = type(msg)(content=sanitized_content)
                    sanitized_messages.append(new_msg)
                else:
                    sanitized_messages.append(msg)
            
            sanitized_state['messages'] = sanitized_messages
        
        return sanitized_state


# Global sanitizer
_default_sanitizer = InputSanitizer()


def sanitize_topic(topic: str, config: SanitizationConfig = None) -> str:
    """Global function for sanitizing the topic"""
    sanitizer = InputSanitizer(config) if config else _default_sanitizer
    return sanitizer.sanitize_topic(topic)


def sanitize_language(language: str, config: SanitizationConfig = None) -> str:
    """Global function for sanitizing the language"""
    sanitizer = InputSanitizer(config) if config else _default_sanitizer
    return sanitizer.sanitize_language(language)


def validate_and_sanitize_state(state: Dict[str, Any], config: SanitizationConfig = None) -> Dict[str, Any]:
    """Global function for validation and sanitization of the state"""
    sanitizer = InputSanitizer(config) if config else _default_sanitizer
    return sanitizer.validate_state_input(state)