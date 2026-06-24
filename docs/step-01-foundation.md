# Step 1 — Project Foundation

## Objective

Create a modular foundation for the World News AI application before
implementing news collection, artificial intelligence or database
functionality.

## Work Completed

- Created the World News AI project directory.
- Created a Python virtual environment.
- Initialized a Git repository.
- Created the modular application folder structure.
- Separated ingestion, processing, AI, API, search and database components.
- Created separate folders for Airflow and Spark.
- Created testing, documentation, infrastructure and monitoring folders.
- Added `.gitignore`.
- Added `.env.example`.
- Added the initial README.
- Defined the primary news categories.
- Defined the copy-content feature.
- Defined the social-media news-card feature.
- Created the initial current and target architectures.

## Why a Modular Structure Was Used

The project will contain several independent services and processing stages.

Keeping every responsibility in a separate module makes the application:

- Easier to understand
- Easier to test
- Easier to maintain
- Easier to deploy
- Easier to scale
- Better suited for team development

## Folder Responsibilities

### src/ingestion

Collects articles from GDELT, RSS feeds and news APIs.

Future responsibilities include:

- Connecting to news sources
- Fetching articles
- Handling API errors
- Tracking source availability
- Publishing articles to Kafka

### src/processing

Cleans, normalizes, validates and deduplicates news data.

Future responsibilities include:

- Standardizing article fields
- Removing invalid records
- Detecting duplicate articles
- Normalizing country and category names
- Preparing data for AI processing

### src/ai

Contains artificial-intelligence operations.

Future responsibilities include:

- Article summarization
- News classification
- Entity extraction
- Sentiment analysis
- Embedding generation
- Related-story detection
- Social-media caption generation

### src/database

Contains PostgreSQL database connections, models and repositories.

Future responsibilities include:

- Saving articles
- Saving article sources
- Saving categories
- Saving AI results
- Tracking pipeline status
- Saving generated news-card metadata

### src/search

Contains Elasticsearch indexing and search operations.

Future responsibilities include:

- Full-text search
- Keyword search
- Article filtering
- Related-news search
- Semantic search

### src/api

Contains FastAPI routes and request and response models.

Future endpoints may include:

- Latest news
- Search news
- News by category
- News by country
- Trending news
- Article details
- Generate social card
- Download generated social card

### src/common

Contains shared functionality.

Future responsibilities include:

- Application configuration
- Logging
- Constants
- Shared exceptions
- Utility functions
- Category definitions

### dashboard

Contains the Streamlit user interface.

Future responsibilities include:

- Displaying articles
- Applying filters
- Showing AI summaries
- Copying news content
- Generating social-media cards
- Downloading PNG cards
- Opening original article links

### orchestration/dags

Contains Apache Airflow workflows.

Future responsibilities include:

- Scheduling news collection
- Running processing jobs
- Running AI jobs
- Handling retries
- Monitoring failed tasks

### spark/jobs

Contains PySpark processing jobs.

Future responsibilities include:

- Large-scale article processing
- Deduplication
- Aggregations
- Trending-score calculations
- Historical analytics

### tests/unit

Tests individual functions and classes.

### tests/integration

Tests communication between:

- APIs
- Databases
- Kafka
- Elasticsearch
- Redis
- External news sources

### infrastructure/docker

Contains Dockerfiles and Docker Compose configuration.

### monitoring

Contains Prometheus and Grafana configuration.

### data/raw

Temporarily stores raw articles during local development.

### data/processed

Temporarily stores cleaned and processed articles during local development.

## Planned Copy Feature

The dashboard will provide copy buttons for:

- Headline
- Summary
- Article URL
- Formatted article content
- Social-media caption

The copy feature improves usability because users do not need to manually
select and copy different parts of the article.

## Planned Social-Media News Card

The application will generate a visual news card from a selected article.

The news card will contain:

- Headline
- Short summary
- Category
- Country
- Source
- Publication date
- Related background image
- Application branding

The final output will be a PNG image.

## Why Pillow Is Planned

Pillow is a Python image-processing library.

It will allow the project to:

- Open a background image
- Resize and crop the image
- Add a dark overlay
- Draw headline text
- Draw summary text
- Add category and source information
- Add branding
- Save the result as PNG

Pillow is suitable because the image-generation process remains inside the
Python application and can be tested with Pytest.

## Image Selection Strategy

The application will select a background image in the following order:

1. Use the original article image when it is available and usable.
2. Use a licensed external image related to the article topic.
3. Use a category-specific default background.
4. Use a generic application background.

This fallback process ensures that a news card can still be generated even
when an article has no image.

## Current Limitations

- No news articles are being collected yet.
- No external services have been installed.
- No AI model has been connected.
- No database has been created.
- Copy buttons are not implemented yet.
- Social-media card generation is not implemented yet.

This step only establishes the project foundation and documents the planned
features.

## Next Step

Build a centralized configuration-management module using Pydantic Settings.

The configuration module will:

- Load values from `.env`
- Validate required settings
- Prevent hardcoded passwords and API keys
- Provide one central configuration object
- Support multiple environments