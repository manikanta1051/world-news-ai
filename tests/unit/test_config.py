import pytest
from pydantic import ValidationError

from src.common.config import Settings, settings


def test_local_settings_load_successfully() -> None:
    """Confirm that settings are loaded from the local environment."""

    assert settings.app_name == "World News AI"
    assert settings.app_env == "development"
    assert isinstance(settings.app_debug, bool)
    assert isinstance(settings.postgres_port, int)
    assert isinstance(settings.redis_port, int)


def test_testing_environment_is_valid() -> None:
    """Confirm that testing is an accepted environment."""

    test_settings = Settings(
        app_env="testing",
        app_debug=False,
        _env_file=None,
    )

    assert test_settings.app_env == "testing"
    assert test_settings.app_debug is False


def test_invalid_environment_is_rejected() -> None:
    """Confirm that unsupported environment names are rejected."""

    with pytest.raises(ValidationError):
        Settings(
            app_env="staging",
            _env_file=None,
        )


def test_invalid_postgres_port_is_rejected() -> None:
    """Confirm that an invalid PostgreSQL port is rejected."""

    with pytest.raises(ValidationError):
        Settings(
            postgres_port=70000,
            _env_file=None,
        )


def test_invalid_redis_port_is_rejected() -> None:
    """Confirm that an invalid Redis port is rejected."""

    with pytest.raises(ValidationError):
        Settings(
            redis_port=0,
            _env_file=None,
        )