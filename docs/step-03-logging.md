# Step 3 — Application Logging System

## 1. Objective

The objective of Step 3 was to create a centralized logging system for the
World News AI application.

The logging system records application activity in two locations:

* The terminal
* A rotating log file

This allows developers to understand what the application is doing and
investigate errors when something fails.

---

## 2. Why Logging Is Required

The World News AI project will eventually include several services:

* News ingestion
* Apache Kafka
* PySpark processing
* AI summarization and classification
* PostgreSQL
* Redis
* Elasticsearch
* FastAPI
* Streamlit
* Apache Airflow

When one of these services fails, terminal messages alone may not be enough.

Logging provides a permanent record of events such as:

```text
Application startup
News articles collected
Invalid records detected
API request failures
Database connection errors
Kafka publishing failures
AI processing errors
Pipeline completion
```

The planned application flow is:

```text
Application action
        ↓
Create log message
        ↓
Console handler
        ├── Display in terminal
        ↓
Rotating file handler
        └── Save in log file
```

---

## 3. Work Completed

The following work was completed:

1. Added logging settings to `.env.example`.
2. Added logging settings to the private `.env` file.
3. Added logging fields to the centralized Settings class.
4. Added validation for supported log levels.
5. Created the main logging configuration module.
6. Added console logging.
7. Added rotating file logging.
8. Added automatic log-directory creation.
9. Added protection against duplicate logging handlers.
10. Created the application startup module.
11. Added application startup log messages.
12. Created automated logging tests.
13. Verified console output.
14. Verified file output.
15. Verified that all configuration and logging tests pass.

---

## 4. Files Created

### `src/common/logging_config.py`

This is the central logging module.

It is responsible for:

* Creating the application logger
* Setting the logging level
* Defining the log-message format
* Sending logs to the terminal
* Saving logs to a file
* Rotating large log files
* Preventing duplicate handlers

### `src/main.py`

This is the current application entry point.

It starts the application and records startup messages.

### `tests/unit/test_logging_config.py`

This file contains automated tests for the logging system.

### `docs/step-03-logging.md`

This file documents the complete logging implementation.

---

## 5. Files Updated

### `.env.example`

The following variables were added:

```env
LOG_LEVEL=INFO
LOG_FILE=logs/world_news_ai.log
```

### `.env`

The same local logging values were added.

The `.env` file remains private and is ignored by Git.

### `src/common/config.py`

The following settings were added:

```python
log_level
log_file
```

---

## 6. Logging Configuration Values

### `LOG_LEVEL`

Controls which messages are recorded.

Supported values are:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Example:

```env
LOG_LEVEL=INFO
```

When the level is `INFO`, the logger records:

```text
INFO
WARNING
ERROR
CRITICAL
```

It does not record `DEBUG` messages.

### `LOG_FILE`

Controls where the log file is stored.

Example:

```env
LOG_FILE=logs/world_news_ai.log
```

The final file location is:

```text
World_News_AI/logs/world_news_ai.log
```

---

## 7. Log Levels

### DEBUG

Used for detailed development information.

Example:

```python
logger.debug("Received 25 raw articles from GDELT")
```

### INFO

Used for normal application activity.

Example:

```python
logger.info("Application started successfully")
```

### WARNING

Used when something unexpected happens but the application can continue.

Example:

```python
logger.warning("Article image was missing")
```

### ERROR

Used when an operation fails.

Example:

```python
logger.error("Failed to connect to PostgreSQL")
```

### CRITICAL

Used for a serious failure that may stop the application.

Example:

```python
logger.critical("Application configuration could not be loaded")
```

---

## 8. Log Message Format

The project uses this format:

```text
Timestamp | Level | Logger name | File and line | Message
```

Example:

```text
2026-06-25 15:20:10 | INFO | World News AI |
main.py:10 | Application started successfully
```

This format helps identify:

* When the event occurred
* How serious it was
* Which logger produced it
* Which file produced it
* Which line produced it
* What happened

---

## 9. Console Logging

The console handler uses:

```python
logging.StreamHandler()
```

It displays messages in:

* PowerShell
* VS Code terminal
* Container logs
* Deployment logs

Example:

```text
INFO | World News AI | Starting World News AI
```

Console logging is useful while the application is running.

---

## 10. Rotating File Logging

The file handler uses:

```python
RotatingFileHandler
```

The main log file is:

```text
logs/world_news_ai.log
```

The maximum file size is approximately:

```text
5 MB
```

When the file reaches the maximum size, Python creates backup files:

```text
world_news_ai.log
world_news_ai.log.1
world_news_ai.log.2
world_news_ai.log.3
```

The project keeps up to five backup files.

This prevents the log file from growing without limit.

---

## 11. Automatic Directory Creation

The logging system creates the parent directory automatically:

```python
log_file_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

This means the application can create:

```text
logs/
```

when the folder does not already exist.

---

## 12. Duplicate Handler Protection

The logging module checks:

```python
if logger.handlers:
    return logger
```

Without this protection, importing the logging module repeatedly could produce
duplicate messages.

Incorrect behavior:

```text
Application started
Application started
Application started
```

Correct behavior:

```text
Application started
```

---

## 13. Application Startup Logging

The application entry point is:

```text
src/main.py
```

Run it using:

```powershell
python -m src.main
```

The application records:

```text
Starting World News AI in development environment
Configuration system loaded successfully
Logging system loaded successfully
```

These messages appear in both:

```text
Terminal
logs/world_news_ai.log
```

---

## 14. Logging Tests

The tests are located at:

```text
tests/unit/test_logging_config.py
```

The tests verify:

### Test 1: Log directory creation

Confirms that the parent directory is created automatically.

### Test 2: Handler configuration

Confirms that the logger receives:

```text
One console handler
One file handler
```

### Test 3: File output

Confirms that a log message is written to the expected file.

### Test 4: Duplicate-handler prevention

Confirms that calling the setup function multiple times does not add extra
handlers.

The tests use Pytest's temporary directory:

```python
tmp_path
```

This prevents test files from being written into the real application log
directory.

---

## 15. Running the Tests

Run all unit tests:

```powershell
python -m pytest tests\unit -v
```

Expected result:

```text
9 passed
```

The nine tests include:

```text
5 configuration tests
4 logging tests
```

---

## 16. Current Logging Flow

```text
src/main.py
    ↓
Application action
    ↓
Central logger
    ├── Console handler
    │       ↓
    │   Terminal output
    │
    └── Rotating file handler
            ↓
        logs/world_news_ai.log
```

---

## 17. Git and Security

The private `.env` file is ignored by Git.

The generated log files are also ignored because `.gitignore` contains:

```gitignore
*.log
logs/
```

Git will track:

```text
Logging source code
Logging tests
.env.example
Documentation
Architecture updates
```

Git will not track:

```text
.env
logs/world_news_ai.log
Rotated backup log files
```

---

## 18. Current Limitations

The logging system is implemented, but the application currently logs only
startup activity.

Future components will add logs for:

* News API requests
* Article collection
* Kafka messages
* PySpark jobs
* AI processing
* Database operations
* Search indexing
* Social-card generation
* API requests
* Dashboard errors

---

## 19. Step 3 Final Result

The World News AI project now has a centralized logging system that:

* Displays logs in the terminal
* Saves logs to a file
* Rotates large log files
* Supports multiple log levels
* Creates log directories automatically
* Prevents duplicate handlers
* Records application startup
* Has automated unit tests

---

## 20. Next Step

The next major step is:

```text
Step 4 — News Category and Data Model Design
```

Step 4 will define:

* Article data structure
* News categories
* Country information
* Source information
* Trending and breaking labels
* Validation rules
* Social-media card fields
