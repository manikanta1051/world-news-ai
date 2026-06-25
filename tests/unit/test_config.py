import pytest
from pydantic import ValidationError

from src.common.config import Settings, settings


def test_local_settings_load_successfully() -> None:
    """Confirm that settings load from the local environment."""

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
    """Confirm that unsupported environment names fail."""

    with pytest.raises(ValidationError):
        Settings(
            app_env="staging",
            _env_file=None,
        )


def test_invalid_postgres_port_is_rejected() -> None:
    """Confirm that an invalid PostgreSQL port fails."""

    with pytest.raises(ValidationError):
        Settings(
            postgres_port=70000,
            _env_file=None,
        )


def test_invalid_redis_port_is_rejected() -> None:
    """Confirm that an invalid Redis port fails."""

    with pytest.raises(ValidationError):
        Settings(
            redis_port=0,
            _env_file=None,
        )


def test_http_configuration_loads_successfully() -> None:
    """Confirm that HTTP configuration uses valid values."""

    assert settings.http_timeout_seconds > 0
    assert settings.http_max_connections >= 1
    assert (
        settings.http_max_keepalive_connections
        <= settings.http_max_connections
    )
    assert settings.http_retry_attempts >= 1
    assert (
        settings.http_retry_min_wait_seconds
        <= settings.http_retry_max_wait_seconds
    )
    assert settings.http_user_agent


def test_keepalive_connections_cannot_exceed_total() -> None:
    """Confirm that HTTP connection limits are consistent."""

    with pytest.raises(ValidationError):
        Settings(
            http_max_connections=5,
            http_max_keepalive_connections=6,
            _env_file=None,
        )


def test_retry_minimum_wait_cannot_exceed_maximum() -> None:
    """Confirm that retry waiting values are consistent."""

    with pytest.raises(ValidationError):
        Settings(
            http_retry_min_wait_seconds=10,
            http_retry_max_wait_seconds=2,
            _env_file=None,
        )