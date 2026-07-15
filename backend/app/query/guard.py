"""SQL query guard - validates and restricts SQL statements for safety."""

import logging
import re

import sqlparse

logger = logging.getLogger(__name__)

# Keywords that modify data or schema
_WRITE_KEYWORDS = frozenset({
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "LOCK",
    "RENAME",
    "COMMENT",
    "LOAD",
})

# Keywords considered safe for read-only mode
_READ_KEYWORDS = frozenset({
    "SELECT",
    "SHOW",
    "DESCRIBE",
    "DESC",
    "EXPLAIN",
    "WITH",
})


class QueryGuard:
    """Validates SQL statements to enforce read-only or read-write policies.

    Uses sqlparse to strip comments and detect the first meaningful keyword,
    then checks it against allowed/blocked keyword sets.
    """

    def __init__(self, read_only: bool = True) -> None:
        """Initialize the guard.

        Args:
            read_only: When True, only read statements (SELECT, SHOW, etc.)
                       are allowed. Write/DDL statements are blocked.
        """
        self.read_only = read_only

    def is_allowed(self, sql: str) -> bool:
        """Check whether a SQL statement is allowed under the current policy.

        Strips SQL comments, detects the first keyword, and validates it
        against the policy.

        Args:
            sql: The SQL statement to validate.

        Returns:
            True if the statement is allowed, False if blocked.
        """
        if not sql or not sql.strip():
            return False

        # Strip comments using sqlparse
        cleaned = sqlparse.format(sql, strip_comments=True).strip()
        if not cleaned:
            return False

        # Check for multiple statements (semicolon-separated) - block in read-only
        parsed_statements = sqlparse.split(cleaned)
        if self.read_only and len(parsed_statements) > 1:
            # Multiple statements could be an injection attempt
            logger.warning("Multiple statements detected in read-only mode")
            return False

        # Detect the first keyword
        first_keyword = self._get_first_keyword(cleaned)
        if first_keyword is None:
            # Cannot determine keyword - be cautious
            logger.warning("Could not determine first keyword for SQL: %s", cleaned[:100])
            return not self.read_only

        first_keyword_upper = first_keyword.upper()

        if not self.read_only:
            # In read-write mode, everything goes (except obviously harmful patterns)
            return True

        # In read-only mode, check against blocked keywords
        if first_keyword_upper in _WRITE_KEYWORDS:
            logger.info("Blocked write statement: %s", first_keyword_upper)
            return False

        if first_keyword_upper in _READ_KEYWORDS:
            return True

        # Unknown keyword - block in read-only mode for safety
        logger.warning("Unknown keyword '%s' blocked in read-only mode", first_keyword_upper)
        return False

    @staticmethod
    def _get_first_keyword(sql: str) -> str | None:
        """Extract the first keyword from a SQL statement.

        Handles leading parentheses (subqueries) and WITH clauses.

        Args:
            sql: Cleaned SQL string (comments stripped).

        Returns:
            The first keyword as a string, or None if not determinable.
        """
        # Tokenize with sqlparse
        parsed = sqlparse.parse(sql)
        if not parsed:
            return None

        statement = parsed[0]
        for token in statement.tokens:
            # Skip whitespace and newlines
            if token.is_whitespace:
                continue
            # Skip comment tokens (shouldn't be any after strip, but just in case)
            if isinstance(token, sqlparse.sql.Comment):
                continue

            # If it's a keyword token, return its value
            if token.ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DDL,
                               sqlparse.tokens.Keyword.DML):
                return token.value

            # If it's a parenthesized expression (subquery), look inside
            if isinstance(token, sqlparse.sql.Parenthesis):
                return QueryGuard._get_first_keyword(token.value.strip("()"))

            # For Identifier/IdentifierList, get the first real token
            if isinstance(token, (sqlparse.sql.Identifier, sqlparse.sql.IdentifierList)):
                return token.value.split()[0] if token.value.strip() else None

            # Generic fallback: take the first word
            word = token.value.strip().split()[0] if token.value.strip() else None
            return word

        return None
