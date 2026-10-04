from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError


class TestLive:
    """GET /live — проверка, что процесс запущен."""

    async def test_live_200(self, client: AsyncClient):
        response = await client.get("/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


class TestReady:
    """GET /ready — проверка готовности, включая соединение с БД."""

    async def test_ready_200(self, client: AsyncClient):
        response = await client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    async def test_ready_503_when_db_unavailable(self, client: AsyncClient):
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("Connection refused")

        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("src.api.health.async_session_maker_null_pool", mock_maker):
            response = await client.get("/ready")

        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}


class TestVersion:
    """GET /version — версия приложения и Git SHA."""

    async def test_version_200(self, client: AsyncClient):
        response = await client.get("/version")
        assert response.status_code == 200
        body = response.json()
        assert "version" in body
        assert "git_sha" in body
        assert isinstance(body["version"], str)
        assert isinstance(body["git_sha"], str)

    async def test_version_with_env_sha(self, client: AsyncClient, monkeypatch):
        monkeypatch.setenv("GIT_SHA", "abcdef1234567890")
        response = await client.get("/version")
        assert response.status_code == 200
        assert response.json()["git_sha"] == "abcdef12"
