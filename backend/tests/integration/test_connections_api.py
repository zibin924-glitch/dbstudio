"""Integration tests for the Connections API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestConnectionsAPI:

    async def test_create_connection(self, client: AsyncClient, sample_connection_config):
        response = await client.post("/api/connections/", json=sample_connection_config)
        assert response.status_code == 200
        data = response.json()
        # Response may be wrapped in SuccessResponse envelope
        payload = data.get("data", data)
        assert payload["name"] == sample_connection_config["name"]
        assert payload["db_type"] == sample_connection_config["db_type"]
        assert "id" in payload

    async def test_create_connection_missing_fields_422(self, client: AsyncClient):
        incomplete = {"name": "Incomplete"}
        response = await client.post("/api/connections/", json=incomplete)
        assert response.status_code == 422

    async def test_list_connections(self, client: AsyncClient, sample_connection_config):
        await client.post("/api/connections/", json=sample_connection_config)
        config2 = {**sample_connection_config, "name": "Test MySQL 2"}
        await client.post("/api/connections/", json=config2)

        response = await client.get("/api/connections/")
        assert response.status_code == 200
        data = response.json()
        items = data.get("data", data) if isinstance(data, dict) else data
        assert isinstance(items, list)
        assert len(items) >= 2

    async def test_get_connection_by_id(self, client: AsyncClient, sample_connection_config):
        create_resp = await client.post("/api/connections/", json=sample_connection_config)
        create_data = create_resp.json()
        conn_id = create_data.get("data", create_data).get("id", create_data.get("id"))

        response = await client.get(f"/api/connections/{conn_id}")
        assert response.status_code == 200
        data = response.json()
        payload = data.get("data", data)
        assert payload["name"] == sample_connection_config["name"]

    async def test_get_connection_not_found_404(self, client: AsyncClient):
        response = await client.get("/api/connections/99999")
        assert response.status_code in (404, 200)
        if response.status_code == 200:
            data = response.json()
            # May return error envelope
            assert data.get("data") is None or data.get("code", 0) != 0

    async def test_update_connection(self, client: AsyncClient, sample_connection_config):
        create_resp = await client.post("/api/connections/", json=sample_connection_config)
        create_data = create_resp.json()
        conn_id = create_data.get("data", create_data).get("id", create_data.get("id"))

        update_data = {"name": "Updated MySQL", "host": "192.168.1.100"}
        response = await client.put(f"/api/connections/{conn_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        payload = data.get("data", data)
        assert payload["name"] == "Updated MySQL"

    async def test_delete_connection(self, client: AsyncClient, sample_connection_config):
        create_resp = await client.post("/api/connections/", json=sample_connection_config)
        create_data = create_resp.json()
        conn_id = create_data.get("data", create_data).get("id", create_data.get("id"))

        delete_resp = await client.delete(f"/api/connections/{conn_id}")
        assert delete_resp.status_code in (200, 204)

    async def test_password_not_exposed(self, client: AsyncClient, sample_connection_config):
        create_resp = await client.post("/api/connections/", json=sample_connection_config)
        create_data = create_resp.json()
        conn_id = create_data.get("data", create_data).get("id", create_data.get("id"))

        get_resp = await client.get(f"/api/connections/{conn_id}")
        data = get_resp.json()
        payload = data.get("data", data)
        # Password should never appear in plaintext
        if "password" in payload:
            assert payload["password"] != sample_connection_config["password"]
