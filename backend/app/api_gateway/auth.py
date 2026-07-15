"""Token-based authentication manager for API Gateway endpoints."""

import logging
import secrets
from typing import Optional

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages API authentication tokens.

    Provides token generation, registration, verification, and revocation.
    Tokens are stored in-memory for simplicity; in production, persist to a
    database or cache.
    """

    def __init__(self) -> None:
        # In-memory token store: {token: api_id}
        self._tokens: dict[str, int] = {}

    def generate_token(self) -> str:
        """Generate a cryptographically secure random 64-character hex token.

        Returns:
            A 64-character hexadecimal string.
        """
        return secrets.token_hex(32)  # 32 bytes = 64 hex chars

    def register_token(self, api_id: int, token: str) -> None:
        """Register a token for a specific API definition.

        Args:
            api_id: The API definition ID this token belongs to.
            token: The token string to register.
        """
        self._tokens[token] = api_id
        logger.info("Registered token for api_id=%d", api_id)

    def verify_token(self, token: str, api_id: int, auth_type: str = "token") -> bool:
        """Verify that a token is valid for the given API definition.

        Args:
            token: The token to verify.
            api_id: The API definition ID to check against.
            auth_type: Authentication type. If 'none', verification always passes.

        Returns:
            True if the token is valid, False otherwise.
        """
        if auth_type == "none":
            return True

        stored_api_id = self._tokens.get(token)
        if stored_api_id is None:
            logger.warning("Token not found: %s...", token[:8] if len(token) > 8 else token)
            return False

        if stored_api_id != api_id:
            logger.warning(
                "Token mismatch: token registered for api_id=%d but request is for api_id=%d",
                stored_api_id,
                api_id,
            )
            return False

        return True

    def revoke_token(self, api_id: int, token: str) -> None:
        """Revoke (remove) a token.

        Args:
            api_id: The API definition ID (for logging purposes).
            token: The token to revoke.
        """
        if token in self._tokens:
            del self._tokens[token]
            logger.info("Revoked token for api_id=%d", api_id)

    def revoke_all_for_api(self, api_id: int) -> int:
        """Revoke all tokens associated with a specific API definition.

        Args:
            api_id: The API definition ID.

        Returns:
            Number of tokens revoked.
        """
        tokens_to_remove = [
            t for t, aid in self._tokens.items() if aid == api_id
        ]
        for t in tokens_to_remove:
            del self._tokens[t]
        return len(tokens_to_remove)

    def get_token_for_api(self, api_id: int) -> Optional[str]:
        """Find the registered token for an API definition.

        Args:
            api_id: The API definition ID.

        Returns:
            The token string, or None if not found.
        """
        for token, stored_api_id in self._tokens.items():
            if stored_api_id == api_id:
                return token
        return None


# Module-level singleton
token_manager = TokenManager()
