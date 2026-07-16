"""Dialect-specific metadata query factories.

Provides a factory function to instantiate the correct dialect class
for a given database type, enabling access to metadata that SQLAlchemy's
Inspector does not expose (stored procedures, triggers, sequences, etc.).
"""

from app.explorer.dialects.mysql import MySQLDialect
from app.explorer.dialects.oracle import OracleDialect
from app.explorer.dialects.postgresql import PostgreSQLDialect

_DIALECT_MAP = {
    "mysql": MySQLDialect,
    "postgresql": PostgreSQLDialect,
    "oracle": OracleDialect,
}


def get_dialect(db_type: str, engine):
    """Return a dialect-specific metadata query instance for the given database type.

    Args:
        db_type: Database type string (e.g. 'mysql', 'postgresql', 'oracle').
        engine: A SQLAlchemy Engine used to execute metadata queries.

    Returns:
        An instance of the matching dialect class (MySQLDialect, PostgreSQLDialect,
        or OracleDialect).

    Raises:
        ValueError: If ``db_type`` is not a recognised/supported database type.
    """
    cls = _DIALECT_MAP.get(db_type)
    if cls is None:
        raise ValueError(f"Unsupported database type: {db_type}")
    return cls(engine)
