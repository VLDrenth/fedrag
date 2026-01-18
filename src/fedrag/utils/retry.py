"""Retry utilities with exponential backoff."""

import asyncio
import functools
import logging
import random
from typing import Callable, TypeVar, Any

import aiohttp

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """An error that can be retried."""
    pass


class RateLimitError(RetryableError):
    """Rate limit (429) error."""

    def __init__(self, retry_after: float = 60.0):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")


def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 5.0,
    max_delay: float = 300.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        RetryableError,
    ),
) -> Callable:
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt == max_retries:
                        raise
                    delay = e.retry_after
                    logger.warning(
                        f"Rate limited on {func.__name__}, "
                        f"waiting {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    last_exception = e
                except aiohttp.ClientResponseError as e:
                    # Don't retry on 4xx client errors - these are definitive
                    if 400 <= e.status < 500:
                        raise
                    # Retry on 5xx server errors
                    if attempt == max_retries:
                        raise

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Server error in {func.__name__}: {e}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    last_exception = e
                except retryable_exceptions as e:
                    if attempt == max_retries:
                        raise

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Error in {func.__name__}: {e}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    last_exception = e

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error")

        return wrapper
    return decorator
