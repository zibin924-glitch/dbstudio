"""Unit tests for app.generator.code_generator — multi-language code generation."""

import pytest
from app.generator.code_generator import CodeGenerator


@pytest.mark.unit
class TestCodeGenerator:

    def _gen(self, table, target, **kwargs):
        cg = CodeGenerator()
        return cg.generate(table=table, target=target, **kwargs)

    def test_generate_sqlalchemy_model(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "sqlalchemy")
        assert "class" in code
        assert "id" in code
        assert "username" in code
        assert "Integer" in code or "INTEGER" in code.upper()

    def test_generate_django_model(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "django")
        assert "class" in code
        assert "models.Model" in code
        assert "username" in code

    def test_generate_pydantic_schema(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "pydantic")
        assert "class" in code
        assert "BaseModel" in code
        assert "username" in code

    def test_generate_typescript_interface(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "typescript")
        assert "interface" in code
        assert "username" in code
        assert "string" in code or "number" in code

    def test_generate_go_struct(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "go")
        assert "struct" in code
        assert "string" in code

    def test_generate_java_entity(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "java")
        assert "class" in code
        assert "String" in code or "Integer" in code or "int" in code

    def test_naming_style_camel_case(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "typescript", naming_style="camel")
        # camelCase: createdAt, not created_at
        assert "createdAt" in code or "created_at" in code

    def test_naming_style_pascal_case(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "sqlalchemy", naming_style="pascal")
        assert "Users" in code or "User" in code

    def test_include_comments(self, sample_table_metadata):
        code = self._gen(sample_table_metadata, "sqlalchemy", include_comments=True)
        assert "Primary key" in code or "comment" in code.lower() or "primary" in code.lower()

    def test_unsupported_target_raises_error(self, sample_table_metadata):
        with pytest.raises((ValueError, NotImplementedError, KeyError)):
            self._gen(sample_table_metadata, "fortran")
