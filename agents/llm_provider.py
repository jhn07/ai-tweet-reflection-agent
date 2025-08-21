"""
LLM Provider abstraction layer for managing different models
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from config import TweetAgentConfig
from .cache import get_cache

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Model types"""
    GENERATION = "generation"
    CRITIQUE = "critique"
    REWRITE = "rewrite"


class ProviderType(Enum):
    """Provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """Model configuration"""
    provider: ProviderType
    model_name: str
    temperature: float = 0.4
    max_tokens: Optional[int] = None
    timeout: int = 120
    cost_per_token: float = 0.0  # For cost calculation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "cost_per_token": self.cost_per_token
        }


@dataclass
class ModelResponse:
    """Standardized model response"""
    content: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    cost: Optional[float] = None
    model_name: Optional[str] = None
    provider: Optional[ProviderType] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_ai_message(self) -> AIMessage:
        """Conversion to AIMessage for compatibility"""
        return AIMessage(content=self.content)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._client = None
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the provider"""
        pass
    
    @abstractmethod
    def invoke(self, messages: List[BaseMessage]) -> ModelResponse:
        """Invoke the model"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check the availability of the provider"""
        pass
    
    @abstractmethod
    def get_cost_estimate(self, messages: List[BaseMessage]) -> float:
        """Estimate the cost of the request"""
        pass
    
    def __str__(self) -> str:
        return f"{self.config.provider.value}:{self.config.model_name}"


class OpenAIProvider(LLMProvider):
    """OpenAI provider with caching"""
    
    def __init__(self, config: ModelConfig, enable_cache: bool = True):
        super().__init__(config)
        self.enable_cache = enable_cache
        self._cache = get_cache() if enable_cache else None
    
    def initialize(self) -> None:
        """Initialize OpenAI client"""
        try:
            self._client = ChatOpenAI(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            logger.info(f"Initialized OpenAI provider: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Error initializing OpenAI provider: {e}")
            raise
    
    def invoke(self, messages: List[BaseMessage]) -> ModelResponse:
        """Invoke OpenAI with caching"""
        if not self._client:
            self.initialize()
        
        # Check cache if enabled
        if self.enable_cache and self._cache:
            model_config = self.config.to_dict()
            cached_entry = self._cache.get(messages, model_config)
            
            if cached_entry:
                logger.debug(f"Using cached response for {self.config.model_name}")
                return ModelResponse(
                    content=cached_entry.content,
                    tokens_used=cached_entry.tokens_used,
                    response_time=0.0,  # Cache = instant response
                    cost=cached_entry.cost,
                    model_name=cached_entry.model_name,
                    provider=ProviderType.OPENAI,
                    metadata=cached_entry.metadata
                )
        
        start_time = time.time()
        
        try:
            response = self._client.invoke(messages)
            response_time = time.time() - start_time
            
            # Extract token usage information
            tokens_used = self._extract_token_usage(response)
            cost = self._calculate_cost(tokens_used) if tokens_used else None
            metadata = self._extract_metadata(response)
            
            model_response = ModelResponse(
                content=response.content,
                tokens_used=tokens_used,
                response_time=response_time,
                cost=cost,
                model_name=self.config.model_name,
                provider=ProviderType.OPENAI,
                metadata=metadata
            )
            
            # Save to cache if enabled
            if self.enable_cache and self._cache:
                model_config = self.config.to_dict()
                self._cache.put(
                    messages=messages,
                    model_config=model_config,
                    content=response.content,
                    tokens_used=tokens_used,
                    cost=cost,
                    model_name=self.config.model_name,
                    metadata=metadata
                )
            
            return model_response
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Error calling OpenAI: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check the availability of OpenAI"""
        try:
            if not self._client:
                self.initialize()
            
            # Simple test request
            from langchain_core.messages import HumanMessage
            self._client.invoke([HumanMessage(content="test")])
            return True
        except Exception as e:
            logger.warning(f"OpenAI недоступен: {e}")
            return False
    
    def get_cost_estimate(self, messages: List[BaseMessage]) -> float:
        """Estimate the cost of the request"""
        # Rough estimate based on message length
        total_chars = sum(len(msg.content) for msg in messages if hasattr(msg, 'content'))
        estimated_tokens = total_chars // 4  # Rough estimate: 4 characters = 1 token
        return estimated_tokens * self.config.cost_per_token
    
    def _extract_token_usage(self, response) -> Optional[int]:
        """Extract token usage information"""
        try:
            # Check different possible attributes
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                if hasattr(usage, 'total_tokens'):
                    return usage.total_tokens
            
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                if 'token_usage' in metadata:
                    return metadata['token_usage'].get('total_tokens')
            
            if hasattr(response, 'additional_kwargs'):
                if 'usage' in response.additional_kwargs:
                    return response.additional_kwargs['usage'].get('total_tokens')
                    
            return None
        except Exception as e:
            logger.debug(f"Failed to extract tokens: {e}")
            return None
    
    def _calculate_cost(self, tokens: int) -> float:
        """Calculate the cost based on tokens"""
        return tokens * self.config.cost_per_token
    
    def _extract_metadata(self, response) -> Dict[str, Any]:
        """Extract additional metadata"""
        metadata = {}
        
        try:
            if hasattr(response, 'response_metadata'):
                metadata['response_metadata'] = response.response_metadata
            if hasattr(response, 'additional_kwargs'):
                metadata['additional_kwargs'] = response.additional_kwargs
        except Exception as e:
            logger.debug(f"Failed to extract metadata: {e}")
        
        return metadata


class ModelManager:
    """Manager for managing different models"""
    
    def __init__(self, config: TweetAgentConfig = None):
        self.config = config or TweetAgentConfig()
        self._providers: Dict[ModelType, LLMProvider] = {}
        self._fallback_providers: Dict[ModelType, List[LLMProvider]] = {}
        self._initialize_default_providers()
    
    def _initialize_default_providers(self):
        """Initialize default providers"""
        # Main models
        generation_config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name=self.config.model_name,
            temperature=self.config.temperature,
            timeout=self.config.request_timeout,
            cost_per_token=0.000002  # Rough estimate for gpt-4o-mini
        )
        
        critique_config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name=self.config.model_name,
            temperature=self.config.critique_temperature,
            timeout=self.config.request_timeout,
            cost_per_token=0.000002
        )
        
        rewrite_config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name=self.config.model_name,
            temperature=self.config.temperature,
            timeout=self.config.request_timeout,
            cost_per_token=0.000002
        )
        
        # Create providers
        self._providers[ModelType.GENERATION] = OpenAIProvider(generation_config)
        self._providers[ModelType.CRITIQUE] = OpenAIProvider(critique_config)
        self._providers[ModelType.REWRITE] = OpenAIProvider(rewrite_config)
        
        # Initialize all providers
        for model_type, provider in self._providers.items():
            try:
                provider.initialize()
                logger.info(f"Initialized {model_type.value}: {provider}")
            except Exception as e:
                logger.error(f"Error initializing {model_type.value}: {e}")
    
    def get_provider(self, model_type: ModelType) -> LLMProvider:
        """Get the provider for the model type"""
        if model_type not in self._providers:
            raise ValueError(f"Provider for {model_type.value} not found")
        
        provider = self._providers[model_type]
        
        # Check availability
        if not provider.is_available():
            logger.warning(f"Main provider {provider} is not available")
            
            # Try to use fallback
            if model_type in self._fallback_providers:
                for fallback in self._fallback_providers[model_type]:
                    if fallback.is_available():
                        logger.info(f"Using fallback provider: {fallback}")
                        return fallback
            
            # If no fallback providers are available, use the main one
            logger.warning(f"No fallback providers are available, using the main one")
        
        return provider
    
    def add_fallback_provider(self, model_type: ModelType, provider: LLMProvider):
        """Add a fallback provider"""
        if model_type not in self._fallback_providers:
            self._fallback_providers[model_type] = []
        
        provider.initialize()
        self._fallback_providers[model_type].append(provider)
        logger.info(f"Added fallback provider for {model_type.value}: {provider}")
    
    def switch_provider(self, model_type: ModelType, new_config: ModelConfig):
        """Switch the provider for the model type"""
        # Create a new provider
        if new_config.provider == ProviderType.OPENAI:
            new_provider = OpenAIProvider(new_config)
        else:
            raise ValueError(f"Unsupported provider: {new_config.provider}")
        
        # Initialize
        new_provider.initialize()
        
        # Replace
        old_provider = self._providers.get(model_type)
        self._providers[model_type] = new_provider
        
        logger.info(f"Switched provider {model_type.value}: {old_provider} -> {new_provider}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of all providers"""
        status = {}
        
        for model_type, provider in self._providers.items():
            status[model_type.value] = {
                "provider": str(provider),
                "available": provider.is_available(),
                "config": provider.config.to_dict()
            }
        
        return status
    
    def get_total_cost_estimate(self, messages: List[BaseMessage]) -> Dict[str, float]:
        """Get the cost estimate for all model types"""
        costs = {}
        
        for model_type, provider in self._providers.items():
            try:
                cost = provider.get_cost_estimate(messages)
                costs[model_type.value] = cost
            except Exception as e:
                logger.warning(f"Failed to estimate cost for {model_type.value}: {e}")
                costs[model_type.value] = 0.0
        
        costs['total'] = sum(costs.values())
        return costs


# Global model manager
_model_manager = None


def get_model_manager(config: TweetAgentConfig = None) -> ModelManager:
    """Get the global model manager"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(config)
    return _model_manager


def reset_model_manager():
    """Reset the global model manager"""
    global _model_manager
    _model_manager = None