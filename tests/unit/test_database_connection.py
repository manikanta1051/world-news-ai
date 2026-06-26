import asyncio
import base64
import json
from typing import Any

import pytest
from botocore.exceptions import ClientError
from pydantic import SecretStr

from src.common.config import settings
from src.database import (
    DatabaseConfigurationError,
    DatabaseCredentials,
    DatabaseSecretError,
    build_database_url,
    create_database_engine,
    decode_secret_response,
    load_database_credentials,
)


class FakeSecretsClient:
    """Return a predefined Secrets Manager response."""

    def __init__(
        self,
        secret_payload: dict[str, Any],
    ) -> None:
        self.secret_payload = secret_payload
        self.requested_secret_id: str | None = None

    def get_secret_value(
        self,
        SecretId: str,
    ) -> dict[str, str]:
        """Return the fake database secret."""

        self.requested_secret_id = SecretId

        return {
            "SecretString": json.dumps(
                self.secret_payload
            )
        }


class FailingSecretsClient:
    """Simulate a Secrets Manager permission failure."""

    def get_secret_value(
        self,
        SecretId: str,
    ) -> dict[str, str]:
        """Raise a realistic AWS client error."""

        raise ClientError(
            error_response={
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Access denied",
                }
            },
            operation_name="GetSecretValue",
        )


def create_test_credentials() -> DatabaseCredentials:
    """Create fixed database credentials for unit tests."""

    return DatabaseCredentials(
        username="worldnewsadmin",
        password=SecretStr("test-password"),
        host=(
            "test-database."
            "us-east-1.rds.amazonaws.com"
        ),
        port=5432,
        database="world_news",
    )


def test_decode_secret_string() -> None:
    """Confirm that a JSON SecretString is decoded."""

    result = decode_secret_response(
        {
            "SecretString": json.dumps(
                {
                    "username": "secret-user",
                    "password": "secret-password",
                }
            )
        }
    )

    assert result["username"] == "secret-user"
    assert result["password"] == "secret-password"


def test_decode_base64_secret_binary() -> None:
    """Confirm that base64 SecretBinary values are decoded."""

    secret_json = json.dumps(
        {
            "username": "binary-user",
            "password": "binary-password",
        }
    )

    encoded_secret = base64.b64encode(
        secret_json.encode("utf-8")
    ).decode("utf-8")

    result = decode_secret_response(
        {
            "SecretBinary": encoded_secret,
        }
    )

    assert result["username"] == "binary-user"
    assert result["password"] == "binary-password"


def test_credentials_load_from_secret() -> None:
    """Confirm that RDS secret fields become credentials."""

    client = FakeSecretsClient(
        {
            "username": "secret-user",
            "password": "secret-password",
            "host": "secret-host.example.com",
            "port": 5432,
            "dbname": "secret-database",
        }
    )

    credentials = load_database_credentials(
        secret_id="test-secret-id",
        secrets_client=client,
    )

    assert credentials.username == "secret-user"
    assert (
        credentials.password.get_secret_value()
        == "secret-password"
    )
    assert credentials.host == (
        "secret-host.example.com"
    )
    assert credentials.port == 5432
    assert credentials.database == (
        "secret-database"
    )
    assert client.requested_secret_id == (
        "test-secret-id"
    )


def test_secret_uses_environment_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm missing endpoint fields use project settings."""

    monkeypatch.setattr(
        settings,
        "postgres_host",
        "configured-host.example.com",
    )
    monkeypatch.setattr(
        settings,
        "postgres_port",
        5432,
    )
    monkeypatch.setattr(
        settings,
        "postgres_db",
        "world_news",
    )

    client = FakeSecretsClient(
        {
            "username": "secret-user",
            "password": "secret-password",
        }
    )

    credentials = load_database_credentials(
        secret_id="test-secret-id",
        secrets_client=client,
    )

    assert credentials.host == (
        "configured-host.example.com"
    )
    assert credentials.port == 5432
    assert credentials.database == "world_news"


def test_missing_secret_id_is_rejected() -> None:
    """Confirm that an empty Secrets Manager ID fails."""

    with pytest.raises(
        DatabaseConfigurationError,
        match="AWS_RDS_SECRET_ID",
    ):
        load_database_credentials(
            secret_id="",
        )


def test_secrets_manager_error_is_converted() -> None:
    """Confirm AWS failures use a project exception."""

    with pytest.raises(
        DatabaseSecretError
    ) as error:
        load_database_credentials(
            secret_id="test-secret-id",
            secrets_client=FailingSecretsClient(),
        )

    assert error.value.secret_id == (
        "test-secret-id"
    )


def test_database_url_and_engine_creation() -> None:
    """Confirm AsyncPG URL and engine creation."""

    credentials = create_test_credentials()

    database_url = build_database_url(
        credentials
    )

    assert database_url.drivername == (
        "postgresql+asyncpg"
    )
    assert database_url.username == (
        "worldnewsadmin"
    )
    assert database_url.host == (
        "test-database."
        "us-east-1.rds.amazonaws.com"
    )
    assert database_url.port == 5432
    assert database_url.database == "world_news"

    safe_url = database_url.render_as_string(
        hide_password=True
    )

    assert "test-password" not in safe_url
    assert "***" in safe_url

    engine = create_database_engine(
        credentials
    )

    assert engine.url.drivername == (
        "postgresql+asyncpg"
    )
    assert engine.url.database == "world_news"

    asyncio.run(engine.dispose())