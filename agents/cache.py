"""
System of caching for LLM responses and prompts
"""
import hashlib
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry"""
    content: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    model_name: Optional[str] = None
    timestamp: float = 0.0
    access_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the entry is expired"""
        return (time.time() - self.timestamp) > ttl_seconds
    
    def touch(self):
        """Update the last access time and counter"""
        self.access_count += 1
        return self


class LLMCache:
    """
    System of caching for LLM responses
    
    Features:
    - In-memory caching with configurable TTL
    - LRU eviction policy
    - Thread-safe operations
    - Persistence (optional)
    - Cache usage metrics
    """
    
    def __init__(
        self, 
        max_size: int = 1000, 
        ttl_seconds: int = 3600,  # 1 hour
        enable_persistence: bool = True,
        cache_dir: str = ".cache"
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_persistence = enable_persistence
        self.cache_dir = Path(cache_dir)
        
        # In-memory storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU
        self._lock = threading.RLock()
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Create cache directory
        if self.enable_persistence:
            self.cache_dir.mkdir(exist_ok=True)
            self._load_persistent_cache()
    
    def _generate_key(self, messages: List[BaseMessage], model_config: Dict[str, Any]) -> str:
        """Generate cache key from messages and model configuration"""
        # Create hash from messages content + model configuration
        content = {
            'messages': [
                {
                    'type': msg.__class__.__name__,
                    'content': msg.content if hasattr(msg, 'content') else str(msg)
                }
                for msg in messages
            ],
            'model_config': {
                k: v for k, v in model_config.items() 
                if k in ['model_name', 'temperature', 'max_tokens']
            }
        }
        
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def get(self, messages: List[BaseMessage], model_config: Dict[str, Any]) -> Optional[CacheEntry]:
        """Get entry from cache"""
        key = self._generate_key(messages, model_config)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss for key: {key[:8]}...")
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if entry.is_expired(self.ttl_seconds):
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._misses += 1
                logger.debug(f"Cache entry expired for key: {key[:8]}...")
                return None
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._hits += 1
            logger.debug(f"Cache hit for key: {key[:8]}...")
            
            return entry.touch()
    
    def put(
        self, 
        messages: List[BaseMessage], 
        model_config: Dict[str, Any],
        content: str,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add entry to cache"""
        key = self._generate_key(messages, model_config)
        
        entry = CacheEntry(
            content=content,
            tokens_used=tokens_used,
            cost=cost,
            model_name=model_name,
            metadata=metadata
        )
        
        with self._lock:
            # If cache is full, evict least used entries
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = entry
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            logger.debug(f"Cache entry added for key: {key[:8]}...")
            
            # Persistence (async)
            if self.enable_persistence:
                threading.Thread(
                    target=self._save_entry_to_disk, 
                    args=(key, entry),
                    daemon=True
                ).start()
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._access_order:
            return
            
        lru_key = self._access_order.pop(0)
        if lru_key in self._cache:
            del self._cache[lru_key]
            self._evictions += 1
            logger.debug(f"Evicted LRU entry: {lru_key[:8]}...")
    
    def _save_entry_to_disk(self, key: str, entry: CacheEntry):
        """Save entry to disk"""
        try:
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(entry), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")
    
    def _load_persistent_cache(self):
        """Load cache from disk"""
        try:
            loaded_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    entry = CacheEntry(**data)
                    key = cache_file.stem
                    
                    # Check TTL when loading
                    if not entry.is_expired(self.ttl_seconds):
                        self._cache[key] = entry
                        self._access_order.append(key)
                        loaded_count += 1
                    else:
                        # Remove expired file
                        cache_file.unlink()
                        
                except Exception as e:
                    logger.warning(f"Failed to load {cache_file}: {e}")
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} entries from persistent cache")
                
        except Exception as e:
            logger.warning(f"Failed to load persistent cache: {e}")
    
    def clear(self):
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            
        # Clear persistent cache
        if self.enable_persistence:
            try:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
                logger.info("Persistent cache cleared")
            except Exception as e:
                logger.warning(f"Failed to clear persistent cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self._evictions,
                'ttl_seconds': self.ttl_seconds,
                'persistence_enabled': self.enable_persistence
            }
    
    def cleanup_expired(self):
        """Clean up expired entries"""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired(self.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            if expired_keys:
                logger.info(f"Removed {len(expired_keys)} expired entries")
    
    def get_cache_info(self) -> List[Dict[str, Any]]:
        """Get information about entries in cache"""
        with self._lock:
            info = []
            for key, entry in self._cache.items():
                info.append({
                    'key': key[:12] + "...",
                    'model': entry.model_name,
                    'tokens': entry.tokens_used,
                    'cost': entry.cost,
                    'access_count': entry.access_count,
                    'age_seconds': int(time.time() - entry.timestamp),
                    'content_preview': entry.content[:50] + "..." if len(entry.content) > 50 else entry.content
                })
            
            # Sort by usage frequency
            info.sort(key=lambda x: x['access_count'], reverse=True)
            return info


# Global cache instance
_global_cache: Optional[LLMCache] = None


def get_cache(
    max_size: int = 1000, 
    ttl_seconds: int = 3600, 
    enable_persistence: bool = True
) -> LLMCache:
    """Get global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache(
            max_size=max_size,
            ttl_seconds=ttl_seconds,
            enable_persistence=enable_persistence
        )
    return _global_cache


def reset_cache():
    """Сбросить глобальный кэш"""
    global _global_cache
    if _global_cache:
        _global_cache.clear()
    _global_cache = None