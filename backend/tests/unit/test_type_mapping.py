"""Unit tests for app.generator.code_generator.TypeMapper — type mapping."""

import pytest
from app.generator.code_generator import TypeMapper


@pytest.mark.unit
class TestTypeMapping:

    def _map(self, db_type, target):
        mapper = TypeMapper()
        return mapper.map_type(db_type, target)

    # INTEGER
    def test_integer_python(self):
        assert "int" in self._map("INTEGER", "python").lower() or "Integer" in self._map("INTEGER", "python")

    def test_integer_typescript(self):
        assert self._map("INTEGER", "typescript") == "number"

    def test_integer_go(self):
        assert "int" in self._map("INTEGER", "go").lower()

    def test_integer_java(self):
        r = self._map("INTEGER", "java")
        assert "Integer" in r or "Long" in r or "int" in r

    # VARCHAR
    def test_varchar_python(self):
        assert "str" in self._map("VARCHAR(50)", "python").lower() or "String" in self._map("VARCHAR(50)", "python")

    def test_varchar_typescript(self):
        assert self._map("VARCHAR(100)", "typescript") == "string"

    def test_varchar_go(self):
        assert self._map("VARCHAR(255)", "go") == "string"

    def test_varchar_java(self):
        assert "String" in self._map("VARCHAR(50)", "java")

    # DATETIME
    def test_datetime_python(self):
        assert "datetime" in self._map("DATETIME", "python").lower()

    def test_datetime_typescript(self):
        r = self._map("DATETIME", "typescript")
        assert r in ("Date", "string", "Date | string")

    def test_datetime_go(self):
        assert "time" in self._map("DATETIME", "go").lower()

    def test_datetime_java(self):
        r = self._map("DATETIME", "java")
        assert "Date" in r or "Time" in r or "Local" in r

    # DECIMAL
    def test_decimal_python(self):
        r = self._map("DECIMAL(10,2)", "python")
        assert "Decimal" in r or "Float" in r or "float" in r or "Numeric" in r

    def test_decimal_typescript(self):
        assert self._map("DECIMAL(10,2)", "typescript") == "number"

    def test_decimal_go(self):
        r = self._map("DECIMAL(10,2)", "go")
        assert "float" in r.lower()

    def test_decimal_java(self):
        r = self._map("DECIMAL(10,2)", "java")
        assert "Decimal" in r or "Double" in r or "BigDecimal" in r

    # BOOLEAN
    def test_boolean_python(self):
        assert "bool" in self._map("BOOLEAN", "python").lower()

    def test_boolean_typescript(self):
        assert self._map("BOOLEAN", "typescript") == "boolean"

    def test_boolean_go(self):
        assert self._map("BOOLEAN", "go") == "bool"

    def test_boolean_java(self):
        assert "Boolean" in self._map("BOOLEAN", "java") or "boolean" in self._map("BOOLEAN", "java")

    # TEXT
    def test_text_python(self):
        assert "str" in self._map("TEXT", "python").lower() or "Text" in self._map("TEXT", "python")

    def test_text_typescript(self):
        assert self._map("TEXT", "typescript") == "string"

    def test_text_go(self):
        assert self._map("TEXT", "go") == "string"

    def test_text_java(self):
        assert "String" in self._map("TEXT", "java")
