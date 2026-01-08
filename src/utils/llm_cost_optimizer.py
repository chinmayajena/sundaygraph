"""LLM Cost Optimization Module

This module provides cost optimization features:
- Response caching to avoid duplicate API calls
- Token counting and cost tracking
- Model selection based on task complexity
- Request batching
- Prompt optimization
"""

from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import hashlib
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
import functools


class LLMCostOptimizer:
    """Optimizes LLM API costs through caching, token tracking, and smart model selection"""
    
    # Token pricing per 1M tokens (as of 2024)
    PRICING = {
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    }
    
    # Approximate tokens per character (rough estimate)
    CHARS_PER_TOKEN = 4
    
    def __init__(self, cache_ttl: int = 3600, enable_cache: bool = True):
        """
        Initialize cost optimizer
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            enable_cache: Whether to enable response caching
        """
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._stats = {
            "total_requests": 0,
            "cached_requests": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "total_cost": 0.0,
            "requests_by_model": defaultdict(int),
            "cost_by_model": defaultdict(float),
        }
        self._last_cleanup = time.time()
    
    def _get_cache_key(self, prompt: str, system_prompt: Optional[str] = None, model: str = "") -> str:
        """Generate cache key from prompt and model"""
        content = f"{model}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text"""
        return len(text) // self.CHARS_PER_TOKEN
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost for a request"""
        if model not in self.PRICING:
            logger.warning(f"Unknown model pricing for {model}, using gpt-3.5-turbo pricing")
            model = "gpt-3.5-turbo"
        
        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def get_cached_response(self, prompt: str, system_prompt: Optional[str] = None, model: str = "") -> Optional[Any]:
        """Get cached response if available"""
        if not self.enable_cache:
            return None
        
        # Cleanup old cache entries periodically
        if time.time() - self._last_cleanup > 300:  # Every 5 minutes
            self._cleanup_cache()
        
        cache_key = self._get_cache_key(prompt, system_prompt, model)
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self._stats["cached_requests"] += 1
                logger.debug(f"Cache hit for prompt (key: {cache_key[:16]}...)")
                return response
        
        return None
    
    def cache_response(self, prompt: str, response: Any, system_prompt: Optional[str] = None, model: str = ""):
        """Cache a response"""
        if not self.enable_cache:
            return
        
        cache_key = self._get_cache_key(prompt, system_prompt, model)
        self._cache[cache_key] = (response, time.time())
    
    def _cleanup_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        self._last_cleanup = current_time
    
    def select_model(self, task_complexity: str = "medium", prefer_cheap: bool = True) -> str:
        """
        Select appropriate model based on task complexity
        
        Args:
            task_complexity: "simple", "medium", "complex"
            prefer_cheap: Whether to prefer cheaper models
        
        Returns:
            Recommended model name
        """
        if prefer_cheap:
            if task_complexity == "simple":
                return "gpt-4o-mini"  # Cheapest option
            elif task_complexity == "medium":
                return "gpt-3.5-turbo"  # Good balance
            else:
                return "gpt-4o"  # More capable but still cost-effective
        else:
            if task_complexity == "simple":
                return "gpt-3.5-turbo"
            elif task_complexity == "medium":
                return "gpt-4o"
            else:
                return "gpt-4-turbo"  # Most capable
    
    def optimize_prompt(self, prompt: str, max_length: Optional[int] = None) -> str:
        """
        Optimize prompt to reduce token usage
        
        Args:
            prompt: Original prompt
            max_length: Maximum character length (optional)
        
        Returns:
            Optimized prompt
        """
        # Remove excessive whitespace
        prompt = " ".join(prompt.split())
        
        # Truncate if needed
        if max_length and len(prompt) > max_length:
            prompt = prompt[:max_length] + "..."
            logger.debug(f"Truncated prompt to {max_length} characters")
        
        return prompt
    
    def track_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False
    ):
        """Track API request for cost analysis"""
        self._stats["total_requests"] += 1
        
        if not cached:
            self._stats["total_tokens_input"] += input_tokens
            self._stats["total_tokens_output"] += output_tokens
            
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            self._stats["total_cost"] += cost
            self._stats["requests_by_model"][model] += 1
            self._stats["cost_by_model"][model] += cost
            
            logger.info(
                f"LLM Request: {model} | "
                f"Tokens: {input_tokens}+{output_tokens} | "
                f"Cost: ${cost:.6f}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cost and usage statistics"""
        cache_hit_rate = (
            self._stats["cached_requests"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0.0
        )
        
        return {
            **self._stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._cache),
            "estimated_savings": self._stats["cached_requests"] * 0.01,  # Rough estimate
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            "total_requests": 0,
            "cached_requests": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "total_cost": 0.0,
            "requests_by_model": defaultdict(int),
            "cost_by_model": defaultdict(float),
        }


def cached_llm_call(cache_ttl: int = 3600):
    """Decorator to cache LLM function calls"""
    def decorator(func):
        optimizer = LLMCostOptimizer(cache_ttl=cache_ttl)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key_data = json.dumps({"args": str(args), "kwargs": kwargs}, sort_keys=True)
            cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()
            
            # Check cache
            cached = optimizer.get_cached_response("", model=cache_key)
            if cached is not None:
                return cached
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            optimizer.cache_response("", result, model=cache_key)
            
            return result
        
        return wrapper
    return decorator
