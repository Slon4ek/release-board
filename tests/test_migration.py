import pytest
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import ENUM

from src.database import engine
from src.models import Release


@pytest.mark.asyncio
async def test_releases_table_matches_model():
    async with engine.begin() as conn:

        def check(connection):
            insp = inspect(connection)
            columns = {c["name"]: c for c in insp.get_columns("releases")}
            expected = set(Release.__table__.columns.keys())
            actual = set(columns.keys())
            assert actual == expected, f"Column mismatch: {actual ^ expected}"
            for name in ["service", "version"]:
                assert columns[name]["nullable"] is False
            assert columns["created_at"]["nullable"] is False

        await conn.run_sync(check)


@pytest.mark.asyncio
async def test_releases_column_types():
    async with engine.begin() as conn:

        def check(connection):
            insp = inspect(connection)
            columns = {c["name"]: c for c in insp.get_columns("releases")}
            pk = insp.get_pk_constraint("releases")
            assert pk["constrained_columns"] == ["id"]
            assert str(columns["id"]["type"]) == "UUID"
            assert columns["service"]["type"].length == 255
            assert columns["version"]["type"].length == 50
            env_enum = columns["environment"]["type"]
            assert isinstance(env_enum, ENUM)
            assert env_enum.name == "release_environment"
            status_enum = columns["status"]["type"]
            assert isinstance(status_enum, ENUM)
            assert status_enum.name == "release_status"
            assert columns["created_at"]["type"].timezone
            assert "now" in str(columns["created_at"]["default"])

        await conn.run_sync(check)
