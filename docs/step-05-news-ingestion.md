# Step 5 — News Ingestion Foundation

## 1. Objective

The objective of Step 5 was to create the foundation required to collect news
articles from external sources.

This step introduced:

* Asynchronous HTTP requests
* HTTP connection reuse
* Request timeouts
* Automatic retries
* Project-specific ingestion exceptions
* A standard news-provider interface
* The first live provider using GDELT
* Conversion of provider results into validated Article models
* Automated tests using mocked responses

---

## 2. Why a News Ingestion Layer Is Required

World News AI will collect articles from several sources, including:

* GDELT
* RSS feeds
* News APIs
* Government publications
* Health organizations
* Energy organizations
* Defence and international-relations sources

Every source returns information in a different structure.

The ingestion layer provides one common flow:

```text
External news source
        ↓
Provider-specific request
        ↓
HTTP client
        ↓
Raw JSON or text response
        ↓
Provider mapping
        ↓
Validated Article models
```

The rest of the application receives standard `Article` objects instead of
handling every provider's response format separately.

---

## 3. Work Completed

Step 5 completed the following work:

1. Installed HTTPX.
2. Installed Tenacity.
3. Added HTTP-client configuration settings.
4. Added validation for HTTP settings.
5. Created ingestion-specific exceptions.
6. Created a reusable asynchronous HTTP client.
7. Added request timeouts.
8. Added connection pooling.
9. Added connection keep-alive settings.
10. Added configurable retry behavior.
11. Added exponential retry delays.
12. Added HTTP status handling.
13. Added JSON decoding.
14. Added text-response handling.
15. Added HTTP request logging.
16. Created the common `NewsProvider` interface.
17. Created the GDELT search-request model.
18. Created the GDELT provider.
19. Added GDELT response validation.
20. Added GDELT-to-Article mapping.
21. Added publisher-country conversion.
22. Added language-code conversion.
23. Added invalid-article skipping.
24. Added HTTP client tests.
25. Added GDELT provider tests.
26. Added realistic GDELT fixture data.
27. Expanded configuration tests.

---

## 4. Dependencies Added

The following packages were added to `requirements.txt`:

```text
httpx
tenacity
```

### HTTPX

HTTPX is used to send HTTP requests.

The project uses its asynchronous client:

```python
httpx.AsyncClient
```

This allows the application to collect news from multiple providers without
blocking the entire process while waiting for one server.

### Tenacity

Tenacity provides retry behavior.

It allows the HTTP client to retry temporary failures such as:

* Connection errors
* Network failures
* Read timeouts
* Temporary service interruptions

---

## 5. HTTP Configuration

The following values were added to `.env.example` and the private `.env` file:

```env
HTTP_TIMEOUT_SECONDS=20
HTTP_MAX_CONNECTIONS=20
HTTP_MAX_KEEPALIVE_CONNECTIONS=10
HTTP_RETRY_ATTEMPTS=3
HTTP_RETRY_MIN_WAIT_SECONDS=1
HTTP_RETRY_MAX_WAIT_SECONDS=5
HTTP_USER_AGENT=World-News-AI/0.1
```

### Timeout

```text
HTTP_TIMEOUT_SECONDS
```

Controls how long the application waits before treating a request as failed.

### Maximum connections

```text
HTTP_MAX_CONNECTIONS
```

Limits the total number of open HTTP connections.

### Keep-alive connections

```text
HTTP_MAX_KEEPALIVE_CONNECTIONS
```

Controls how many connections remain open for reuse.

Reusing a connection is faster than opening a new connection for every
article request.

### Retry attempts

```text
HTTP_RETRY_ATTEMPTS
```

Controls the total number of request attempts.

### Retry waiting period

```text
HTTP_RETRY_MIN_WAIT_SECONDS
HTTP_RETRY_MAX_WAIT_SECONDS
```

Control the minimum and maximum waiting period between retries.

### User agent

```text
HTTP_USER_AGENT
```

Identifies the application when sending requests to external servers.

---

## 6. HTTP Configuration Validation

The centralized Settings class now validates relationships between HTTP
values.

The following configuration is invalid:

```env
HTTP_MAX_CONNECTIONS=5
HTTP_MAX_KEEPALIVE_CONNECTIONS=10
```

Keep-alive connections cannot exceed the total number of connections.

The following configuration is also invalid:

```env
HTTP_RETRY_MIN_WAIT_SECONDS=10
HTTP_RETRY_MAX_WAIT_SECONDS=2
```

The minimum retry delay cannot be greater than the maximum retry delay.

These errors are detected before the ingestion process starts.

---

## 7. Ingestion Exceptions

The following project-specific exceptions were created:

```text
NewsIngestionError
HttpRequestFailedError
HttpResponseStatusError
HttpResponseDecodeError
NewsProviderResponseError
```

### `NewsIngestionError`

Base exception for ingestion failures.

### `HttpRequestFailedError`

Raised when network or timeout failures continue after all retries.

### `HttpResponseStatusError`

Raised when a server returns an unsuccessful HTTP status, such as:

```text
404
500
503
```

### `HttpResponseDecodeError`

Raised when the response is expected to contain JSON but cannot be decoded.

### `NewsProviderResponseError`

Raised when a provider returns JSON in an unexpected structure.

Using project-specific exceptions prevents HTTPX-specific errors from
spreading throughout the application.

---

## 8. Asynchronous HTTP Client

The HTTP client is located at:

```text
src/ingestion/http_client.py
```

The main class is:

```python
AsyncNewsHttpClient
```

It provides three main methods:

```text
get_response()
get_json()
get_text()
```

### `get_response`

Sends a GET request and returns the complete HTTP response.

It performs:

* Logging
* Timeout handling
* Retry handling
* Status-code validation

### `get_json`

Sends a GET request and returns decoded JSON data.

The accepted top-level result is:

```text
Dictionary
or
List
```

Invalid JSON raises `HttpResponseDecodeError`.

### `get_text`

Sends a GET request and returns the response body as text.

This method will later be useful for RSS and XML feeds.

---

## 9. Asynchronous Context Management

The HTTP client supports:

```python
async with AsyncNewsHttpClient() as client:
    ...
```

When the block finishes, network resources are closed automatically.

This prevents:

* Open connections remaining in memory
* Resource warnings
* Connection leaks
* Unnecessary network usage

---

## 10. Connection Pooling

The project creates one reusable `AsyncClient`.

Instead of:

```text
Request 1 → Open connection → Close connection
Request 2 → Open connection → Close connection
Request 3 → Open connection → Close connection
```

the application can use:

```text
Open connection
      ↓
Request 1
Request 2
Request 3
      ↓
Close connection
```

This improves ingestion performance.

---

## 11. Retry Flow

The request flow is:

```text
Send request
     ↓
Successful?
 ├── Yes → Return response
 └── No
       ↓
Timeout or network error?
 ├── Yes → Wait and retry
 └── No  → Raise project exception
```

The waiting period grows between attempts using exponential retry behavior.

HTTP status errors such as `404` are not retried automatically because they
normally indicate a request or resource problem rather than a temporary
network failure.

---

## 12. News Provider Interface

The common provider interface is located at:

```text
src/ingestion/providers/base.py
```

The main abstract class is:

```python
NewsProvider
```

Every provider must implement:

```text
provider_name
fetch_articles()
close()
```

This provides one standard interface for all future sources.

Example:

```python
articles = await provider.fetch_articles(
    query="renewable energy",
    max_records=25,
    timespan="24h",
)
```

The application does not need different calling logic for every provider.

---

## 13. GDELT Provider

The GDELT implementation is located at:

```text
src/ingestion/providers/gdelt.py
```

The main class is:

```python
GdeltNewsProvider
```

Its responsibilities include:

* Validating search input
* Building GDELT request parameters
* Sending the request
* Validating the response structure
* Reading the article list
* Mapping each article
* Skipping invalid records
* Returning validated Article objects
* Logging ingestion statistics

---

## 14. GDELT Search Model

The search options are validated using:

```python
GdeltSearchRequest
```

Fields include:

```text
query
max_records
timespan
```

### Query

The search query must contain at least three characters.

### Maximum records

The accepted range is:

```text
1 to 250
```

### Timespan

Examples include:

```text
15min
24h
7d
2weeks
1month
```

Minute-based requests must cover at least 15 minutes.

---

## 15. GDELT Request Parameters

The provider sends:

```text
query
mode=artlist
maxrecords
timespan
sort=datedesc
format=json
```

### Article-list mode

```text
mode=artlist
```

Requests article records rather than charts or timeline results.

### Date sorting

```text
sort=datedesc
```

Requests newer articles first.

### JSON format

```text
format=json
```

Makes the response suitable for Python processing.

---

## 16. GDELT Response Validation

The provider expects a structure similar to:

```json
{
  "articles": [
    {
      "url": "...",
      "title": "...",
      "seendate": "..."
    }
  ]
}
```

The provider rejects responses when:

* The top-level value is not an object
* The `articles` field is missing
* The `articles` field is not a list

Items inside the list that are not JSON objects are skipped.

---

## 17. Article Mapping

Each valid GDELT record is converted into the project's `Article` model.

Mapping includes:

```text
GDELT title          → Article title
GDELT URL            → Article URL
GDELT social image   → Article image URL
GDELT domain         → Source name
GDELT source country → Source country code
GDELT language       → Language code
GDELT seen date      → Published date
```

The initial category is:

```text
General
```

AI classification will assign a more specific category later.

---

## 18. Publisher Country and Topic Country

GDELT's `sourcecountry` represents the publisher's country.

It is stored in:

```text
article.source.country_code
```

It is not stored in:

```text
article.country_codes
```

Example:

```text
Publisher: United Kingdom
Article topic: India and France
```

Stored result:

```text
Source country: GB
Topic countries: added later through entity extraction
```

This distinction prevents publisher location from being incorrectly treated as
the subject of the article.

---

## 19. Language Mapping

The provider converts language names into standard codes.

Examples:

```text
English → en
French  → fr
Hindi   → hi
```

When a language cannot be mapped, the provider uses:

```text
und
```

This means:

```text
Undetermined language
```

---

## 20. Invalid Article Handling

The provider processes each result separately.

When one article is invalid:

```text
Valid article 1 → Saved
Valid article 2 → Saved
Invalid article → Skipped
Valid article 3 → Saved
```

The entire ingestion job does not fail because of one bad record.

The system logs:

```text
Received article count
Validated article count
Skipped article count
```

---

## 21. Test Fixtures

A realistic GDELT response is stored at:

```text
tests/fixtures/gdelt_response.json
```

The fixture contains:

* Valid articles
* An invalid optional image URL
* An article with an empty required URL
* A non-object result

This allows the ingestion logic to be tested without calling the live GDELT
service.

---

## 22. HTTP Client Tests

The HTTP client tests are stored in:

```text
tests/unit/test_http_client.py
```

They verify:

1. Successful JSON decoding
2. HTTP status-error conversion
3. Invalid JSON handling
4. Successful retry after temporary timeout
5. Failure after all retries are exhausted

The tests use:

```python
httpx.MockTransport
```

This creates controlled local responses.

---

## 23. GDELT Provider Tests

The GDELT tests are stored in:

```text
tests/unit/test_gdelt_provider.py
```

They verify:

1. Valid search settings
2. Invalid search settings
3. Article mapping
4. Invalid article skipping
5. Invalid image handling
6. Request-parameter construction
7. Non-object response rejection
8. Missing article-list rejection

A fake HTTP client is used so no live network request is required.

---

## 24. Updated Test Count

The project now contains:

```text
Configuration tests       8
Logging tests             4
Model tests              10
HTTP client tests         5
GDELT provider tests      5
--------------------------------
Total                    32
```

Run all tests with:

```powershell
python -m pytest tests\unit -v
```

---

## 25. Current Ingestion Architecture

```text
Search request
      ↓
GdeltSearchRequest validation
      ↓
GdeltNewsProvider
      ↓
AsyncNewsHttpClient
      ↓
GDELT API
      ↓
JSON response
      ↓
Response structure validation
      ↓
Article mapping
      ↓
Pydantic Article validation
      ↓
List of validated Article objects
```

---

## 26. Logging Integration

The ingestion layer logs:

* Request attempts
* Successful responses
* HTTP status failures
* Retry attempts
* JSON decoding failures
* Invalid articles
* Invalid image URLs
* Unknown countries
* Unknown languages
* Received and validated article counts

The logs are written to:

```text
Terminal
logs/world_news_ai.log
```

---

## 27. Current Limitations

The following work has not yet been completed:

* RSS feed provider
* Additional news APIs
* Persistent raw article storage
* Content-hash generation
* Duplicate detection
* Kafka publishing
* Database storage
* Article classification
* Article summarization
* Scheduled ingestion
* Full article-content extraction

The current step creates the foundation required for these future features.

---

## 28. Step 5 Final Result

World News AI can now:

* Send asynchronous news requests
* Reuse connections
* Apply timeouts
* Retry temporary failures
* Convert technical failures into project exceptions
* Use a standard provider interface
* Search live GDELT news
* Convert GDELT records into Article models
* Skip invalid results safely
* Test ingestion without external network dependencies

---

## 29. Next Step

The next major step is:

```text
Step 6 — RSS News Provider
```

Step 6 will introduce:

* RSS and Atom feed parsing
* Multiple trusted news-source feeds
* Feed-source configuration
* RSS article mapping
* Duplicate feed-entry prevention
* RSS fixtures and automated tests
