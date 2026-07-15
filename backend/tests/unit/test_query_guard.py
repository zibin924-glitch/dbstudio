"""Unit tests for app.query.guard — SQL read-only guard."""

import pytest
from app.query.guard import QueryGuard


@pytest.mark.unit
class TestQueryGuard:
    """Tests for the SQL read-only guard."""

    def _guard(self, read_only=True):
        return QueryGuard(read_only=read_only)

    def test_select_allowed(self):
        assert self._guard().is_allowed("SELECT * FROM users") is True

    def test_insert_blocked(self):
        assert self._guard().is_allowed("INSERT INTO users (name) VALUES ('bob')") is False

    def test_update_blocked(self):
        assert self._guard().is_allowed("UPDATE users SET name = 'alice' WHERE id = 1") is False

    def test_delete_blocked(self):
        assert self._guard().is_allowed("DELETE FROM users WHERE id = 1") is False

    def test_drop_blocked(self):
        assert self._guard().is_allowed("DROP TABLE users") is False

    def test_alter_blocked(self):
        assert self._guard().is_allowed("ALTER TABLE users ADD COLUMN age INT") is False

    def test_truncate_blocked(self):
        assert self._guard().is_allowed("TRUNCATE TABLE users") is False

    def test_case_insensitive(self):
        g = self._guard()
        for stmt in [
            "insert INTO users VALUES (1)",
            "INSERT into users VALUES (1)",
            "update users set name='x'",
            "UPDATE users SET name='x'",
            "delete from users",
            "DELETE FROM users",
        ]:
            assert g.is_allowed(stmt) is False, f"Should block: {stmt}"

        for stmt in [
            "select * from users",
            "SELECT * FROM users",
            "Select * From users",
        ]:
            assert g.is_allowed(stmt) is True, f"Should allow: {stmt}"

    def test_comment_bypass_prevention(self):
        g = self._guard()
        sneaky = [
            "-- this looks safe\nDROP TABLE users",
            "/* comment */ DELETE FROM users",
            "-- comment\nINSERT INTO users VALUES (1)",
        ]
        for sql in sneaky:
            assert g.is_allowed(sql) is False, f"Should block: {sql!r}"

    def test_non_read_only_mode(self):
        g = self._guard(read_only=False)
        assert g.is_allowed("INSERT INTO users (name) VALUES ('bob')") is True
        assert g.is_allowed("UPDATE users SET name = 'alice'") is True
        assert g.is_allowed("DELETE FROM users") is True
