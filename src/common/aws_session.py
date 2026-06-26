from functools import lru_cache

import boto3
from boto3.session import Session

from src.common.config import settings


@lru_cache
def get_aws_session() -> Session:
    """Create the shared Boto3 session used by AWS services."""

    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        )

    return boto3.Session(
        region_name=settings.aws_region,
    )


def get_aws_account_id() -> str:
    """Return the AWS account ID for the active identity."""

    session = get_aws_session()
    sts_client = session.client("sts")

    response = sts_client.get_caller_identity()

    return str(response["Account"])