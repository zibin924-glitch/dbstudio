"""Unit tests for app.generator.ddl_generator — DDL SQL generation."""

import pytest
from app.generator.ddl_generator import DDLGenerator


@pytest.mark.unit
class TestDDLGenerator:

    def _gen(self, table, include_indexes=True, include_foreign_keys=True):
        g = DDLGenerator()
        return g.generate_create_table(
            table,
            include_indexes=include_indexes,
            include_foreign_keys=include_foreign_keys,
        )

    def test_generate_create_table(self, sample_table_metadata):
        ddl = self._gen(sample_table_metadata)
        ddl_upper = ddl.upper()
        assert "CREATE TABLE" in ddl_upper
        assert "INTEGER" in ddl_upper
        assert "PRIMARY KEY" in ddl_upper

    def test_generate_with_indexes(self, sample_table_metadata):
        ddl = self._gen(sample_table_metadata, include_indexes=True)
        ddl_upper = ddl.upper()
        assert "INDEX" in ddl_upper or "UNIQUE" in ddl_upper

    def test_generate_without_indexes(self, sample_table_metadata):
        ddl = self._gen(sample_table_metadata, include_indexes=False)
        ddl_lower = ddl.lower()
        assert "uk_username" not in ddl_lower
        assert "idx_email" not in ddl_lower

    def test_generate_with_foreign_keys(self, sample_table_with_fk):
        ddl = self._gen(sample_table_with_fk)
        ddl_upper = ddl.upper()
        assert "FOREIGN KEY" in ddl_upper or "REFERENCES" in ddl_upper
        assert "users" in ddl.lower()

    def test_generate_schema(self, sample_table_metadata, sample_table_with_fk):
        g = DDLGenerator()
        ddl = g.generate_schema([sample_table_metadata, sample_table_with_fk])
        ddl_upper = ddl.upper()
        assert ddl_upper.count("CREATE TABLE") >= 2
