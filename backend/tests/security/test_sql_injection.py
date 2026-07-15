"""Security tests for SQL injection prevention in the API Gateway."""

import pytest
from app.api_gateway.gateway import ApiGateway


@pytest.mark.security
class TestSQLInjection:

    def _gw(self):
        return ApiGateway()

    def test_parameterized_query_safe(self):
        gw = self._gw()
        sql = "SELECT * FROM users WHERE id = :user_id AND status = :status"
        assert gw.is_safe_sql(sql) is True

    def test_sql_template_cannot_be_modified(self):
        gw = self._gw()
        # Non-SELECT should fail
        assert gw.is_safe_sql("DROP TABLE users") is False
        assert gw.is_safe_sql("INSERT INTO users VALUES (:name)") is False

    def test_multiple_statements_blocked(self):
        gw = self._gw()
        dangerous = [
            "SELECT * FROM users; DROP TABLE users",
            "SELECT 1; DELETE FROM users WHERE 1=1",
            "SELECT 1;\nALTER TABLE users DROP COLUMN password",
        ]
        for sql in dangerous:
            assert gw.is_safe_sql(sql) is False, f"Should block: {sql!r}"

    def test_union_injection_blocked_by_type_check(self):
        gw = self._gw()
        params_def = [{"name": "user_id", "type": "int", "required": True, "default": None}]

        malicious = {"user_id": "1 UNION SELECT password FROM admin_users"}
        with pytest.raises((ValueError, TypeError)):
            gw.validate_params(params_def, malicious)

        for payload in [
            {"user_id": "1 OR 1=1"},
            {"user_id": "1; DROP TABLE users"},
        ]:
            with pytest.raises((ValueError, TypeError)):
                gw.validate_params(params_def, payload)
