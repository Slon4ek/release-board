import uuid

import pytest


@pytest.mark.asyncio
class TestDeleteRelease:
    async def test_delete_returns_204(self, client):
        create = await client.post(
            "/releases",
            json={"service": "svc-del", "version": "1.0.0", "environment": "dev"},
        )
        release_id = create.json()["id"]

        response = await client.delete(f"/releases/{release_id}")
        assert response.status_code == 204
        assert response.content == b""

    async def test_delete_actually_removes(self, client):
        create = await client.post(
            "/releases",
            json={"service": "svc-del-2", "version": "1.0.0", "environment": "dev"},
        )
        release_id = create.json()["id"]

        await client.delete(f"/releases/{release_id}")
        response = await client.get(f"/releases/{release_id}")
        assert response.status_code == 404

    async def test_delete_unknown_uuid_returns_404(self, client):
        response = await client.delete(f"/releases/{uuid.uuid4()}")
        assert response.status_code == 404
