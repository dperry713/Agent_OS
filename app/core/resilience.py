import time
import asyncio
from enum import Enum
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

import asyncio
import time
from typing import Callable, Any, Optional
import valkey.asyncio as valkey
from app.core.config import settings
from app.core.exceptions import RateLimitExceeded
from app.core.logging import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Distributed Rate Limiter using Valkey/Redis."""
    
    def __init__(self):
        self.valkey_url = settings.VALKEY_URL

    async def check_rate_limit(self, tenant_id: str, limit: int = 100, window: int = 60):
        """
        Enforces a sliding window rate limit.
        Default: 100 requests per 60 seconds.
        """
        client = valkey.from_url(self.valkey_url)
        now = time.time()
        key = f"rate_limit:{tenant_id}"
        
        try:
            # Use a sorted set for sliding window
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window + 1)
            _, _, count, _ = await pipe.execute()
            
            if count > limit:
                logger.warning("rate_limit_exceeded", tenant_id=tenant_id, count=count)
                raise RateLimitExceeded(f"Rate limit exceeded: {limit} requests per {window}s")
        finally:
            await client.close()

class CircuitBreaker:
    """
    Simple async-compatible Circuit Breaker to prevent cascading failures.
    Transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED (on success) or -> OPEN (on fail).
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit Breaker transitioned to HALF_OPEN")
            else:
                raise RuntimeError("Circuit is OPEN. Call rejected.")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit Breaker transitioned to CLOSED (Recovered)")
        self.state = CircuitState.CLOSED
        self.failures = 0

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit Breaker transitioned to OPEN (Failures: {self.failures})")
