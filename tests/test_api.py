import uuid

import pytest


@pytest.mark.asyncio
class TestCreateRelease:
    async def test_create_returns_201(self, client):
        response = await client.post(
            "/releases",
            json={
                "service": "api-gateway",
                "version": "1.0.0",
                "environment": "dev",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["service"] == "api-gateway"
        assert body["version"] == "1.0.0"
        assert body["status"] == "planned"
        assert "id" in body
        assert "created_at" in body

    async def test_create_invalid_semver_returns_422(self, client):
        response = await client.post(
            "/releases",
            json={
                "service": "api-gateway",
                "version": "not-a-version",
                "environment": "dev",
            },
        )
        assert response.status_code == 422

    async def test_create_missing_field_returns_422(self, client):
        response = await client.post(
            "/releases",
            json={
                "version": "1.0.0",
                "environment": "dev",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestGetRelease:
    async def test_get_existing_returns_200(self, client):
        create = await client.post(
            "/releases",
            json={
                "service": "billing",
                "version": "2.1.0",
                "environment": "prod",
            },
        )
        release_id = create.json()["id"]

        response = await client.get(f"/releases/{release_id}")
        assert response.status_code == 200
        assert response.json()["id"] == release_id

    async def test_get_unknown_uuid_returns_404(self, client):
        response = await client.get(f"/releases/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_get_invalid_uuid_returns_422(self, client):
        response = await client.get("/releases/not-a-uuid")
        assert response.status_code == 422


@pytest.mark.asyncio
class TestFiltering:
    async def test_filter_by_environment(self, client):
        await client.post(
            "/releases",
            json={
                "service": "svc-a",
                "version": "1.0.0",
                "environment": "dev",
            },
        )
        await client.post(
            "/releases",
            json={
                "service": "svc-b",
                "version": "1.0.1",
                "environment": "prod",
            },
        )
        await client.post(
            "/releases",
            json={
                "service": "svc-c",
                "version": "1.0.2",
                "environment": "prod",
            },
        )

        response = await client.get("/releases?environment=prod")
        assert response.status_code == 200
        results = response.json()
        assert all(r["environment"] == "prod" for r in results)
        assert len(results) == 2

    async def test_filter_by_service(self, client):
        await client.post(
            "/releases",
            json={
                "service": "unique-svc",
                "version": "3.0.0",
                "environment": "stage",
            },
        )

        response = await client.get("/releases?service=unique-svc")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["service"] == "unique-svc"

    async def test_filter_by_status(self, client):
        create = await client.post(
            "/releases",
            json={
                "service": "svc-status",
                "version": "1.0.0",
                "environment": "dev",
            },
        )
        release_id = create.json()["id"]

        await client.patch(f"/releases/{release_id}/status", json={"status": "deployed"})

        response = await client.get("/releases?status=deployed")
        assert response.status_code == 200
        results = response.json()
        assert all(r["status"] == "deployed" for r in results)


@pytest.mark.asyncio
class TestUpdateRelease:
    async def test_update_status_returns_200(self, client):
        create = await client.post(
            "/releases",
            json={
                "service": "svc-update",
                "version": "1.0.0",
                "environment": "dev",
            },
        )
        release_id = create.json()["id"]

        response = await client.patch(
            f"/releases/{release_id}/status",
            json={
                "status": "deployed",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "deployed"

    async def test_update_unknown_uuid_returns_404(self, client):
        response = await client.patch(f"/releases/{uuid.uuid4()}/status", json={"status": "deployed"})
        assert response.status_code == 404

    async def test_invalid_transition_returns_409(self, client):
        create = await client.post(
            "/releases",
            json={"service": "svc-trans", "version": "1.0.0", "environment": "dev"},
        )
        release_id = create.json()["id"]

        response = await client.patch(
            f"/releases/{release_id}/status",
            json={"status": "rolled_back"},
        )
        assert response.status_code == 409
        body = response.json()
        assert "Cannot transition" in body["detail"]
        assert "planned" in body["detail"]
        assert "rolled_back" in body["detail"]
