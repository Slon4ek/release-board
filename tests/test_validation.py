"""Unit-тесты правил валидации — без БД, только Pydantic-схемы."""

import pytest
from pydantic import ValidationError

from src.schemas import (
    VALID_TRANSITIONS,
    ReleaseCreate,
    ReleaseEnvironment,
    ReleaseStatus,
)


class TestSemVer:
    """Валидация формата версии (Semantic Versioning)."""

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0",
            "0.0.0",
            "10.20.30",
            "1.2.3",
            "0.1.0",
            "1.0.0-beta",
            "1.0.0-beta.1",
            "1.0.0-alpha-beta",
            "1.0.0-0.3.7",
            "1.0.0-x.7.z.92",
            "1.0.0+build.5",
            "1.0.0+20130313144700",
            "1.0.0-rc.1+build.1",
        ],
    )
    def test_valid_semver(self, version: str):
        release = ReleaseCreate(service="api", version=version, environment="prod")
        assert release.version == version

    @pytest.mark.parametrize(
        "version",
        [
            # формат в целом
            "v1.0.0",  # префикс v
            "1.0",  # нет patch
            "1.0.0.0",  # лишний сегмент
            "latest",  # не число
            "1.0.x",  # буква в patch
            " 1.0.0",  # ведущий пробел
            "1.0.0 ",  # хвостовой пробел
            "",  # пусто
            # ведущие нули в major.minor.patch
            "01.0.0",
            "1.00.0",
            "1.0.00",
            # пустые части prerelease
            "1.0.0-",  # пустой prerelease
            "1.0.0-beta..1",  # пустой идентификатор между точками
            "1.0.0-01",  # ведущий ноль в числовом prerelease
            # build metadata
            "1.0.0+",  # пустой build
            # недопустимые символы
            "1.0.0-beta_1",  # подчёркивание
        ],
    )
    def test_invalid_semver(self, version: str):
        with pytest.raises(ValidationError):
            ReleaseCreate(service="api", version=version, environment="prod")


class TestRequiredFields:
    """Проверка обязательных полей."""

    def test_missing_service(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(version="1.0.0", environment="prod")

    def test_missing_version(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(service="api", environment="prod")

    def test_missing_environment(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(service="api", version="1.0.0")

    def test_empty_service(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(service="", version="1.0.0", environment="prod")

    def test_whitespace_service(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(service="   ", version="1.0.0", environment="prod")


class TestEnvironmentEnum:
    """Валидация значений окружения."""

    @pytest.mark.parametrize("env", ["dev", "stage", "prod"])
    def test_valid_environments(self, env: str):
        release = ReleaseCreate(service="api", version="1.0.0", environment=env)
        assert release.environment == ReleaseEnvironment(env)

    @pytest.mark.parametrize(
        "env",
        ["production", "development", "test", "PROD", "", "qa"],
    )
    def test_invalid_environments(self, env: str):
        with pytest.raises(ValidationError):
            ReleaseCreate(service="api", version="1.0.0", environment=env)


class TestStatusTransitions:
    """Проверка машины состояний VALID_TRANSITIONS."""

    def test_planned_can_deploy(self):
        assert ReleaseStatus.DEPLOYED in VALID_TRANSITIONS[ReleaseStatus.PLANNED]

    def test_planned_can_fail(self):
        assert ReleaseStatus.FAILED in VALID_TRANSITIONS[ReleaseStatus.PLANNED]

    def test_deployed_can_rollback(self):
        assert ReleaseStatus.ROLLED_BACK in VALID_TRANSITIONS[ReleaseStatus.DEPLOYED]

    def test_failed_is_terminal(self):
        assert VALID_TRANSITIONS[ReleaseStatus.FAILED] == set()

    def test_rolled_back_is_terminal(self):
        assert VALID_TRANSITIONS[ReleaseStatus.ROLLED_BACK] == set()

    def test_deployed_cannot_redeploy(self):
        assert ReleaseStatus.DEPLOYED not in VALID_TRANSITIONS[ReleaseStatus.DEPLOYED]

    def test_planned_cannot_rollback(self):
        assert ReleaseStatus.ROLLED_BACK not in VALID_TRANSITIONS[ReleaseStatus.PLANNED]
