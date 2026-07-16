"""Code generator - produces ORM/model code from database table metadata."""

import logging
import os
import re
from typing import Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Jinja2 template directory (code_templates/ subdirectory within the templates package)
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "code_templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


class TypeMapper:
    """Maps database column types to target language types."""

    # Mapping: (db_type_pattern, target) -> language type
    _MAPPINGS: dict[tuple[str, str], str] = {
        # Integer types
        ("TINYINT", "python"): "int",
        ("TINYINT", "typescript"): "number",
        ("TINYINT", "go"): "int8",
        ("TINYINT", "java"): "Byte",
        ("SMALLINT", "python"): "int",
        ("SMALLINT", "typescript"): "number",
        ("SMALLINT", "go"): "int16",
        ("SMALLINT", "java"): "Short",
        ("MEDIUMINT", "python"): "int",
        ("MEDIUMINT", "typescript"): "number",
        ("MEDIUMINT", "go"): "int32",
        ("MEDIUMINT", "java"): "Integer",
        ("INTEGER", "python"): "int",
        ("INTEGER", "typescript"): "number",
        ("INTEGER", "go"): "int64",
        ("INTEGER", "java"): "Long",
        ("INT", "python"): "int",
        ("INT", "typescript"): "number",
        ("INT", "go"): "int32",
        ("INT", "java"): "Integer",
        ("BIGINT", "python"): "int",
        ("BIGINT", "typescript"): "number",
        ("BIGINT", "go"): "int64",
        ("BIGINT", "java"): "Long",

        # Float types
        ("FLOAT", "python"): "float",
        ("FLOAT", "typescript"): "number",
        ("FLOAT", "go"): "float32",
        ("FLOAT", "java"): "Float",
        ("DOUBLE", "python"): "float",
        ("DOUBLE", "typescript"): "number",
        ("DOUBLE", "go"): "float64",
        ("DOUBLE", "java"): "Double",
        ("REAL", "python"): "float",
        ("REAL", "typescript"): "number",
        ("REAL", "go"): "float64",
        ("REAL", "java"): "Double",
        ("DECIMAL", "python"): "Decimal",
        ("DECIMAL", "typescript"): "number",
        ("DECIMAL", "go"): "float64",
        ("DECIMAL", "java"): "BigDecimal",
        ("NUMERIC", "python"): "Decimal",
        ("NUMERIC", "typescript"): "number",
        ("NUMERIC", "go"): "float64",
        ("NUMERIC", "java"): "BigDecimal",

        # String types
        ("CHAR", "python"): "str",
        ("CHAR", "typescript"): "string",
        ("CHAR", "go"): "string",
        ("CHAR", "java"): "String",
        ("VARCHAR", "python"): "str",
        ("VARCHAR", "typescript"): "string",
        ("VARCHAR", "go"): "string",
        ("VARCHAR", "java"): "String",
        ("TEXT", "python"): "str",
        ("TEXT", "typescript"): "string",
        ("TEXT", "go"): "string",
        ("TEXT", "java"): "String",
        ("TINYTEXT", "python"): "str",
        ("TINYTEXT", "typescript"): "string",
        ("TINYTEXT", "go"): "string",
        ("TINYTEXT", "java"): "String",
        ("MEDIUMTEXT", "python"): "str",
        ("MEDIUMTEXT", "typescript"): "string",
        ("MEDIUMTEXT", "go"): "string",
        ("MEDIUMTEXT", "java"): "String",
        ("LONGTEXT", "python"): "str",
        ("LONGTEXT", "typescript"): "string",
        ("LONGTEXT", "go"): "string",
        ("LONGTEXT", "java"): "String",
        ("CLOB", "python"): "str",
        ("CLOB", "typescript"): "string",
        ("CLOB", "go"): "string",
        ("CLOB", "java"): "String",

        # Boolean
        ("BOOLEAN", "python"): "bool",
        ("BOOLEAN", "typescript"): "boolean",
        ("BOOLEAN", "go"): "bool",
        ("BOOLEAN", "java"): "Boolean",
        ("BOOL", "python"): "bool",
        ("BOOL", "typescript"): "boolean",
        ("BOOL", "go"): "bool",
        ("BOOL", "java"): "Boolean",
        ("BIT", "python"): "bool",
        ("BIT", "typescript"): "boolean",
        ("BIT", "go"): "bool",
        ("BIT", "java"): "Boolean",

        # Date/Time
        ("DATE", "python"): "date",
        ("DATE", "typescript"): "Date",
        ("DATE", "go"): "time.Time",
        ("DATE", "java"): "LocalDate",
        ("DATETIME", "python"): "datetime",
        ("DATETIME", "typescript"): "Date",
        ("DATETIME", "go"): "time.Time",
        ("DATETIME", "java"): "LocalDateTime",
        ("TIMESTAMP", "python"): "datetime",
        ("TIMESTAMP", "typescript"): "Date",
        ("TIMESTAMP", "go"): "time.Time",
        ("TIMESTAMP", "java"): "LocalDateTime",
        ("TIME", "python"): "time",
        ("TIME", "typescript"): "string",
        ("TIME", "go"): "time.Time",
        ("TIME", "java"): "LocalTime",
        ("YEAR", "python"): "int",
        ("YEAR", "typescript"): "number",
        ("YEAR", "go"): "int",
        ("YEAR", "java"): "Integer",

        # Binary
        ("BLOB", "python"): "bytes",
        ("BLOB", "typescript"): "Buffer",
        ("BLOB", "go"): "[]byte",
        ("BLOB", "java"): "byte[]",
        ("BINARY", "python"): "bytes",
        ("BINARY", "typescript"): "Buffer",
        ("BINARY", "go"): "[]byte",
        ("BINARY", "java"): "byte[]",
        ("VARBINARY", "python"): "bytes",
        ("VARBINARY", "typescript"): "Buffer",
        ("VARBINARY", "go"): "[]byte",
        ("VARBINARY", "java"): "byte[]",
        ("BYTEA", "python"): "bytes",
        ("BYTEA", "typescript"): "Buffer",
        ("BYTEA", "go"): "[]byte",
        ("BYTEA", "java"): "byte[]",

        # JSON
        ("JSON", "python"): "dict",
        ("JSON", "typescript"): "Record<string, any>",
        ("JSON", "go"): "map[string]interface{}",
        ("JSON", "java"): "Map<String, Object>",
        ("JSONB", "python"): "dict",
        ("JSONB", "typescript"): "Record<string, any>",
        ("JSONB", "go"): "map[string]interface{}",
        ("JSONB", "java"): "Map<String, Object>",

        # UUID
        ("UUID", "python"): "str",
        ("UUID", "typescript"): "string",
        ("UUID", "go"): "string",
        ("UUID", "java"): "UUID",

        # Enum
        ("ENUM", "python"): "str",
        ("ENUM", "typescript"): "string",
        ("ENUM", "go"): "string",
        ("ENUM", "java"): "String",
    }

    # Default fallbacks per target language
    _DEFAULTS = {
        "python": "str",
        "typescript": "string",
        "go": "string",
        "java": "String",
    }

    @classmethod
    def map_type(cls, db_type: str, target: str) -> str:
        """Map a database column type to a target language type.

        Strips length/precision info (e.g., VARCHAR(255) -> VARCHAR) before lookup.

        Args:
            db_type: The database column type string (e.g., "VARCHAR(255)", "INTEGER").
            target: Target language ("python", "typescript", "go", "java").

        Returns:
            The corresponding language type string.
        """
        target = target.lower()

        # Normalize: strip length/precision, take base type
        normalized = db_type.upper().strip()
        # Remove parenthesized parts: VARCHAR(255) -> VARCHAR, DECIMAL(10,2) -> DECIMAL
        base_type = re.sub(r"\(.*?\)", "", normalized).strip()
        # Handle unsigned
        base_type = base_type.replace(" UNSIGNED", "").strip()

        # Try exact match first
        key = (base_type, target)
        if key in cls._MAPPINGS:
            return cls._MAPPINGS[key]

        # Try partial match (e.g., "VARCHAR2" matches "VARCHAR")
        for (pattern, tgt), mapped in cls._MAPPINGS.items():
            if tgt == target and base_type.startswith(pattern):
                return mapped

        return cls._DEFAULTS.get(target, "str")


class CodeGenerator:
    """Generates ORM/model code from database table metadata."""

    @staticmethod
    def _convert_name(name: str, style: str = "snake_case") -> str:
        """Convert a name between naming conventions.

        Args:
            name: The identifier name to convert.
            style: Target style - 'snake_case', 'camelCase', or 'PascalCase'.

        Returns:
            Converted name string.
        """
        if style == "snake_case":
            # PascalCase/camelCase to snake_case
            s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
            s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
            return s2.lower().replace("-", "_").replace(" ", "_")

        # First, convert to snake_case as intermediate
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        parts = s2.lower().replace("-", "_").replace(" ", "_").split("_")
        parts = [p for p in parts if p]

        if style == "camelCase":
            return parts[0] + "".join(p.capitalize() for p in parts[1:])
        elif style == "PascalCase":
            return "".join(p.capitalize() for p in parts)
        else:
            return name

    @staticmethod
    def generate(
        table: dict,
        target: str,
        naming_style: str = "snake_case",
        include_comments: bool = False,
    ) -> str:
        """Generate code for a single table definition.

        Args:
            table: Table metadata dict with keys: name, columns, indexes, foreign_keys.
            target: Target framework/language. One of:
                    'sqlalchemy', 'django', 'pydantic', 'typescript', 'go', 'java'.
            naming_style: Naming convention for generated identifiers:
                          'snake_case', 'camelCase', 'PascalCase'.
            include_comments: Whether to include column comments in generated code.

        Returns:
            Generated code as a string.

        Raises:
            ValueError: If the target is not supported.
        """
        generators = {
            "sqlalchemy": CodeGenerator._gen_sqlalchemy,
            "django": CodeGenerator._gen_django,
            "pydantic": CodeGenerator._gen_pydantic,
            "typescript": CodeGenerator._gen_typescript,
            "go": CodeGenerator._gen_go,
            "java": CodeGenerator._gen_java,
        }

        if target not in generators:
            raise ValueError(
                f"Unsupported target '{target}'. "
                f"Supported: {', '.join(generators.keys())}"
            )

        return generators[target](table, naming_style, include_comments)

    @staticmethod
    def _gen_sqlalchemy(table: dict, naming_style: str, include_comments: bool) -> str:
        """Generate SQLAlchemy 2.0 model class using Jinja2 template."""
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        class_name = CodeGenerator._convert_name(table_name, "PascalCase")

        enriched_columns = []
        has_optional = False
        for col in columns:
            col_type = col["type"].upper()
            nullable = col.get("nullable", True)
            is_pk = col.get("primary_key", False)
            py_type = TypeMapper.map_type(col_type, "python")
            if nullable and not is_pk:
                py_type = f"Optional[{py_type}]"
                has_optional = True

            enriched_columns.append({
                "name": col["name"],
                "py_type": py_type,
                "sa_type": CodeGenerator._sqlalchemy_type(col_type),
                "is_pk": is_pk,
                "nullable": nullable,
                "default": col.get("default"),
                "default_repr": repr(col.get("default")),
                "comment": col.get("comment", ""),
            })

        template = _jinja_env.get_template("sqlalchemy.j2")
        rendered = template.render(
            table_name=table_name,
            class_name=class_name,
            columns=enriched_columns,
            has_optional=has_optional,
            include_comments=include_comments,
        )
        return rendered

    @staticmethod
    def _sqlalchemy_type(db_type: str) -> str:
        """Map DB type to SQLAlchemy column type string."""
        base = re.sub(r"\(.*?\)", "", db_type.upper()).strip().replace(" UNSIGNED", "")
        mapping = {
            "TINYINT": "Integer",
            "SMALLINT": "Integer",
            "MEDIUMINT": "Integer",
            "INTEGER": "Integer",
            "INT": "Integer",
            "BIGINT": "BigInteger",
            "FLOAT": "Float",
            "DOUBLE": "Float",
            "REAL": "Float",
            "DECIMAL": "Numeric",
            "NUMERIC": "Numeric",
            "CHAR": "String",
            "VARCHAR": "String",
            "VARCHAR2": "String",
            "TEXT": "Text",
            "TINYTEXT": "Text",
            "MEDIUMTEXT": "Text",
            "LONGTEXT": "Text",
            "CLOB": "Text",
            "BOOLEAN": "Boolean",
            "BOOL": "Boolean",
            "BIT": "Boolean",
            "DATE": "Date",
            "DATETIME": "DateTime",
            "TIMESTAMP": "DateTime",
            "TIME": "Time",
            "JSON": "JSON",
            "JSONB": "JSON",
        }
        for pattern, sa_type in mapping.items():
            if base.startswith(pattern):
                return sa_type
        return "String"

    @staticmethod
    def _gen_django(table: dict, naming_style: str, include_comments: bool) -> str:
        """Generate Django model class using Jinja2 template."""
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        class_name = CodeGenerator._convert_name(table_name, "PascalCase")

        enriched_columns = []
        for col in columns:
            col_type = col["type"].upper()
            nullable = col.get("nullable", True)
            is_pk = col.get("primary_key", False)
            default = col.get("default")
            comment = col.get("comment", "")

            dj_field = CodeGenerator._django_field_type(col_type)
            kwargs: list[str] = []

            if is_pk:
                kwargs.append("primary_key=True")
            if nullable and not is_pk:
                kwargs.append("null=True")
                kwargs.append("blank=True")
            if default is not None:
                kwargs.append(f"default={repr(default)}")
            if include_comments and comment:
                kwargs.append(f'help_text="{comment}"')

            # Add max_length for CharField
            if "CHAR" in col_type and "max_length" not in col_type:
                length_match = re.search(r"\((\d+)\)", col["type"])
                if length_match:
                    kwargs.insert(0, f"max_length={length_match.group(1)}")
                else:
                    kwargs.insert(0, "max_length=255")

            enriched_columns.append({
                "name": col["name"],
                "dj_field": dj_field,
                "dj_kwargs": ", ".join(kwargs),
            })

        template = _jinja_env.get_template("django.j2")
        return template.render(
            table_name=table_name,
            class_name=class_name,
            columns=enriched_columns,
        )

    @staticmethod
    def _django_field_type(db_type: str) -> str:
        """Map DB type to Django field type."""
        base = re.sub(r"\(.*?\)", "", db_type.upper()).strip().replace(" UNSIGNED", "")
        mapping = {
            "TINYINT": "models.SmallIntegerField",
            "SMALLINT": "models.SmallIntegerField",
            "INTEGER": "models.IntegerField",
            "INT": "models.IntegerField",
            "BIGINT": "models.BigIntegerField",
            "FLOAT": "models.FloatField",
            "DOUBLE": "models.FloatField",
            "DECIMAL": "models.DecimalField",
            "NUMERIC": "models.DecimalField",
            "CHAR": "models.CharField",
            "VARCHAR": "models.CharField",
            "TEXT": "models.TextField",
            "BOOLEAN": "models.BooleanField",
            "BOOL": "models.BooleanField",
            "DATE": "models.DateField",
            "DATETIME": "models.DateTimeField",
            "TIMESTAMP": "models.DateTimeField",
            "TIME": "models.TimeField",
            "JSON": "models.JSONField",
            "JSONB": "models.JSONField",
            "BLOB": "models.BinaryField",
            "BYTEA": "models.BinaryField",
            "UUID": "models.UUIDField",
        }
        for pattern, field in mapping.items():
            if base.startswith(pattern):
                return field
        return "models.CharField"

    @staticmethod
    def _gen_pydantic(table: dict, naming_style: str, include_comments: bool) -> str:
        """Generate Pydantic v2 model class using Jinja2 template."""
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        class_name = CodeGenerator._convert_name(table_name, "PascalCase")

        enriched_columns = []
        for col in columns:
            col_type = col["type"].upper()
            nullable = col.get("nullable", True)
            default = col.get("default")
            comment = col.get("comment", "")

            py_type = TypeMapper.map_type(col_type, "python")
            if nullable:
                py_type = f"Optional[{py_type}]"

            field_args: list[str] = []
            if nullable:
                field_args.append("default=None")
            elif default is not None:
                field_args.append(f"default={repr(default)}")
            else:
                field_args.append("...")

            if include_comments and comment:
                field_args.append(f'description="{comment}"')

            enriched_columns.append({
                "name": col["name"],
                "py_type": py_type,
                "field_args": ", ".join(field_args),
            })

        template = _jinja_env.get_template("pydantic.j2")
        return template.render(
            table_name=table_name,
            class_name=class_name,
            columns=enriched_columns,
        )

    @staticmethod
    def _gen_typescript(table: dict, naming_style: str, include_comments: bool) -> str:
        """Generate TypeScript interface using Jinja2 template."""
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        interface_name = CodeGenerator._convert_name(table_name, "PascalCase")

        enriched_columns = []
        for col in columns:
            col_type = col["type"].upper()
            nullable = col.get("nullable", True)
            enriched_columns.append({
                "name": col["name"],
                "converted_name": CodeGenerator._convert_name(col["name"], naming_style),
                "ts_type": TypeMapper.map_type(col_type, "typescript"),
                "nullable": nullable,
                "comment": col.get("comment", ""),
            })

        template = _jinja_env.get_template("typescript.j2")
        return template.render(
            class_name=interface_name,
            columns=enriched_columns,
            include_comments=include_comments,
        )

    @staticmethod
    def _gen_go(table: dict, naming_style: str, include_comments: bool) -> str:
        """Generate Go struct using Jinja2 template."""
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        struct_name = CodeGenerator._convert_name(table_name, "PascalCase")

        enriched_columns = []
        for col in columns:
            col_type = col["type"].upper()
            nullable = col.get("nullable", True)
            go_type = TypeMapper.map_type(col_type, "go")
            if nullable and go_type not in ("[]byte",):
                go_type = f"*{go_type}"

            enriched_columns.append({
                "name": col["name"],
                "pascal_name": CodeGenerator._convert_name(col["name"], "PascalCase"),
                "go_type": go_type,
                "comment": col.get("comment", ""),
            })

        template = _jinja_env.get_template("go.j2")
        return template.render(
            class_name=struct_name,
            columns=enriched_columns,
            include_comments=include_comments,
        )

    @staticmethod
    def _gen_java(table: dict, naming_style: str, include_comments: bool) -> str:
        """Generate Java entity class with Jakarta Persistence annotations using Jinja2 template."""
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        class_name = CodeGenerator._convert_name(table_name, "PascalCase")

        enriched_columns = []
        for col in columns:
            col_name = col["name"]
            field_name = CodeGenerator._convert_name(col_name, "camelCase")
            pascal_name = CodeGenerator._convert_name(col_name, "PascalCase")
            col_type = col["type"].upper()
            nullable = col.get("nullable", True)
            is_pk = col.get("primary_key", False)
            comment = col.get("comment", "")

            java_type = TypeMapper.map_type(col_type, "java")

            # Build @Column annotation arguments
            col_annotations = [f'name = "{col_name}"']
            if not nullable:
                col_annotations.append("nullable = false")
            length_match = re.search(r"\((\d+)\)", col["type"])
            if length_match and "CHAR" in col_type:
                col_annotations.append(f"length = {length_match.group(1)}")

            enriched_columns.append({
                "name": col_name,
                "field_name": field_name,
                "pascal_name": pascal_name,
                "java_type": java_type,
                "is_pk": is_pk,
                "auto_increment": col.get("auto_increment", False),
                "col_annotations": ", ".join(col_annotations),
                "comment": comment,
            })

        template = _jinja_env.get_template("java.j2")
        return template.render(
            table_name=table_name,
            class_name=class_name,
            columns=enriched_columns,
            include_comments=include_comments,
        )
