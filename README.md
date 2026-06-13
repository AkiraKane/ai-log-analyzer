# AI Log Analyzer 📊🤖

A CLI tool that analyzes application logs and uses AI to provide root cause analysis and suggested fixes. Supports JSON and text log formats.

## What It Does

1. **Parses** log files (JSON and text formats)
2. **Analyzes** error patterns and frequencies
3. **Explains** root causes using AI (Ollama)
4. **Suggests** specific fixes

## Quick Start

```bash
# Analyze log file
python src/main.py app.log

# Filter by level
python src/main.py app.log --level ERROR

# Filter by keyword
python src/main.py app.log --keyword timeout

# Summary only (no AI)
python src/main.py app.log --summary

# Output as JSON
python src/main.py app.log --output json

# Read from stdin
tail -f app.log | python src/main.py -
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Log File      │────▶│   Log Parser    │────▶│   LLM Client    │
│   (JSON/text)   │     │  (structured)   │     │   (Ollama)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                         │
                              ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  LogAnalysis    │────▶│   Root Cause    │
                        │  (summary)      │     │   Analysis      │
                        └─────────────────┘     └─────────────────┘
```

## Example

Input `app.log`:
```
2024-01-15 10:00:00 INFO Application started
2024-01-15 10:01:00 INFO Connected to database
2024-01-15 10:02:00 ERROR Connection timeout to redis:6379
2024-01-15 10:02:01 WARN Retrying connection...
2024-01-15 10:02:05 ERROR Connection timeout to redis:6379
2024-01-15 10:02:06 WARN Retrying connection...
2024-01-15 10:02:10 ERROR Connection timeout to redis:6379
2024-01-15 10:02:10 FATAL Max retries exceeded, shutting down
```

Output:
```
Total entries: 8
Errors: 4
Warnings: 2

## Summary
The application is failing to connect to Redis, causing a cascade of
retries that ultimately leads to a fatal shutdown.

## Root Cause
The Redis server at redis:6379 is unreachable. This could be due to:
- Redis pod not running
- Network policy blocking connection
- Wrong Redis hostname/port

## Suggested Fixes

1. Check if Redis is running:
   ```bash
   kubectl get pods -l app=redis
   ```

2. Test connectivity:
   ```bash
   kubectl exec -it app-pod -- redis-cli -h redis ping
   ```

3. Check network policies:
   ```bash
   kubectl get networkpolicies
   ```

## Prevention
- Add health checks for Redis dependency
- Use init containers to wait for dependencies
- Implement circuit breaker pattern
```

## Supported Log Formats

- **JSON**: `{"timestamp":"...", "level":"ERROR", "message":"..."}`
- **Text**: `2024-01-15 10:00:00 ERROR message`
- **Bracket**: `[2024-01-15T10:00:00] [ERROR] message`

## Requirements

- Python 3.11+
- Ollama running locally (or OPENAI_API_KEY)

## Installation

```bash
git clone https://github.com/AkiraKane/ai-log-analyzer.git
cd ai-log-analyzer
```

## Docker

```bash
docker build -t ai-log-analyzer .
docker run -v $(pwd):/app/input ai-log-analyzer
```

## Interview Talking Points

- **Log Analysis Automation**: Automates tedious log review
- **Root Cause Analysis**: Uses AI to identify issues quickly
- **Multiple Formats**: Supports various log formats
- **CI/CD Integration**: Can run in pipeline to catch issues

## License

MIT
