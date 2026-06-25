# Step 4 — News Categories and Article Data Models

## 1. Objective

The objective of Step 4 was to define a standard and validated data structure
for every news article processed by World News AI.

The models created in this step will be shared by:

* News ingestion
* Data processing
* Artificial intelligence
* PostgreSQL storage
* Elasticsearch indexing
* FastAPI responses
* Streamlit dashboard
* Social-media card generation

Using one common data model prevents different components from representing
the same article in different ways.

---

## 2. Work Completed

Step 4 completed the following work:

1. Created standard news categories.
2. Created dynamic article labels.
3. Created source-type definitions.
4. Created sentiment definitions.
5. Added standardized country validation.
6. Created the news-source model.
7. Created the main article model.
8. Created the social-media card data model.
9. Added URL validation.
10. Added country-code normalization.
11. Added keyword normalization.
12. Added UTC date conversion.
13. Added content-hash validation.
14. Created realistic sample article data.
15. Added automated model tests.
16. Verified JSON loading and serialization.

---

## 3. Files Created

```text
src/models/__init__.py
src/models/enums.py
src/models/country.py
src/models/source.py
src/models/article.py
tests/fixtures/sample_article.json
tests/unit/test_models.py
docs/step-04-news-data-models.md
```

## 4. Files Updated

```text
requirements.txt
README.md
docs/architecture.md
```

---

## 5. New Dependency

The following package was added:

```text
pycountry
```

`pycountry` provides standardized ISO country names and country codes.

Examples:

```text
India          → IN
United States  → US
United Kingdom → GB
```

This prevents the project from maintaining a large manually written country
list.

---

## 6. Model Architecture

```text
Enums and country utilities
        ↓
NewsSource model
        ↓
Article model
        ↓
AI, database, API, dashboard and search components
```

All future application components will use the same validated models.

---

## 7. News Categories

The project currently supports these primary categories:

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
14. General

An article receives one primary category.

Example:

```text
Primary category: Defence & Security
```

---

## 8. Dynamic Article Labels

The following labels were created:

```text
Breaking
Trending
Developing
Live
Analysis
Exclusive
Fact Check
```

Labels are different from categories.

The category describes the subject of an article.

Labels describe the current status or type of coverage.

Example:

```text
Category: Energy
Labels: Breaking, Trending
```

An article may have several labels.

---

## 9. Source Types

The project supports these collection-source types:

```text
RSS
GDELT
News API
Web Feed
Manual
```

These values identify how an article entered the application.

Example:

```text
Source name: Reuters
Source type: RSS
```

---

## 10. Sentiment Values

The following sentiment values were defined:

```text
Positive
Negative
Neutral
Mixed
Unknown
```

The initial value is:

```text
Unknown
```

AI processing can later update it after analyzing the article.

---

## 11. Country Utilities

Country validation is implemented in:

```text
src/models/country.py
```

### `normalize_country_code`

This function validates and standardizes two-letter ISO codes.

Example:

```python
normalize_country_code("in")
```

Result:

```text
IN
```

It also removes surrounding spaces:

```python
normalize_country_code(" us ")
```

Result:

```text
US
```

Invalid values such as `IND` or `XX` are rejected.

### `get_country_name`

This function returns the official country name.

Example:

```python
get_country_name("GB")
```

Result:

```text
United Kingdom
```

---

## 12. News Source Model

The `NewsSource` model stores information about a publisher.

Fields include:

```text
name
source_type
homepage_url
country_code
credibility_score
```

Example:

```text
Name: Reuters
Source type: RSS
Homepage: https://www.reuters.com
Country: GB
Credibility score: 95
```

### Source validation

The source model validates:

* Source-name length
* Homepage URL format
* Country code
* Credibility score

The credibility score must be between:

```text
0 and 100
```

Unexpected fields are rejected.

---

## 13. Article Model

The `Article` model is the main news structure used throughout the project.

### Identity

```text
article_id
```

A UUID is generated automatically for each article.

### Article content

```text
title
description
content
summary
```

### URLs

```text
url
canonical_url
image_url
```

Pydantic validates these using `HttpUrl`.

Malformed URLs are rejected.

### Source and author

```text
source
author
```

### Dates

```text
published_at
collected_at
```

All dates are normalized to UTC.

### Classification

```text
primary_category
labels
sentiment
country_codes
keywords
language_code
```

### Processing fields

```text
ai_processed
content_hash
```

### Sharing fields

```text
share_caption
social_card
```

---

## 14. Why UTC Is Used

News sources publish articles from different time zones.

Examples include:

```text
India Standard Time
Central Time
British Summer Time
Japan Standard Time
```

The application converts all dates to UTC.

This allows articles to be:

* Sorted correctly
* Compared correctly
* Stored consistently
* Processed by scheduled pipelines
* Displayed in the user's local time later

---

## 15. Keyword Normalization

The article model removes empty and duplicate keywords.

Input:

```text
Energy
 energy
India
empty value
```

Stored output:

```text
Energy
India
```

Duplicate comparison is case-insensitive.

This improves:

* Search
* Analytics
* Elasticsearch indexing
* Trending-topic calculations

---

## 16. Country Normalization

Input:

```text
in
US
in
```

Stored output:

```text
IN
US
```

The model:

* Converts codes to uppercase
* Checks ISO validity
* Removes duplicates
* Preserves the original order

---

## 17. Content Hash

The article model includes:

```text
content_hash
```

This field expects a 64-character hexadecimal SHA-256 value.

Example:

```text
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

The hash will later help detect:

* Exact duplicate articles
* Repeated ingestion
* Content changes
* Previously processed stories

Actual hash generation will be implemented in a later processing step.

---

## 18. Social-Media Card Model

The `SocialCardData` model stores information required to generate a shareable
news image.

Fields include:

```text
headline
summary
background_image_url
template_name
generated_image_path
is_generated
```

The default template is:

```text
standard
```

The initial generation status is:

```text
false
```

Planned flow:

```text
Validated article
      ↓
Select article or background image
      ↓
Apply social-card template
      ↓
Add headline and summary
      ↓
Generate PNG
      ↓
Store generated image path
      ↓
Allow download and sharing
```

The actual image-generation code will be implemented later.

---

## 19. Pydantic Validation

The models use Pydantic to validate incoming data.

Validation includes:

* Required article fields
* Minimum and maximum text lengths
* Valid URL formats
* Accepted enum values
* Country codes
* Credibility scores
* Port-independent article data
* Language-code pattern
* Content-hash format
* UTC date conversion

Invalid data is rejected before it reaches the database or dashboard.

---

## 20. Configuration Behavior

The models use:

```python
ConfigDict(
    str_strip_whitespace=True,
    extra="forbid",
    validate_assignment=True,
)
```

### `str_strip_whitespace=True`

Removes unnecessary spaces around text values.

### `extra="forbid"`

Rejects unexpected fields.

This helps detect misspelled field names.

### `validate_assignment=True`

Validates a field again when its value is changed after model creation.

---

## 21. Sample Article Fixture

A realistic sample article is stored in:

```text
tests/fixtures/sample_article.json
```

It contains:

* Article text
* Source information
* URLs
* Category
* Labels
* Sentiment
* Countries
* Keywords
* AI status
* Content hash
* Social-card information

The fixture can be reused later for:

* Database tests
* API tests
* Ingestion tests
* Elasticsearch tests
* Dashboard tests

---

## 22. Automated Tests

The model tests are stored in:

```text
tests/unit/test_models.py
```

They verify:

1. Categories and labels contain the expected values.
2. Country codes are normalized.
3. Invalid country codes are rejected.
4. News sources are validated.
5. Invalid credibility scores are rejected.
6. Countries, keywords and dates are normalized.
7. Invalid URLs are rejected.
8. Invalid hashes are rejected.
9. Sample JSON loads successfully.
10. Social-card defaults work.
11. Validated articles can be exported to JSON.

The project currently has:

```text
5 configuration tests
4 logging tests
10 model test functions
```

All unit tests must pass before Step 4 is committed.

---

## 23. Article Data Flow

```text
News source response
        ↓
Raw article dictionary or JSON
        ↓
Article model
        ↓
Validation
        ├── Validate source
        ├── Validate URLs
        ├── Normalize countries
        ├── Normalize keywords
        ├── Convert dates to UTC
        └── Validate categories and labels
        ↓
Validated article
        ├── Kafka
        ├── PostgreSQL
        ├── Elasticsearch
        ├── AI processing
        ├── FastAPI
        └── Streamlit dashboard
```

---

## 24. Current Limitations

The models are implemented, but the following work has not started:

* Article collection from live sources
* Content-hash generation
* Database storage
* Kafka publishing
* AI classification
* AI summarization
* Duplicate detection
* Trending-score calculation
* Social-card image generation

The current step provides the validated structure required by those future
features.

---

## 25. Step 4 Final Result

World News AI now has standardized models for:

* Categories
* Article labels
* Sentiment
* Source types
* Countries
* Publishers
* News articles
* Social-media cards

These models provide one consistent structure across the entire application.

---

## 26. Next Step

The next major step is:

```text
Step 5 — News Ingestion Foundation
```

Step 5 will introduce:

* HTTPX
* Asynchronous HTTP requests
* News-source interfaces
* GDELT request models
* Safe request handling
* Retry and timeout handling
* Raw article collection
