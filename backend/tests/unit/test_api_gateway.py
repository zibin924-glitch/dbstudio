"""Unit tests for app.api_gateway.gateway — parameter handling and SQL safety."""

import pytest
from app.api_gateway.gateway import ApiGateway


@pytest.mark.unit
class TestExtractParams:
    def test_extract_params(self):
        gw = ApiGateway()
        sql = "SELECT * FROM orders WHERE user_id = :user_id AND status = :status"
        params = gw.extract_params(sql)
        assert "user_id" in params
        assert "status" in params
        assert len(params) == 2

    def test_extract_params_empty(self):
        gw = ApiGateway()
        params = gw.extract_params("SELECT * FROM users")
        assert len(params) == 0


@pytest.mark.unit
class TestValidateParams:
    def test_validate_params_int(self):
        gw = ApiGateway()
        params_def = [{"name": "user_id", "type": "int", "required": True, "default": None}]
        result = gw.validate_params(params_def, {"user_id": "42"})
        assert result["user_id"] == 42

    def test_validate_params_type_error(self):
        gw = ApiGateway()
        params_def = [{"name": "user_id", "type": "int", "required": True, "default": None}]
        with pytest.raises((ValueError, TypeError)):
            gw.validate_params(params_def, {"user_id": "not_a_number"})

    def test_validate_params_required_missing(self):
        gw = ApiGateway()
        params_def = [{"name": "user_id", "type": "int", "required": True, "default": None}]
        with pytest.raises((ValueError, KeyError)):
            gw.validate_params(params_def, {})


@pytest.mark.unit
class TestApplyDefaults:
    def test_apply_default_params(self):
        gw = ApiGateway()
        params_def = [
            {"name": "user_id", "type": "int", "required": True, "default": None},
            {"name": "status", "type": "str", "required": False, "default": "paid"},
            {"name": "limit", "type": "int", "required": False, "default": 100},
        ]
        result = gw.validate_params(params_def, {"user_id": "42"})
        assert result["user_id"] == 42
        assert result["status"] == "paid"
        assert result["limit"] == 100


@pytest.mark.unit
class TestCheckSQLSafety:
    def test_only_select_allowed(self):
        gw = ApiGateway()
        assert gw.is_safe_sql("SELECT * FROM users WHERE id = :id") is True
        assert gw.is_safe_sql("INSERT INTO users (name) VALUES (:name)") is False
        assert gw.is_safe_sql("UPDATE users SET name = :name") is False
        assert gw.is_safe_sql("DELETE FROM users WHERE id = :id") is False
        assert gw.is_safe_sql("DROP TABLE users") is False
        assert gw.is_safe_sql("TRUNCATE TABLE users") is False

    def test_multiple_statements_blocked(self):
        gw = ApiGateway()
        assert gw.is_safe_sql("SELECT * FROM users; DROP TABLE users") is False
        assert gw.is_safe_sql("SELECT 1;\nDROP TABLE users") is False
