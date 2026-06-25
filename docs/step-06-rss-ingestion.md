# Step 6 — RSS and Atom News Provider

## 1. Objective

The objective of Step 6 was to add RSS and Atom feed ingestion to the World
News AI project.

The project can now collect articles from configured publisher feeds, parse
their XML content, validate individual entries, remove duplicate URLs, and
convert valid entries into the standard Article model.

---

## 2. Why RSS and Atom Ingestion Is Required

GDELT provides broad global coverage, but World News AI should not depend on
only one source.

Many trusted organizations publish their latest updates through RSS or Atom
feeds.

Examples include:

* Government organizations
* Space agencies
* Health organizations
* Energy organizations
* Technology publishers
* International institutions
* News organizations

RSS ingestion allows World News AI to collect articles directly from these
publishers.

The ingestion flow is:

```text
Configured feed source
        ↓
Asynchronous HTTP request
        ↓
RSS or Atom XML
        ↓
Feedparser
        ↓
Entry validation and normalization
        ↓
Duplicate and time filtering
        ↓
Validated Article models
```

---

## 3. Work Completed

Step 6 completed the following work:

1. Installed the Feedparser library.
2. Added Feedparser to `requirements.txt`.
3. Created the feed-format enum.
4. Created the feed-source configuration model.
5. Created the central feed registry.
6. Added official NASA and JPL feeds.
7. Added feed enable and disable controls.
8. Added feed lookup functions.
9. Added duplicate source-ID validation.
10. Added duplicate feed-URL validation.
11. Created the RSS and Atom news provider.
12. Reused the asynchronous HTTP client.
13. Added RSS and Atom XML parsing.
14. Added feed parsing-error handling.
15. Added article-title extraction.
16. Added article-link extraction.
17. Added description extraction.
18. Added full feed-content extraction.
19. Added HTML removal and text normalization.
20. Added author extraction.
21. Added publication-date conversion to UTC.
22. Added image extraction.
23. Added category and source mapping.
24. Added local keyword filtering.
25. Added timespan filtering.
26. Added per-source article limits.
27. Added URL-based duplicate prevention.
28. Added malformed-feed handling.
29. Added RSS fixtures.
30. Added feed-registry tests.
31. Added RSS-provider tests.
32. Verified the complete unit-test suite.

---

## 4. Files Created

```text
src/ingestion/feed_sources.py
src/ingestion/providers/rss.py
tests/fixtures/rss_feed.xml
tests/fixtures/malformed_feed.xml
tests/unit/test_feed_sources.py
tests/unit/test_rss_provider.py
docs/step-06-rss-ingestion.md
```

## 5. Files Updated

```text
requirements.txt
src/ingestion/__init__.py
src/ingestion/providers/__init__.py
README.md
docs/architecture.md
```

---

## 6. New Dependency

The following dependency was added:

```text
feedparser
```

Feedparser supports common syndication formats such as:

```text
RSS 1.0
RSS 2.0
Atom 0.3
Atom 1.0
```

It converts different feed formats into a normalized Python structure.

Example:

```python
parsed_feed.entries
entry.title
entry.link
entry.summary
entry.published
```

This prevents the project from writing separate XML parsers for every feed
format.

---

## 7. Feed Source Configuration

Feed sources are defined in:

```text
src/ingestion/feed_sources.py
```

Each source is represented by:

```python
FeedSourceConfig
```

The configuration contains:

```text
source_id
name
feed_url
homepage_url
source_country_code
default_category
language_code
expected_format
is_official_source
enabled
max_articles_per_fetch
```

Example:

```text
Source ID: nasa-technology
Name: NASA Technology
Country: US
Category: Technology & AI
Format: RSS
Official source: Yes
Enabled: Yes
Maximum articles: 50
```

---

## 8. Feed Source IDs

Each source has a unique internal ID.

Example:

```text
nasa-technology
nasa-news-releases
nasa-jpl-news
```

Source IDs use lowercase slug formatting.

Valid:

```text
nasa-technology
world-health-news
energy-reports
```

Invalid:

```text
NASA Technology
nasa_technology
Nasa-Technology
```

Using standardized source IDs makes configuration, logging, testing, and
future scheduling easier.

---

## 9. Feed Registry

The feed registry is stored in:

```python
FEED_SOURCES
```

The registry provides one central place for all configured RSS and Atom
sources.

Benefits include:

* Central source management
* Consistent categories
* Feed enable and disable controls
* Duplicate source detection
* Easier scheduling
* Easier testing
* Easier future database migration

---

## 10. Initial Feed Sources

The initial registry contains official NASA and JPL feeds.

Configured sources include:

```text
NASA Recently Published
NASA News Releases
NASA Technology
NASA Jet Propulsion Laboratory News
```

These initial feeds are used to establish the ingestion framework.

Additional feeds will be added gradually after their availability, usage
rules, and reliability are verified.

---

## 11. Registry Validation

The function:

```python
validate_feed_registry()
```

checks that:

* Every source ID is unique
* Every feed URL is unique

Duplicate IDs are rejected because two configurations should not use the same
internal identity.

Duplicate URLs are rejected because downloading the same feed twice would
produce repeated articles and unnecessary network requests.

---

## 12. Feed Lookup Functions

### `get_enabled_feed_sources`

Returns all feeds whose `enabled` field is `True`.

Example:

```python
sources = get_enabled_feed_sources()
```

This will later allow a scheduler to process every active source.

### `get_feed_source`

Returns one feed configuration by source ID.

Example:

```python
source = get_feed_source("nasa-technology")
```

Unknown IDs raise a `KeyError`.

---

## 13. RSS Provider

The provider is implemented in:

```text
src/ingestion/providers/rss.py
```

The main class is:

```python
RssNewsProvider
```

The provider receives either:

* A configured source ID
* A `FeedSourceConfig` object

Example:

```python
provider = RssNewsProvider("nasa-technology")
```

---

## 14. RSS Provider Flow

```text
Feed source configuration
        ↓
RssFetchRequest validation
        ↓
AsyncNewsHttpClient
        ↓
Download XML
        ↓
Feedparser
        ↓
Validate parsed feed
        ↓
Process each entry
        ↓
Create Article model
        ↓
Apply duplicate, query, date, and limit filters
        ↓
Return validated articles
```

---

## 15. Request Validation

The provider uses:

```python
RssFetchRequest
```

It validates:

```text
query
max_records
timespan
```

### Query

The query is optional.

When supplied, it filters article text locally.

### Maximum records

The accepted range is:

```text
1 to 200
```

The feed source may define a smaller limit.

### Timespan

Supported examples include:

```text
30min
24h
7d
2weeks
3months
```

The timespan controls how old an article may be.

---

## 16. Effective Article Limit

Two limits may exist:

```text
Request limit
Source configuration limit
```

The provider uses the smaller value.

Example:

```text
Request maximum: 100
Source maximum: 50
Effective maximum: 50
```

This prevents one request from exceeding the publisher-specific ingestion
limit.

---

## 17. Feed Parsing

The provider downloads the feed through:

```python
AsyncNewsHttpClient
```

The response content is parsed using:

```python
feedparser.parse(response.content)
```

Feedparser returns:

```text
Feed metadata
Feed version
Article entries
Parsing warnings
```

---

## 18. Parsing Warning Handling

Feedparser may mark a feed as malformed while still returning usable entries.

The provider uses the following behavior:

```text
Parsing warning with usable entries
        ↓
Log the warning and continue

Parsing warning without entries
        ↓
Raise NewsProviderResponseError
```

This avoids rejecting an entire feed for a minor formatting issue.

---

## 19. HTML Text Cleaning

RSS descriptions often contain HTML.

Example input:

```html
<p>NASA is testing a <strong>new system</strong>.</p>
```

The function:

```python
clean_html_text()
```

produces:

```text
NASA is testing a new system.
```

The cleaner also:

* Removes HTML tags
* Removes script content
* Removes style content
* Converts HTML entities
* Normalizes repeated spaces

---

## 20. Article Field Mapping

Feed entries are converted into the standard Article model.

The mapping includes:

```text
Entry title          → Article title
Entry link           → Article URL
Entry summary        → Article description
Entry content        → Article content
Entry author         → Article author
Entry publication    → Article published time
Entry media fields   → Article image URL
Feed category        → Primary category
Feed language        → Language code
Feed publisher       → NewsSource model
```

---

## 21. Description Extraction

The provider checks these fields:

```text
summary
description
subtitle
```

The first valid value is cleaned and stored as the article description.

The description is limited to the maximum size supported by the Article
model.

---

## 22. Content Extraction

Some RSS and Atom entries include full or partial article text in a content
collection.

The provider checks:

```text
entry.content
```

It extracts the first usable value and converts it into plain text.

When feed content is unavailable, the Article content field remains empty.

---

## 23. Author Extraction

The provider checks:

```text
author
authors
```

It first uses the single author field.

When that is unavailable, it checks the structured author collection.

Author values are cleaned and limited to the Article model's accepted length.

---

## 24. Publication-Date Handling

The provider checks normalized parsed fields first:

```text
published_parsed
updated_parsed
created_parsed
```

It then checks text date fields:

```text
published
updated
created
```

Dates are converted to UTC before the Article object is created.

Entries without a valid publication date are skipped.

---

## 25. Image Extraction

The provider checks common media locations in this order:

```text
media_content
media_thumbnail
enclosures
```

Only valid HTTP or HTTPS image URLs are accepted.

Invalid or missing image URLs do not invalidate the article.

The image field remains empty when no usable image is found.

---

## 26. Query Filtering

The optional query is matched against:

```text
Title
Description
Feed content
```

Example:

```python
await provider.fetch_articles(
    query="lunar",
    max_records=10,
    timespan="30d",
)
```

The comparison is case-insensitive.

The query is applied locally after the feed is downloaded.

---

## 27. Timespan Filtering

The provider calculates:

```text
Current UTC time - requested timespan
```

This produces a cutoff date.

Articles published before the cutoff are excluded.

Example:

```text
Current time: June 25
Timespan: 7 days
Cutoff: June 18
```

Articles before June 18 are filtered out.

---

## 28. Duplicate Protection

RSS feeds sometimes include the same article more than once.

The provider tracks accepted URLs using:

```python
seen_urls
```

Flow:

```text
First occurrence of URL
        ↓
Accept article and store URL

Second occurrence of same URL
        ↓
Skip duplicate
```

Duplicate removal currently happens within one feed request.

Cross-provider duplicate detection will be added in a later processing step.

---

## 29. Invalid Entry Handling

Each feed entry is processed independently.

Example:

```text
Valid entry   → Accepted
Duplicate     → Skipped
Old entry     → Filtered
Invalid title → Skipped
Valid entry   → Accepted
```

One invalid entry does not stop the entire feed ingestion process.

The provider records counts for:

```text
Received entries
Validated articles
Skipped entries
Filtered entries
Duplicate entries
```

---

## 30. Source Model Mapping

Every RSS article receives a `NewsSource` object.

Example:

```text
Name: NASA Technology
Source type: RSS
Homepage: NASA Technology homepage
Country: US
```

The publisher country represents the location of the source, not necessarily
the countries discussed in the article.

---

## 31. Default Categories

Each feed defines a default category.

Examples:

```text
NASA Technology → Technology & AI
NASA News Releases → Science & Space
NASA JPL News → Science & Space
```

These categories provide an initial classification.

AI processing can later review or replace the category when necessary.

---

## 32. RSS Test Fixtures

The main RSS fixture is stored at:

```text
tests/fixtures/rss_feed.xml
```

It contains:

* A valid technology article
* A duplicate article URL
* A valid lunar article
* An entry with an empty title
* An old article

The malformed fixture is stored at:

```text
tests/fixtures/malformed_feed.xml
```

It contains unusable non-feed content.

---

## 33. Feed Registry Tests

The tests are stored in:

```text
tests/unit/test_feed_sources.py
```

They verify:

1. Enabled sources exist.
2. Sources can be found by ID.
3. Unknown sources are rejected.
4. Country codes are normalized.
5. Invalid source IDs are rejected.
6. Duplicate source IDs are rejected.
7. Duplicate feed URLs are rejected.

---

## 34. RSS Provider Tests

The tests are stored in:

```text
tests/unit/test_rss_provider.py
```

They verify:

1. HTML text is cleaned.
2. Timespans are converted.
3. Invalid requests are rejected.
4. RSS entries are mapped correctly.
5. Duplicate URLs are removed.
6. Old articles are filtered.
7. Invalid articles are skipped.
8. Query filtering works.
9. Per-source limits are respected.
10. Malformed feeds are rejected.
11. Injected HTTP clients are not closed by the provider.

---

## 35. Test Isolation

The tests use a fake HTTP client.

The fake client reads local XML fixture files instead of calling live external
feeds.

This provides:

* Repeatable tests
* Faster execution
* No internet dependency
* No external-service rate limits
* Predictable article dates and content

The current time is also replaced during date-filter tests so results remain
stable.

---

## 36. Current Test Count

The project currently has:

```text
Configuration tests       8
Logging tests             4
Model tests              10
HTTP client tests         5
GDELT provider tests      5
Feed-source tests         7
RSS provider tests        8
--------------------------------
Total                    47
```

Run all tests using:

```powershell
python -m pytest tests\unit -v
```

---

## 37. Current RSS Architecture

```text
Feed registry
     ↓
Select enabled feed
     ↓
RssNewsProvider
     ↓
AsyncNewsHttpClient
     ↓
RSS or Atom XML
     ↓
Feedparser
     ↓
Entry mapping
     ↓
Article validation
     ↓
Date, query, duplicate and limit filtering
     ↓
Validated Article list
```

---

## 38. Logging Integration

The RSS ingestion process logs:

* Feed source and source ID
* Requested article limit
* Requested timespan
* Feed parsing warnings
* Invalid entries
* Duplicate URLs
* Received article count
* Validated article count
* Filtered article count
* Skipped article count

Logs are written to:

```text
Terminal
logs/world_news_ai.log
```

---

## 39. Current Limitations

The following features are not yet implemented:

* Cross-provider duplicate detection
* Automatic ingestion of all enabled feeds
* Persistent raw feed storage
* PostgreSQL article storage
* Kafka publishing
* Scheduled RSS ingestion
* Article-content webpage extraction
* Feed reliability monitoring
* Feed database management
* Automatic source health checks

The current implementation processes one configured feed per provider
instance.

---

## 40. Step 6 Final Result

World News AI can now:

* Configure trusted RSS and Atom sources
* Download feeds asynchronously
* Parse multiple feed formats
* Clean HTML content
* Extract article metadata
* Normalize publication dates
* Extract article images
* Filter by query and date
* Enforce source-specific limits
* Skip invalid entries
* Remove duplicate feed URLs
* Convert feed entries into validated Article objects
* Test feed ingestion without live network calls

---

## 41. Next Step

The next major step is:

```text
Step 7 — PostgreSQL Storage Foundation
```

Step 7 will introduce:

* PostgreSQL through Docker
* SQLAlchemy
* Alembic database migrations
* Article and source database tables
* Database connection management
* Repository methods
* Database integration tests
