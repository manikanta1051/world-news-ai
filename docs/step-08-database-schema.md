# Step 8 — Database Schema, Migrations, and Repositories

## 1. Objective

Step 8 created the structured PostgreSQL database layer for World News AI.

The project now supports:

* News sources
* Normalized news articles
* Article labels and country mappings
* Indian states and Union Territories
* Districts and cities
* Article-to-location relevance mappings
* Application users
* Up to two favorite countries per user
* Favorite Indian states
* Top 10 state-news rankings
* Alembic schema migrations
* Asynchronous repository operations
* Unit tests and live RDS integration testing

---

## 2. Technologies Used

Step 8 uses:

* PostgreSQL
* Amazon RDS
* SQLAlchemy 2.0
* SQLAlchemy AsyncIO
* AsyncPG
* Alembic
* AWS Secrets Manager
* Pydantic
* Pytest
* Pytest AsyncIO

---

## 3. Database Architecture

```text
News Providers
    ├── GDELT
    └── RSS and Atom
          ↓
Article validation and normalization
          ↓
Database repository layer
          ↓
Amazon RDS PostgreSQL
    ├── News sources
    ├── Articles
    ├── Countries
    ├── Indian states
    ├── Districts
    ├── Cities
    ├── User preferences
    └── State Top 10 rankings
```

The database password is not stored in source code.

The application retrieves the password from AWS Secrets Manager and creates an encrypted PostgreSQL connection through SQLAlchemy and AsyncPG.

---

## 4. Database Tables

The initial schema contains 14 application tables.

### 4.1 `news_sources`

Stores news providers and publishers.

Important fields:

* `id`
* `name`
* `source_type`
* `homepage_url`
* `country_code`
* `credibility_score`
* `is_active`
* `extra_metadata`
* `created_at`
* `updated_at`

A unique constraint prevents duplicate combinations of:

```text
name + source_type
```

Examples of source types:

```text
gdelt
rss
atom
api
integration_test
```

---

### 4.2 `articles`

Stores normalized news articles.

Important fields:

* `id`
* `source_id`
* `title`
* `description`
* `content`
* `summary`
* `url`
* `canonical_url`
* `image_url`
* `author`
* `published_at`
* `collected_at`
* `primary_category`
* `sentiment`
* `language_code`
* `ai_processed`
* `content_hash`
* `keywords`
* `share_caption`
* `social_card_data`
* `raw_s3_uri`
* `processed_s3_uri`
* `created_at`
* `updated_at`

The table supports:

* URL-based duplicate detection
* Content-hash duplicate detection
* AI-generated summaries
* Sentiment analysis
* Keyword extraction
* Social-sharing captions
* Social-card metadata
* Raw and processed Amazon S3 paths

---

### 4.3 `article_labels`

Stores dynamic labels assigned to articles.

Important fields:

* `article_id`
* `label`
* `created_at`

Examples:

```text
Breaking News
Politics
Technology
Economy
Sports
World
India
```

The article ID and label together form the primary key.

This prevents the same label from being assigned twice to one article.

---

### 4.4 `article_countries`

Connects articles to countries.

Important fields:

* `article_id`
* `country_code`
* `relevance_score`

The relevance score must remain between:

```text
0 and 1
```

One article can be associated with multiple countries.

Example:

```text
Article: India and United States trade agreement

Country mappings:
IN → 1.0000
US → 0.9500
```

---

### 4.5 `indian_states`

Stores all Indian states and Union Territories.

Important fields:

* `code`
* `short_code`
* `name`
* `region_type`
* `country_code`
* `capital`
* `display_order`
* `is_active`
* `created_at`
* `updated_at`

Supported region types:

```text
state
union_territory
```

The table contains:

```text
28 states
8 Union Territories
36 total regions
```

Examples:

```text
IN-AP → Andhra Pradesh
IN-TG → Telangana
IN-TN → Tamil Nadu
IN-DL → Delhi
IN-JK → Jammu and Kashmir
```

---

### 4.6 `districts`

Stores districts belonging to Indian states or Union Territories.

Important fields:

* `id`
* `state_code`
* `name`
* `slug`
* `is_active`
* `created_at`
* `updated_at`

A district name and slug must be unique within its state.

Example:

```text
State: IN-TG
District: Hyderabad
Slug: hyderabad
```

---

### 4.7 `cities`

Stores cities and major localities.

Important fields:

* `id`
* `state_code`
* `district_id`
* `name`
* `slug`
* `is_active`
* `created_at`
* `updated_at`

A city can be connected to:

* An Indian state
* An optional district

This supports state-, district-, and city-level news filtering.

---

### 4.8 `article_states`

Connects articles to Indian states and Union Territories.

Important fields:

* `article_id`
* `state_code`
* `relevance_score`
* `is_primary`
* `detection_method`

The relevance score must remain between:

```text
0 and 1
```

Example:

```text
Article: Telangana government announces new policy

State: IN-TG
Relevance score: 0.9800
Primary state: true
Detection method: keyword
```

Possible detection methods include:

```text
keyword
named_entity
provider_metadata
manual
ai_model
integration_test
```

---

### 4.9 `article_districts`

Connects articles to Indian districts.

Important fields:

* `article_id`
* `district_id`
* `relevance_score`

This table allows one article to be associated with one or more districts.

---

### 4.10 `article_cities`

Connects articles to cities.

Important fields:

* `article_id`
* `city_id`
* `relevance_score`

This supports city-level news sections in future application versions.

---

### 4.11 `app_users`

Stores World News AI application users.

Important fields:

* `id`
* `email`
* `display_name`
* `is_active`
* `created_at`
* `updated_at`

The email address is unique.

---

### 4.12 `user_favorite_countries`

Stores a user’s favorite countries.

Important fields:

* `user_id`
* `country_code`
* `priority`
* `created_at`

Users can select a maximum of two favorite countries.

Allowed priority values:

```text
1
2
```

Example:

```text
Priority 1 → IN
Priority 2 → US
```

The schema prevents:

* More than two priority positions
* Duplicate country codes for one user
* Duplicate priority positions for one user

---

### 4.13 `user_favorite_states`

Stores Indian states selected by a user.

Important fields:

* `user_id`
* `state_code`
* `created_at`

A user can select one or more favorite Indian states.

Duplicate user-state combinations are prevented.

Example:

```text
User favorite states:
IN-TG
IN-AP
IN-TN
```

---

### 4.14 `state_news_rankings`

Stores the Top 10 news list for every Indian state or Union Territory.

Important fields:

* `id`
* `state_code`
* `article_id`
* `ranking_date`
* `ranking_window`
* `category_filter`
* `rank_position`
* `ranking_score`
* `score_components`
* `generated_at`

Rank positions are restricted to:

```text
1 through 10
```

A state can have separate ranking lists based on:

* Date
* Ranking window
* Category

Example:

```text
State: IN-TG
Date: 2026-06-27
Window: 24h
Category: all
Rank: 1
Score: 95.7500
```

Example score components:

```json
{
  "freshness": 35,
  "state_relevance": 30,
  "source_credibility": 20,
  "engagement": 10,
  "breaking_news_bonus": 5
}
```

---

## 5. Alembic Migration Management

Alembic manages version-controlled database schema changes.

Important files:

```text
alembic.ini
migrations/
├── env.py
├── script.py.mako
└── versions/
```

The migration environment:

1. Loads project configuration.
2. Retrieves RDS credentials from AWS Secrets Manager.
3. Builds the SQLAlchemy AsyncPG URL.
4. Loads SQLAlchemy model metadata.
5. Connects to Amazon RDS.
6. Applies versioned database changes.

The real RDS password is not stored in:

```text
alembic.ini
migration files
Git
source code
```

The password is retrieved only when the migration runs.

---

## 6. Initial Schema Migration

The initial migration creates:

```text
news_sources
articles
article_labels
article_countries
indian_states
districts
cities
article_states
article_districts
article_cities
app_users
user_favorite_countries
user_favorite_states
state_news_rankings
```

Alembic also creates:

```text
alembic_version
```

The `alembic_version` table records the migration currently applied to the database.

Common migration commands:

```powershell
python -m alembic current
```

Displays the current database revision.

```powershell
python -m alembic history
```

Displays the migration history.

```powershell
python -m alembic upgrade head
```

Applies all pending migrations.

```powershell
python -m alembic downgrade -1
```

Reverts the most recent migration.

Downgrades should be used carefully because they can remove tables or data.

---

## 7. India Region Seed Data

The India region catalog is defined in:

```text
src/database/india_seed.py
```

It contains:

```text
28 states
8 Union Territories
36 total regions
```

The seed script is:

```text
scripts/seed_india_regions.py
```

Run it with:

```powershell
python -m scripts.seed_india_regions
```

Expected result:

```text
India region seed completed
Total regions: 36
Active regions: 36
States: 28
Union Territories: 8
```

The seed process uses PostgreSQL upsert behavior.

This means the script can be safely run again.

Existing rows are updated rather than duplicated.

The seed process updates:

* Short code
* Region name
* Region type
* Country code
* Display order
* Active status
* Updated timestamp

---

## 8. Repository Layer

Repository files are stored in:

```text
src/database/repositories/
├── __init__.py
├── articles.py
├── locations.py
├── news_sources.py
├── preferences.py
├── rankings.py
└── validators.py
```

Repositories keep database queries separate from:

* API routes
* Ingestion providers
* Business services
* Dashboard code
* Scheduled jobs

This makes the application easier to test and maintain.

---

## 9. Shared Repository Validation

The shared repository validator is stored in:

```text
src/database/repositories/validators.py
```

It defines:

```python
MAX_RESULT_LIMIT = 200
```

Repository list methods validate that requested limits remain between:

```text
1 and 200
```

This prevents accidentally loading an unlimited number of records.

---

## 10. NewsSourceRepository

The `NewsSourceRepository` handles news providers and publishers.

Supported operations include:

```text
add()
get_by_id()
get_by_name_and_type()
list_active()
get_or_create()
```

### `add()`

Adds a new news source to the current transaction.

### `get_by_id()`

Returns a source using its UUID.

### `get_by_name_and_type()`

Finds a source using its unique business fields.

Example:

```text
Name: Reuters
Source type: rss
```

### `list_active()`

Returns active sources ordered by name.

### `get_or_create()`

Returns an existing source when it already exists.

Otherwise, it creates a new source.

The result includes:

```text
source record
created status
```

Example:

```python
source, created = await repository.get_or_create(...)
```

---

## 11. ArticleRepository

The `ArticleRepository` handles article storage, retrieval, duplicate detection, AI enrichment, and location mappings.

Supported operations include:

```text
add()
get_by_id()
get_by_url()
get_by_content_hash()
list_recent()
list_for_state()
update_ai_results()
upsert_country_link()
upsert_state_link()
```

### `add()`

Adds a normalized article to the current transaction.

### `get_by_url()`

Searches both:

```text
url
canonical_url
```

This helps prevent duplicate article storage.

### `get_by_content_hash()`

Detects articles with duplicate content.

### `list_recent()`

Returns recent articles.

Optional filters include:

* Category
* Language

### `list_for_state()`

Returns articles connected to a specific Indian state.

Articles are ordered by:

1. State relevance score
2. Publication time

### `update_ai_results()`

Stores:

* Summary
* Sentiment
* Keywords
* Share caption
* Social-card metadata
* AI processed status

### `upsert_country_link()`

Creates or updates an article-country relationship.

### `upsert_state_link()`

Creates or updates an article-state relationship.

PostgreSQL `ON CONFLICT DO UPDATE` prevents duplicate mapping records.

---

## 12. IndiaLocationRepository

The `IndiaLocationRepository` provides Indian location data.

Supported operations include:

```text
get_state_by_code()
list_states()
get_district_by_id()
list_districts()
get_city_by_id()
list_cities()
```

### `list_states()`

Can return:

* All active regions
* Only states
* Only Union Territories

Results are ordered by `display_order`.

### `list_districts()`

Returns active districts for a state.

### `list_cities()`

Returns cities for:

* A state
* An optional district

This repository will support the India News navigation interface.

Example flow:

```text
India
    ↓
Select state
    ↓
Select district or city
    ↓
View location-specific news
```

---

## 13. UserPreferenceRepository

The `UserPreferenceRepository` handles application users and personalization.

Supported operations include:

```text
get_user_by_id()
get_user_by_email()
get_or_create_user()
replace_favorite_countries()
list_favorite_countries()
add_favorite_state()
remove_favorite_state()
list_favorite_states()
```

### User creation

Emails are normalized to lowercase before storage.

Example:

```text
User@Example.com
```

becomes:

```text
user@example.com
```

### Favorite countries

Country codes are:

* Trimmed
* Converted to uppercase
* Validated as two-letter codes
* Limited to two selections
* Checked for duplicates

Example input:

```text
" us "
"in"
```

Normalized result:

```text
US
IN
```

### Favorite states

Favorite-state insertion uses:

```text
ON CONFLICT DO NOTHING
```

This allows the application to safely repeat an add request without creating duplicates.

---

## 14. StateRankingRepository

The `StateRankingRepository` manages Top 10 state-news rankings.

Supported operations include:

```text
replace_top_ten()
list_rankings()
list_ranked_articles()
```

The ranking input model is:

```text
StateRankingInput
```

Each ranking input contains:

* Article ID
* Rank position
* Ranking score
* Score components

Ranking validation prevents:

* More than 10 records
* Duplicate article IDs
* Duplicate positions
* Positions outside 1 through 10
* Negative ranking scores
* Ranking gaps
* Rankings that do not begin at position 1

Valid example:

```text
1
2
3
4
5
```

Invalid example:

```text
1
2
4
5
```

The repository replaces a complete ranking snapshot for one:

* State
* Date
* Window
* Category

This keeps each generated Top 10 list consistent.

---

## 15. Transaction Management

Repositories call:

```text
flush()
```

but do not call:

```text
commit()
```

The shared database session manages the transaction.

```text
Successful operation
        ↓
Commit

Failed operation
        ↓
Rollback
```

This allows several repository operations to behave as one unit.

Example:

```text
Create source
    ↓
Create article
    ↓
Add country mapping
    ↓
Add state mapping
    ↓
Commit everything together
```

If one operation fails, the complete transaction can be rolled back.

---

## 16. Unit Testing

Step 8 includes unit tests for:

* ORM table registration
* Required article columns
* Location-mapping tables
* India seed counts
* Unique India region values
* Favorite-country constraints
* Top 10 ranking constraints
* PostgreSQL DDL generation
* News-source repository behavior
* Article repository behavior
* State article queries
* PostgreSQL upserts
* Result-limit validation
* State and Union Territory queries
* District and city filters
* Country-code normalization
* Two-country preference limits
* Duplicate favorite-state handling
* Top 10 ranking validation
* Ranking replacement
* Ranking query ordering

The repository unit tests use mocked asynchronous SQLAlchemy sessions.

They do not require the live RDS database.

Run all unit tests with:

```powershell
python -m pytest tests\unit -v
```

---

## 17. Live Repository Integration Test

The integration-test script is:

```text
scripts/test_repository_integration.py
```

Run it with:

```powershell
python -m scripts.test_repository_integration
```

The test validates the repositories against the real Amazon RDS PostgreSQL database.

It performs the following operations:

1. Retrieves all 36 India regions.
2. Creates a temporary news source.
3. Creates a temporary article.
4. Creates an article-country mapping.
5. Creates an article-state mapping.
6. Retrieves the article by URL.
7. Creates a temporary user.
8. Saves two favorite countries.
9. Saves Telangana as a favorite state.
10. Creates a temporary Top 10 ranking.
11. Retrieves the ranking.
12. Validates all results.
13. Rolls back the transaction.

Expected result:

```text
Repository integration test successful
India regions found: 36
Source created: True
Favorite countries: 2
Favorite states: 1
Ranking records: 1
Temporary test data will be rolled back.
```

Because the transaction is rolled back, the temporary integration-test records are not permanently stored.

---

## 18. Security

The database layer follows these security practices:

* The RDS password is stored in AWS Secrets Manager.
* The password is not stored in source code.
* The password is not stored in `.env`.
* The password is not written to logs.
* SQLAlchemy uses parameterized queries.
* PostgreSQL connections require SSL.
* RDS network access is restricted by a security group.
* Development access is limited to an approved public IP.
* AWS credentials are stored outside the Git repository.
* `.env` is ignored by Git.

The project must never commit:

```text
.env
AWS access keys
AWS secret keys
RDS passwords
Secrets Manager secret values
```

---

## 19. RDS Cost Control

The development RDS instance can be stopped when it is not needed.

Stop the instance:

```powershell
aws rds stop-db-instance `
  --db-instance-identifier "world-news-postgres-dev" `
  --profile "world-news-dev" `
  --region "us-east-1"
```

Check the status:

```powershell
aws rds describe-db-instances `
  --db-instance-identifier "world-news-postgres-dev" `
  --profile "world-news-dev" `
  --region "us-east-1" `
  --query "DBInstances[0].DBInstanceStatus" `
  --output text
```

Start it again:

```powershell
aws rds start-db-instance `
  --db-instance-identifier "world-news-postgres-dev" `
  --profile "world-news-dev" `
  --region "us-east-1"
```

Wait until it becomes available:

```powershell
aws rds wait db-instance-available `
  --db-instance-identifier "world-news-postgres-dev" `
  --profile "world-news-dev" `
  --region "us-east-1"
```

Stopping the instance does not delete:

* Tables
* Data
* Endpoint
* Security group
* Configuration
* Secret

---

## 20. Step 8 Final Result

World News AI now has a complete structured database foundation.

Implemented features include:

* SQLAlchemy declarative ORM base
* Predictable constraint naming
* PostgreSQL UUID fields
* PostgreSQL JSONB fields
* News-source storage
* Normalized article storage
* Article labels
* Country relevance mappings
* India state relevance mappings
* District and city support
* User accounts
* Maximum two favorite countries
* Favorite Indian states
* Top 10 state-news rankings
* Alembic schema migrations
* India region seed data
* Asynchronous repositories
* PostgreSQL upserts
* Unit tests
* Live Amazon RDS repository integration testing

---

## 21. Current Limitations

The following features are not yet implemented:

* Saving live GDELT articles through the repository layer
* Saving live RSS and Atom articles through the repository layer
* Automatic S3 raw-response persistence during ingestion
* Automatic rejected-record storage
* Country detection from article content
* India state detection from article content
* District and city seed catalogs
* Ranking-score calculation
* Scheduled ranking generation
* User authentication
* FastAPI database endpoints
* Dashboard database integration
* AWS Lambda ingestion
* Amazon SQS processing
* EventBridge scheduling
* AWS Glue processing
* CloudWatch monitoring

---

## 22. Next Major Step

The next major step is:

```text
Step 9 — Ingestion Persistence Pipeline
```

Step 9 will connect the existing ingestion providers to Amazon S3 and PostgreSQL.

Planned work includes:

1. Save original provider responses to the S3 raw layer.
2. Normalize GDELT, RSS, and Atom records.
3. Create or reuse news-source records.
4. Detect duplicate articles using URLs and content hashes.
5. Save valid articles to PostgreSQL.
6. Save processed article JSON to Amazon S3.
7. Save rejected records and rejection reasons to Amazon S3.
8. Add country mappings.
9. Add India state mappings.
10. Add transaction and failure handling.
11. Add ingestion-persistence unit tests.
12. Add a live end-to-end ingestion test.
