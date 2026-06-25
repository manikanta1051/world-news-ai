# World News AI

World News AI is a data engineering and artificial intelligence project that collects global news from multiple sources, processes and classifies articles, detects duplicate stories, identifies trending events, and provides searchable news through an API and dashboard.

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

## Primary Categories

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

Trending and Breaking are dynamic labels rather than permanent categories.

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
India announces a new energy infrastructure project

Summary:
The government announced a major energy project intended to improve electricity generation and energy security.

Category:
Energy

Source:
Example News

Read more:
https://example.com/article
```

## Completed Steps

### Step 3: Centralized Application Logging

The project currently includes:

* Console logging
* Rotating file logging
* Application startup logging
* Automated logging tests

## Next Step

### Step 4: News Categories and Article Data Models

Create the news category definitions and article data models.

This step will define:

* Standard article fields
* Primary news categories
* Countries and locations
* Trending and breaking labels
* Article validation rules
* Social-media card fields
