import base64
import json
from functools import lru_cache
from typing import Any, Mapping

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)

from src.common.aws_session import get_aws_session
from src.common.config import settings
from src.common.logging_config import logger
from src.database.exceptions import (
    DatabaseConfigurationError,
    DatabaseSecretError,
)


class DatabaseCredentials(BaseModel):
    """Validated PostgreSQL connection information."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        frozen=True,
    )

    username: str = Field(
        min_length=1,
        max_length=128,
    )

    password: SecretStr

    host: str = Field(
        min_length=1,
        max_length=255,
    )

    port: int = Field(
        default=5432,
        ge=1,
        le=65535,
    )

    database: str = Field(
        min_length=1,
        max_length=63,
    )

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """Reject an empty database password."""

        if not value.get_secret_value():
            raise ValueError(
                "Database password cannot be empty."
            )

        return value


def decode_secret_response(
    response: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert a Secrets Manager response into a dictionary."""

    secret_text: str | None = None

    secret_string = response.get("SecretString")

    if isinstance(secret_string, str):
        secret_text = secret_string

    if secret_text is None:
        secret_binary = response.get("SecretBinary")

        if isinstance(secret_binary, str):
            secret_text = base64.b64decode(
                secret_binary
            ).decode("utf-8")

        elif isinstance(
            secret_binary,
            bytes | bytearray,
        ):
            binary_value = bytes(secret_binary)

            try:
                secret_text = binary_value.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                secret_text = base64.b64decode(
                    binary_value
                ).decode("utf-8")

    if not secret_text:
        raise DatabaseConfigurationError(
            "The secret did not contain SecretString "
            "or SecretBinary."
        )

    try:
        payload = json.loads(secret_text)
    except json.JSONDecodeError as exc:
        raise DatabaseConfigurationError(
            "The database secret does not contain "
            "valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise DatabaseConfigurationError(
            "The database secret must contain "
            "a JSON object."
        )

    return payload


def load_database_credentials(
    secret_id: str | None = None,
    secrets_client: Any | None = None,
) -> DatabaseCredentials:
    """Load PostgreSQL credentials from Secrets Manager."""

    resolved_secret_id = (
        settings.aws_rds_secret_id.strip()
        if secret_id is None
        else secret_id.strip()
    )

    if not resolved_secret_id:
        raise DatabaseConfigurationError(
            "AWS_RDS_SECRET_ID is not configured."
        )

    client = (
        secrets_client
        if secrets_client is not None
        else get_aws_session().client(
            "secretsmanager"
        )
    )

    try:
        response = client.get_secret_value(
            SecretId=resolved_secret_id
        )
    except (
        BotoCoreError,
        ClientError,
    ) as exc:
        logger.exception(
            "Failed to retrieve RDS credentials "
            "secret_id=%s",
            resolved_secret_id,
        )

        raise DatabaseSecretError(
            secret_id=resolved_secret_id,
            detail=str(exc),
        ) from exc

    secret_payload = decode_secret_response(
        response
    )

    username = (
        secret_payload.get("username")
        or settings.postgres_user
    )

    password = secret_payload.get("password")

    host = (
        secret_payload.get("host")
        or settings.postgres_host
    )

    port = (
        secret_payload.get("port")
        or settings.postgres_port
    )

    database = (
        secret_payload.get("dbname")
        or secret_payload.get("database")
        or settings.postgres_db
    )

    if not isinstance(password, str):
        password = ""

    try:
        credentials = DatabaseCredentials(
            username=username,
            password=SecretStr(password),
            host=host,
            port=port,
            database=database,
        )
    except ValidationError as exc:
        raise DatabaseConfigurationError(
            str(exc)
        ) from exc

    logger.info(
        "Database credentials loaded "
        "host=%s port=%s database=%s user=%s",
        credentials.host,
        credentials.port,
        credentials.database,
        credentials.username,
    )

    return credentials


@lru_cache
def get_database_credentials() -> DatabaseCredentials:
    """Return cached database credentials."""

    return load_database_credentials()