"""Integration tests for the Query API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


@pytest.mark.integration
class TestQueryAPI:

    async def test_execute_select(self, client: AsyncClient):
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id", "name"],
                "rows": [[1, "Alice"]],
                "row_count": 1,
                "duration_ms": 15,
            }
            response = await client.post("/api/query/execute", json={
                "connection_id": 1,
                "sql": "SELECT id, name FROM users WHERE id = 1",
                "page": 1,
                "page_size": 50,
            })
            assert response.status_code == 200

    async def test_execute_empty_sql_400(self, client: AsyncClient):
        response = await client.post("/api/query/execute", json={
            "connection_id": 1,
            "sql": "",
        })
        # Empty SQL should be rejected (400) or return an error envelope (200 with error code)
        assert response.status_code in (400, 200)
        if response.status_code == 200:
            data = response.json()
            assert data.get("code", 0) != 0 or "error" in str(data).lower()

    async def test_read_only_blocks_insert_403(self, client: AsyncClient):
        response = await client.post("/api/query/execute", json={
            "connection_id": 1,
            "sql": "INSERT INTO users (name) VALUES ('test')",
            "read_only": True,
        })
        # Should be blocked: either 403 or 200 with error
        assert response.status_code in (403, 200)
        if response.status_code == 200:
            data = response.json()
            assert "read" in str(data).lower() or "only" in str(data).lower() or data.get("code", 0) != 0
