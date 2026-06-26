# Step 7 — AWS Storage Foundation

## 1. Objective

Step 7 created the AWS-first storage foundation for World News AI.

The project now uses:

* Amazon S3 for raw, processed, rejected, curated, and social-card data
* Amazon RDS for PostgreSQL structured storage
* AWS Secrets Manager for database credentials
* Boto3 for AWS service access
* SQLAlchemy and AsyncPG for asynchronous PostgreSQL connections

---

## 2. AWS Storage Architecture

```text
News Providers
    ├── GDELT
    └── RSS and Atom
          ↓
Validated and raw news data
          ↓
Amazon S3 Data Lake
    ├── raw/news
    ├── processed/news
    ├── rejected/news
    ├── curated/news
    └── social-cards
          ↓
Amazon RDS PostgreSQL
    ├── Sources
    ├── Articles
    ├── Categories
    ├── Labels
    ├── Countries
    ├── Indian states
    ├── Districts and cities
    ├── State article relevance
    ├── Top 10 state news
    └── User preferences
```

---

## 3. Work Completed

Step 7 completed the following work:

1. Configured the AWS CLI development profile.
2. Added Boto3 support.
3. Created a reusable Boto3 session.
4. Created a private Amazon S3 data-lake bucket.
5. Enabled S3 public-access blocking.
6. Enabled S3 versioning.
7. Enabled default server-side encryption.
8. Added project tags to AWS resources.
9. Created the S3 news-storage service.
10. Added raw-news storage.
11. Added processed-article storage.
12. Added curated-article storage.
13. Added rejected-record storage.
14. Added partition-friendly S3 object keys.
15. Added India country and state partition support.
16. Added S3 storage exceptions.
17. Added mocked S3 unit tests.
18. Created an encrypted Amazon RDS PostgreSQL instance.
19. Created an RDS security group.
20. Restricted PostgreSQL access to the developer IP.
21. Enabled RDS-managed credentials through Secrets Manager.
22. Added RDS endpoint and secret configuration.
23. Created database-specific exceptions.
24. Created secure Secrets Manager credential retrieval.
25. Added asynchronous SQLAlchemy connection pooling.
26. Added AsyncPG PostgreSQL support.
27. Required encrypted database connections.
28. Added automatic commit and rollback handling.
29. Added a live database health check.
30. Added automated database-connection tests.

---

## 4. Dependencies Added

```text
boto3
sqlalchemy
asyncpg
alembic
```

### Boto3

Used to access:

* Amazon S3
* AWS Secrets Manager
* Amazon RDS metadata
* Future SQS, Glue, Lambda, and CloudWatch services

### SQLAlchemy

Provides:

* Asynchronous database engine
* Database sessions
* Connection pooling
* Transactions
* Future ORM database models

### AsyncPG

Provides the asynchronous PostgreSQL driver.

### Alembic

Will manage database schema migrations in Step 8.

---

## 5. AWS Authentication

Local development uses:

```text
AWS profile: world-news-dev
Region: us-east-1
```

AWS credentials are stored outside the repository in the user AWS configuration directory.

The project does not store:

```text
AWS access key
AWS secret access key
RDS master password
```

inside Git.

Later AWS-hosted services will use IAM roles instead of local AWS profiles.

---

## 6. Amazon S3 Data Lake

The project uses one private data-lake bucket.

Logical storage areas include:

```text
raw/news
processed/news
rejected/news
curated/news
social-cards
```

### Raw Layer

Stores original provider responses before transformation.

Examples:

* GDELT JSON responses
* RSS provider payloads
* Future API responses

### Processed Layer

Stores validated Article objects after normalization.

### Rejected Layer

Stores invalid records together with the reason they were rejected.

### Curated Layer

Will store analytics-ready and AI-enriched articles.

### Social Cards

Will store generated news images for sharing and downloading.

---

## 7. S3 Security

The bucket uses:

* Block Public Access
* Server-side encryption
* Object versioning
* AWS resource tags

News data and generated assets remain private unless the application later creates controlled download URLs.

---

## 8. S3 Object-Key Structure

Example raw object:

```text
raw/news/
provider=gdelt/
year=2026/
month=06/
day=26/
hour=18/
record-id.json
```

Example processed article:

```text
processed/news/
provider=example-news/
category=energy/
year=2026/
month=06/
day=26/
hour=18/
article-id.json
```

This structure supports:

* AWS Glue
* Amazon Athena
* PySpark
* Date-based processing
* Provider analysis
* Category analysis
* Troubleshooting

---

## 9. India State Partition Support

The S3 service supports additional partitions.

Example:

```text
country=in
state=tg
district=hyderabad
```

A future Telangana article may be stored as:

```text
processed/news/
provider=example-news/
category=politics-diplomacy/
country=in/
state=tg/
district=hyderabad/
year=2026/
month=06/
day=26/
hour=18/
article-id.json
```

This supports the planned India News section and Top 10 news for each state.

---

## 10. S3 Storage Service

The main class is:

```python
S3NewsStorageService
```

It provides:

```text
save_raw_payload()
save_article()
save_rejected_payload()
put_json()
build_object_key()
```

### `save_raw_payload`

Stores original provider data.

### `save_article`

Stores validated processed or curated articles.

### `save_rejected_payload`

Stores invalid records and rejection reasons.

### `build_object_key`

Builds provider, category, location, and date partitions.

---

## 11. Amazon RDS PostgreSQL

The development database uses:

```text
Identifier: world-news-postgres-dev
Engine: PostgreSQL
Instance class: db.t4g.micro
Database: world_news
Port: 5432
Storage encryption: enabled
Public endpoint: enabled for development
Network access: restricted by security group
```

Production deployment will use private networking.

---

## 12. RDS Network Security

The database security group allows PostgreSQL traffic only from an approved development IP.

```text
Protocol: TCP
Port: 5432
Source: developer-public-ip/32
```

The database is not opened to:

```text
0.0.0.0/0
```

The rule may need to be updated when the developer’s public IP changes.

---

## 13. AWS Secrets Manager

RDS generated the master password and stored it in AWS Secrets Manager.

The private `.env` contains:

```text
AWS_RDS_SECRET_ID
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_DB
POSTGRES_USER
```

The private `.env` does not contain the database password.

The application retrieves the password when creating the database connection.

---

## 14. Database Credential Loader

The credential loader:

1. Reads `AWS_RDS_SECRET_ID`.
2. Connects to Secrets Manager.
3. Retrieves the secret JSON.
4. Extracts the username and password.
5. Uses the configured RDS endpoint and database name when required.
6. Validates the complete credentials.
7. Stores the password inside Pydantic `SecretStr`.

The password is not written to logs.

---

## 15. SQLAlchemy Connection Layer

The application uses:

```text
postgresql+asyncpg
```

The connection layer provides:

```text
build_database_url()
create_database_engine()
get_async_engine()
get_session_factory()
database_session()
check_database_connection()
close_database_engine()
```

### Connection Pooling

Configured fields include:

```text
POSTGRES_POOL_SIZE
POSTGRES_MAX_OVERFLOW
```

The pool reuses database connections rather than opening a new connection for every operation.

### Transaction Handling

The `database_session()` context manager:

```text
Successful operation → Commit
Failed operation     → Rollback
```

---

## 16. SSL/TLS

The project uses:

```text
POSTGRES_SSL_MODE=require
```

This requires an encrypted connection between the Python application and Amazon RDS.

---

## 17. Live Database Health Check

The connection check runs:

```sql
SELECT
    current_database(),
    current_user,
    version();
```

It confirms:

* The RDS endpoint is reachable
* Secrets Manager returns valid credentials
* SSL connection succeeds
* The `world_news` database exists
* The database user can connect

---

## 18. Automated Tests

### S3 Tests

The S3 tests verify:

* JSON serialization
* Unicode support
* Raw object keys
* Processed article storage
* India state partitions
* Rejected-record storage
* Missing bucket handling
* AWS error conversion

### Database Tests

The database tests verify:

* SecretString decoding
* SecretBinary decoding
* RDS credential mapping
* Configuration fallbacks
* Missing secret validation
* Secrets Manager error conversion
* AsyncPG URL and engine creation

The tests use fake AWS clients and do not expose real credentials.

---

## 19. Current Test Count

```text
Configuration tests         8
Logging tests               4
Model tests                10
HTTP client tests           5
GDELT provider tests        5
Feed-source tests           7
RSS provider tests          8
S3 storage tests            8
Database connection tests   7
--------------------------------
Total                      62
```

Run all tests with:

```powershell
python -m pytest tests\unit -v
```

---

## 20. Current Limitations

The following features are not yet implemented:

* PostgreSQL tables
* SQLAlchemy ORM models
* Alembic migrations
* Article repositories
* Source repositories
* India state and district tables
* User favorite-country storage
* User favorite-state storage
* Top 10 ranking tables
* Scheduled AWS ingestion
* S3 lifecycle policies
* AWS Glue catalog
* Amazon Athena queries

---

## 21. Step 7 Final Result

World News AI now has a secure AWS storage foundation with:

* Private Amazon S3 storage
* Raw, processed, rejected, and curated layers
* Location-based S3 partitions
* Encrypted Amazon RDS PostgreSQL
* Secrets Manager credentials
* Async SQLAlchemy connections
* SSL-required PostgreSQL access
* Automated S3 and database tests

---

## 22. Next Step

The next major step is:

```text
Step 8 — Database Schema, Migrations, and Repositories
```

Step 8 will create:

* SQLAlchemy ORM base
* News-source table
* Article table
* Article labels and countries
* Indian states and districts
* Article-to-state mappings
* User favorite countries and states
* Top 10 state-news ranking structure
* Alembic migrations
* Repository methods
* Automated database-model tests
