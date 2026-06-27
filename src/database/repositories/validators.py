MAX_RESULT_LIMIT = 200


def validate_result_limit(
    limit: int,
    maximum: int = MAX_RESULT_LIMIT,
) -> None:
    """Validate a repository query result limit."""

    if limit < 1 or limit > maximum:
        raise ValueError(
            f"Limit must be between 1 and {maximum}."
        )