"""Проверки версии приложения."""

import re

from release_board import __version__

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_version_is_semver() -> None:
    """Версия должна соответствовать SemVer без префиксов и суффиксов."""
    assert _SEMVER.match(__version__), f"версия {__version__!r} не соответствует SemVer"