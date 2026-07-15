"""DDL converter - converts DDL statements between database dialects."""

import logging
import re

logger = logging.getLogger(__name__)


# Type mapping tables for cross-dialect conversion
# MySQL -> PostgreSQL
MYSQL_TO_PG: dict[str, str] = {
    "TINYINT": "SMALLINT",
    "MEDIUMINT": "INTEGER",
    "INT": "INTEGER",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "FLOAT": "REAL",
    "DOUBLE": "DOUBLE PRECISION",
    "DECIMAL": "NUMERIC",
    "NUMERIC": "NUMERIC",
    "VARCHAR": "VARCHAR",
    "CHAR": "CHAR",
    "TINYTEXT": "TEXT",
    "TEXT": "TEXT",
    "MEDIUMTEXT": "TEXT",
    "LONGTEXT": "TEXT",
    "BLOB": "BYTEA",
    "TINYBLOB": "BYTEA",
    "MEDIUMBLOB": "BYTEA",
    "LONGBLOB": "BYTEA",
    "DATETIME": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "DATE": "DATE",
    "TIME": "TIME",
    "BOOLEAN": "BOOLEAN",
    "BOOL": "BOOLEAN",
    "BIT(1)": "BOOLEAN",
    "JSON": "JSONB",
    "ENUM": "VARCHAR(255)",
    "AUTO_INCREMENT": "",  # Handled via SERIAL type
}

# MySQL -> Oracle
MYSQL_TO_ORACLE: dict[str, str] = {
    "TINYINT": "NUMBER(3)",
    "MEDIUMINT": "NUMBER(7)",
    "INT": "NUMBER(10)",
    "INTEGER": "NUMBER(10)",
    "BIGINT": "NUMBER(19)",
    "FLOAT": "BINARY_FLOAT",
    "DOUBLE": "BINARY_DOUBLE",
    "DECIMAL": "NUMBER",
    "NUMERIC": "NUMBER",
    "VARCHAR": "VARCHAR2",
    "CHAR": "CHAR",
    "TINYTEXT": "CLOB",
    "TEXT": "CLOB",
    "MEDIUMTEXT": "CLOB",
    "LONGTEXT": "CLOB",
    "BLOB": "BLOB",
    "DATETIME": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "DATE": "DATE",
    "TIME": "TIMESTAMP",
    "BOOLEAN": "NUMBER(1)",
    "BOOL": "NUMBER(1)",
    "JSON": "CLOB",
    "ENUM": "VARCHAR2(255)",
}

# PostgreSQL -> MySQL
PG_TO_MYSQL: dict[str, str] = {
    "SERIAL": "INT AUTO_INCREMENT",
    "BIGSERIAL": "BIGINT AUTO_INCREMENT",
    "SMALLSERIAL": "SMALLINT AUTO_INCREMENT",
    "SMALLINT": "SMALLINT",
    "INTEGER": "INT",
    "BIGINT": "BIGINT",
    "REAL": "FLOAT",
    "DOUBLE PRECISION": "DOUBLE",
    "NUMERIC": "DECIMAL",
    "VARCHAR": "VARCHAR",
    "VARCHAR2": "VARCHAR",
    "CHAR": "CHAR",
    "TEXT": "TEXT",
    "BYTEA": "LONGBLOB",
    "TIMESTAMP": "DATETIME",
    "DATE": "DATE",
    "TIME": "TIME",
    "BOOLEAN": "TINYINT(1)",
    "JSONB": "JSON",
    "JSON": "JSON",
    "UUID": "VARCHAR(36)",
}

# PostgreSQL -> Oracle
PG_TO_ORACLE: dict[str, str] = {
    "SERIAL": "NUMBER(10)",
    "BIGSERIAL": "NUMBER(19)",
    "SMALLINT": "NUMBER(5)",
    "INTEGER": "NUMBER(10)",
    "BIGINT": "NUMBER(19)",
    "REAL": "BINARY_FLOAT",
    "DOUBLE PRECISION": "BINARY_DOUBLE",
    "NUMERIC": "NUMBER",
    "VARCHAR": "VARCHAR2",
    "CHAR": "CHAR",
    "TEXT": "CLOB",
    "BYTEA": "BLOB",
    "TIMESTAMP": "TIMESTAMP",
    "DATE": "DATE",
    "TIME": "TIMESTAMP",
    "BOOLEAN": "NUMBER(1)",
    "JSONB": "CLOB",
    "JSON": "CLOB",
    "UUID": "RAW(16)",
}

# Oracle -> MySQL
ORACLE_TO_MYSQL: dict[str, str] = {
    "NUMBER": "DECIMAL",
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "CHAR": "CHAR",
    "NCHAR": "CHAR",
    "CLOB": "LONGTEXT",
    "NCLOB": "LONGTEXT",
    "BLOB": "LONGBLOB",
    "BINARY_FLOAT": "FLOAT",
    "BINARY_DOUBLE": "DOUBLE",
    "DATE": "DATETIME",
    "TIMESTAMP": "DATETIME",
    "RAW": "VARBINARY",
    "LONG RAW": "LONGBLOB",
}

# Oracle -> PostgreSQL
ORACLE_TO_PG: dict[str, str] = {
    "NUMBER": "NUMERIC",
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "CHAR": "CHAR",
    "NCHAR": "CHAR",
    "CLOB": "TEXT",
    "NCLOB": "TEXT",
    "BLOB": "BYTEA",
    "BINARY_FLOAT": "REAL",
    "BINARY_DOUBLE": "DOUBLE PRECISION",
    "DATE": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "RAW": "BYTEA",
    "LONG RAW": "BYTEA",
}

# Conversion direction lookup
_CONVERSION_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("mysql", "postgresql"): MYSQL_TO_PG,
    ("mysql", "oracle"): MYSQL_TO_ORACLE,
    ("postgresql", "mysql"): PG_TO_MYSQL,
    ("postgresql", "oracle"): PG_TO_ORACLE,
    ("oracle", "mysql"): ORACLE_TO_MYSQL,
    ("oracle", "postgresql"): ORACLE_TO_PG,
}


class DDLConverter:
    """Converts DDL statements between MySQL, PostgreSQL, and Oracle dialects.

    Performs type mapping, syntax adjustments, and structural transformations
    to produce valid DDL in the target dialect.
    """

    @staticmethod
    def convert(ddl: str, source: str, target: str) -> str:
        """Convert a DDL statement from one dialect to another.

        Args:
            ddl: The DDL statement to convert (CREATE TABLE ...).
            source: Source database dialect ('mysql', 'postgresql', 'oracle').
            target: Target database dialect ('mysql', 'postgresql', 'oracle').

        Returns:
            Converted DDL string.

        Raises:
            ValueError: If the source/target combination is not supported.
        """
        source = source.lower().strip()
        target = target.lower().strip()

        if source == target:
            return ddl

        type_map = _CONVERSION_MAP.get((source, target))
        if type_map is None:
            raise ValueError(
                f"Unsupported conversion direction: {source} -> {target}. "
                f"Supported: mysql<->postgresql, mysql<->oracle, postgresql<->oracle."
            )

        result = ddl

        # Step 1: Replace backtick quoting with target quoting style
        if source == "mysql":
            # Remove backticks
            result = result.replace("`", "")
        elif source in ("postgresql", "oracle"):
            # Remove double quotes
            result = result.replace('"', "")

        # Step 2: Add target quoting style
        if target == "mysql":
            result = DDLConverter._add_backticks(result)
        elif target == "postgresql":
            result = DDLConverter._add_double_quotes(result)

        # Step 3: Replace data types (longest match first to avoid partial replacements)
        sorted_types = sorted(type_map.keys(), key=len, reverse=True)
        for src_type in sorted_types:
            tgt_type = type_map[src_type]
            # Use word boundary matching
            pattern = r"\b" + re.escape(src_type) + r"\b"
            result = re.sub(pattern, tgt_type, result, flags=re.IGNORECASE)

        # Step 4: Dialect-specific adjustments
        result = DDLConverter._adjust_syntax(result, source, target)

        return result

    @staticmethod
    def _adjust_syntax(ddl: str, source: str, target: str) -> str:
        """Apply dialect-specific syntax adjustments after type conversion."""
        result = ddl

        # MySQL -> PostgreSQL: AUTO_INCREMENT -> use SERIAL
        if source == "mysql" and target == "postgresql":
            # Convert INT AUTO_INCREMENT columns to SERIAL
            result = re.sub(
                r"\bINT\s+AUTO_INCREMENT\b",
                "SERIAL",
                result,
                flags=re.IGNORECASE,
            )
            result = re.sub(
                r"\bBIGINT\s+AUTO_INCREMENT\b",
                "BIGSERIAL",
                result,
                flags=re.IGNORECASE,
            )
            # Remove remaining AUTO_INCREMENT
            result = re.sub(r"\s*AUTO_INCREMENT\b", "", result, flags=re.IGNORECASE)
            # Remove ENGINE=InnoDB
            result = re.sub(r"\s*ENGINE\s*=\s*\w+", "", result, flags=re.IGNORECASE)
            # Remove COMMENT = '...'
            result = re.sub(r"\s*COMMENT\s*=\s*'[^']*'", "", result, flags=re.IGNORECASE)
            # Convert MODIFY COLUMN to ALTER COLUMN
            result = result.replace("MODIFY COLUMN", "ALTER COLUMN")

        # MySQL -> Oracle: AUTO_INCREMENT -> GENERATED ALWAYS AS IDENTITY
        if source == "mysql" and target == "oracle":
            result = re.sub(
                r"\bAUTO_INCREMENT\b",
                "GENERATED ALWAYS AS IDENTITY",
                result,
                flags=re.IGNORECASE,
            )
            result = re.sub(r"\s*ENGINE\s*=\s*\w+", "", result, flags=re.IGNORECASE)

        # PostgreSQL -> MySQL: SERIAL -> INT AUTO_INCREMENT
        if source == "postgresql" and target == "mysql":
            result = re.sub(r"\bSERIAL\b", "INT AUTO_INCREMENT", result, flags=re.IGNORECASE)
            result = re.sub(r"\bBIGSERIAL\b", "BIGINT AUTO_INCREMENT", result, flags=re.IGNORECASE)
            result = re.sub(r"\bSMALLSERIAL\b", "SMALLINT AUTO_INCREMENT", result, flags=re.IGNORECASE)

        # Oracle -> MySQL: GENERATED ALWAYS AS IDENTITY -> AUTO_INCREMENT
        if source == "oracle" and target == "mysql":
            result = re.sub(
                r"\bGENERATED\s+ALWAYS\s+AS\s+IDENTITY\b",
                "AUTO_INCREMENT",
                result,
                flags=re.IGNORECASE,
            )

        # Oracle -> PostgreSQL
        if source == "oracle" and target == "postgresql":
            result = re.sub(
                r"\bGENERATED\s+ALWAYS\s+AS\s+IDENTITY\b",
                "",
                result,
                flags=re.IGNORECASE,
            )

        return result.strip()

    @staticmethod
    def _add_backticks(ddl: str) -> str:
        """Add MySQL-style backtick quoting to table and column names."""
        # This is a simplified approach - quotes identifiers after CREATE TABLE
        # and within column definitions. Full parsing would require a SQL parser.
        # For now, we quote the table name in CREATE TABLE statements.
        result = re.sub(
            r"CREATE\s+TABLE\s+(\w+)",
            lambda m: f"CREATE TABLE `{m.group(1)}`",
            ddl,
            flags=re.IGNORECASE,
        )
        return result

    @staticmethod
    def _add_double_quotes(ddl: str) -> str:
        """Add PostgreSQL-style double-quote quoting to identifiers."""
        result = re.sub(
            r"CREATE\s+TABLE\s+(\w+)",
            lambda m: f'CREATE TABLE "{m.group(1)}"',
            ddl,
            flags=re.IGNORECASE,
        )
        return result
