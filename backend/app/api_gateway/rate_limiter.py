"""Sliding-window rate limiter for API Gateway endpoints."""

import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory sliding window rate limiter.

    Tracks request timestamps per key and enforces a maximum number
    of requests within a configurable time period.
    """

    def __init__(self, rate: int = 60, period: int = 60) -> None:
        """Initialize the rate limiter.

        Args:
            rate: Maximum number of requests allowed within the period.
            period: Time window in seconds.
        """
        self.rate = rate
        self.period = period
        # {key: [timestamp, timestamp, ...]}
        self._requests: dict[str, list[float]] = {}

    def is_allowed(
        self,
        key: str,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ) -> bool:
        """Check whether a request from the given key is allowed.

        Records the current timestamp if allowed. Cleans up expired
        entries before checking.

        Args:
            key: Identifier for the rate-limit subject (e.g., API path,
                 client IP, or token).
            max_requests: Override the default rate for this call.
                          If None, uses the instance-level ``self.rate``.
            window_seconds: Override the default window for this call.
                            If None, uses the instance-level ``self.period``.

        Returns:
            True if the request is within the rate limit, False if exceeded.
        """
        effective_rate = max_requests if max_requests is not None else self.rate
        effective_period = window_seconds if window_seconds is not None else self.period

        now = time.time()
        self._cleanup(key, now=now, window_seconds=effective_period)

        timestamps = self._requests.get(key, [])

        if len(timestamps) >= effective_rate:
            logger.warning(
                "Rate limit exceeded for key='%s': %d requests in %ds window",
                key,
                len(timestamps),
                effective_period,
            )
            return False

        # Record this request
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key].append(now)
        return True

    def _cleanup(
        self,
        key: str,
        now: float | None = None,
        window_seconds: int | None = None,
    ) -> None:
        """Remove expired timestamps for the given key.

        Args:
            key: The rate-limit subject key.
            now: Current time (defaults to time.time()).
            window_seconds: Override the default period for this cleanup.
                            If None, uses the instance-level ``self.period``.
        """
        if key not in self._requests:
            return

        if now is None:
            now = time.time()

        effective_period = window_seconds if window_seconds is not None else self.period
        cutoff = now - effective_period
        # Keep only timestamps within the window
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff
        ]

        # Remove empty keys to prevent memory leak
        if not self._requests[key]:
            del self._requests[key]

    def get_remaining(self, key: str, max_requests: int | None = None) -> int:
        """Get the number of remaining requests for a key.

        Args:
            key: The rate-limit subject key.
            max_requests: Override the default rate for this call.
                          If None, uses the instance-level ``self.rate``.

        Returns:
            Number of requests still allowed in the current window.
        """
        effective_rate = max_requests if max_requests is not None else self.rate
        now = time.time()
        self._cleanup(key, now=now)
        used = len(self._requests.get(key, []))
        return max(0, effective_rate - used)

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit counters.

        Args:
            key: If provided, reset only this key. If None, reset all.
        """
        if key is not None:
            self._requests.pop(key, None)
        else:
            self._requests.clear()


# Module-level singleton with default settings
rate_limiter = RateLimiter(rate=60, period=60)
