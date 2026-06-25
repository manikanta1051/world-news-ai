# Step 2 — Centralized Application Configuration

## Objective

Create one centralized configuration system for the World News AI project.

The configuration system loads application settings from the local `.env`
file and validates them before other project components use them.

## Work Completed

- Installed Pydantic Settings.
- Created the local `.env` file from `.env.example`.
- Created `src/common/config.py`.
- Added application settings.
- Added news-source settings.
- Added Groq configuration.
- Added PostgreSQL configuration.
- Added Kafka configuration.
- Added Redis configuration.
- Added Elasticsearch configuration.
- Added validation for environment names.
- Added validation for PostgreSQL and Redis ports.
- Created automated configuration tests.
- Updated `requirements.txt`.
- Verified the complete configuration system.

## Files Created

```text
src/common/config.py
tests/unit/test_config.py
docs/step-02-configuration.md
