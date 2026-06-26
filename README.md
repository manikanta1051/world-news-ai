# World News AI

World News AI is a data engineering and artificial intelligence project that collects global news from multiple sources, processes and classifies articles, detects duplicate stories, identifies trending events, and provides searchable news through an API and dashboard.

The project is being developed step by step using production-style practices such as structured configuration, centralized logging, data validation, automated testing, documentation, and modular application design.

## Project Goals

* Collect current global news from multiple sources.
* Process both batch and streaming news data.
* Categorize articles into meaningful world-news categories.
* Detect duplicate and related articles.
* Generate concise AI summaries.
* Extract countries, organizations, people, and locations.
* Calculate trending and breaking-news scores.
* Provide full-text and semantic search.
* Display news analytics through an interactive dashboard.
* Allow users to copy headlines, summaries, and article links.
* Generate shareable social-media news cards.
* Build a production-style, monitored data pipeline.

## Primary News Categories

1. Politics & Diplomacy
2. Defence & Security
3. Conflict & Humanitarian
4. Economy & Business
5. Energy
6. Technology & AI
7. Health & Medicine
8. Science & Space
9. Climate & Environment
10. Disasters & Weather
11. Law & Governance
12. Society & Culture
13. Sports

Trending and Breaking are dynamic article labels rather than permanent news categories.

## Planned System Architecture

```text
News Sources
     |
     v
Data Ingestion
     |
     v
Raw News Storage
     |
     v
Data Cleaning and Validation
     |
     v
Duplicate Detection
     |
     v
News Classification
     |
     v
AI Summarization
     |
     v
Entity and Location Extraction
     |
     v
Trending and Breaking Scoring
     |
     v
Processed News Storage
     |
     +-------------------+
     |                   |
     v                   v
Search API         Analytics Dashboard
```

## Planned User Features

### News Dashboard

Users will be able to:

* Browse current world news.
* Search for articles.
* Filter by country.
* Filter by category.
* Filter by source.
* Filter by publication date.
* View AI-generated summaries.
* View related articles covering the same event.
* View trending and breaking-news labels.
* View news analytics and category trends.

### Copy Feature

Each article will provide options to copy:

* Headline
* AI summary
* Article link
* Headline and summary together
* Full formatted news content

Example copied content:

```text
Headline:
India announces a new renewable energy project

Summary:
The government announced a major renewable energy project intended to improve electricity generation and energy security.

Category:
Energy

Source:
Example News

Read more:
https://example.com/article
```

### Social-Media Card Feature

The application will support shareable social-media news cards containing:

* Headline
* Short summary
* Category
* Source
* Publication date
* Country or location
* Article image
* Share caption
* Article link

## Current Project Structure

```text
World_News_AI/
|
|-- docs/
|   |-- architecture.md
|   |-- step-02-configuration.md
|   |-- step-03-logging.md
|   `-- step-04-news-data-models.md
|
|-- logs/
|
|-- src/
|   |-- common/
|   |   |-- config.py
|   |   `-- logging_config.py
|   |
|   |-- models/
|   |   |-- __init__.py
|   |   |-- article.py
|   |   |-- country.py
|   |   |-- enums.py
|   |   `-- source.py
|   |
|   `-- main.py
|
|-- tests/
|   |-- fixtures/
|   |   `-- sample_article.json
|   |
|   `-- unit/
|       |-- test_config.py
|       |-- test_logging_config.py
|       `-- test_models.py
|
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Completed Development Steps

### Step 1: Project Foundation

The initial project structure was created with separate folders for:

* Application source code
* Unit tests
* Test fixtures
* Documentation
* Configuration
* Logs

### Step 2: Centralized Configuration

The project includes centralized configuration management for:

* Application environment
* Debug mode
* Logging settings
* Environment variables
* Default configuration values
* Configuration validation

Environment variables are loaded from a local `.env` file.

The `.env.example` file documents the required configuration fields without exposing real credentials.

### Step 3: Centralized Application Logging

The project includes centralized logging with:

* Console logging
* Rotating file logging
* Configurable log levels
* Configurable log file paths
* Application startup logging
* Prevention of duplicate log handlers
* Automated logging tests

The rotating file handler prevents application log files from growing without limits.

### Step 4: News Categories and Article Data Models

The project includes validated models for news data.

Implemented components include:

* Standard news categories
* Dynamic article labels
* Source-type definitions
* Sentiment labels
* ISO country-code normalization
* Country-name lookup
* News-source model
* Complete article model
* Social-media card model
* URL validation
* Publication date validation
* Keyword normalization
* Duplicate keyword removal
* Duplicate country-code removal
* Article JSON fixture
* Automated model validation tests

## Data Models

### NewsSource

The news-source model stores information such as:

* Source name
* Source type
* Homepage URL
* Country code
* Credibility score

Example source types include:

* RSS
* REST API
* Website
* Streaming source

### Article

The article model stores fields such as:

* Article ID
* Title
* Description
* Original article URL
* Image URL
* Source
* Author
* Publication time
* Primary category
* Article labels
* Sentiment
* Country codes
* Keywords
* AI summary
* Share caption

### SocialCardData

The social-media card model contains formatted data used to generate shareable news cards.

It can include:

* Headline
* Summary
* Category
* Source
* Country
* Image
* Publication date
* Share caption
* Article URL

## Article Validation

The models validate and normalize incoming news data.

Examples include:

```text
"in"       -> "IN"
" us "     -> "US"
```

Duplicate country codes are removed:

```text
["in", "US", "in"]
```

becomes:

```text
["IN", "US"]
```

Duplicate keywords are also removed without considering letter case:

```text
[
    "Renewable Energy",
    "India",
    "renewable energy"
]
```

becomes:

```text
[
    "Renewable Energy",
    "India"
]
```

## Installation

### 1. Clone the repository

```powershell
git clone <repository-url>
cd World_News_AI
```

### 2. Create a virtual environment

```powershell
python -m venv venv
```

### 3. Activate the virtual environment

Using PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, the terminal should display:

```text
(venv)
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Create the local environment file

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Update the `.env` file with local configuration values.

Do not commit the real `.env` file because it may contain API keys, passwords, or other secrets.

## Running the Application

Run the main application module from the project root:

```powershell
python -m src.main
```

This verifies that:

* Configuration loads correctly.
* Logging initializes correctly.
* Application startup messages are generated.

## Running Tests

Run all tests:

```powershell
python -m pytest -v
```

Run configuration tests:

```powershell
python -m pytest tests/unit/test_config.py -v
```

Run logging tests:

```powershell
python -m pytest tests/unit/test_logging_config.py -v
```

Run model tests:

```powershell
python -m pytest tests/unit/test_models.py -v
```

## Example Article Model

```python
from datetime import datetime, timezone

from src.models import (
    Article,
    ArticleLabel,
    NewsCategory,
    NewsSource,
    SentimentLabel,
    SourceType,
)

source = NewsSource(
    name="Reuters",
    source_type=SourceType.RSS,
    homepage_url="https://www.reuters.com",
    country_code="GB",
    credibility_score=95,
)

article = Article(
    title="India announces a new renewable energy project",
    description=(
        "The government announced a major project "
        "to improve renewable energy production."
    ),
    url="https://www.reuters.com/world/example-article",
    image_url="https://www.reuters.com/example-image.jpg",
    source=source,
    author="Example Reporter",
    published_at=datetime.now(timezone.utc),
    primary_category=NewsCategory.ENERGY,
    labels={
        ArticleLabel.BREAKING,
        ArticleLabel.TRENDING,
    },
    sentiment=SentimentLabel.NEUTRAL,
    country_codes=["IN", "US"],
    keywords=[
        "Renewable Energy",
        "India",
    ],
    share_caption=(
        "India announces a major renewable energy project."
    ),
)

print(article.model_dump_json(indent=2))
```

## Development Practices

The project follows these development practices:

* Modular Python source code
* Environment-based configuration
* Centralized application logging
* Strong data validation
* Automated unit testing
* Reusable data models
* Test fixtures
* Step-by-step technical documentation
* Git version control
* Clear commit history
* Separation of application code and tests

- Step 5: News-ingestion foundation
- Reusable asynchronous HTTP client
- Connection pooling and timeouts
- Automatic retry handling
- Project-specific ingestion exceptions
- Standard news-provider interface
- Live GDELT news provider
- GDELT response-to-Article mapping
- Mocked HTTP and provider tests

* Step 6: RSS and Atom news ingestion
* Validated feed-source registry
* Official NASA and JPL feed configurations
* Feed enable and disable controls
* RSS and Atom parsing with Feedparser
* HTML description and content cleaning
* Author, publication-date, and image extraction
* Query and timespan filtering
* Per-source article limits
* URL-based feed-entry deduplication
* RSS fixtures and automated tests

* Step 7: AWS storage foundation
* Private Amazon S3 data-lake bucket
* Raw, processed, rejected, curated, and social-card layers
* S3 public-access blocking, encryption, and versioning
* Provider, category, date, country, and state partitions
* Mocked S3 storage tests
* Encrypted Amazon RDS PostgreSQL database
* RDS credentials managed through AWS Secrets Manager
* PostgreSQL security-group access restricted to the developer IP
* Async SQLAlchemy and AsyncPG connection layer
* SSL-required RDS connections
* Database health check and connection tests

### Next Step

Create the PostgreSQL database schema and repository layer.

The next step will:

* Add SQLAlchemy ORM models.
* Create source and article tables.
* Add countries, Indian states, districts, and cities.
* Add article-to-location mappings.
* Add user favorite-country and favorite-state storage.
* Add Top 10 state-news ranking structures.
* Create Alembic migrations.
* Add database repository methods.
* Apply the first schema migration to Amazon RDS.
