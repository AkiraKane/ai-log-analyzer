"""Parse and analyze application logs."""

import re
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: str = ""
    level: str = ""  # INFO, WARN, ERROR, DEBUG, FATAL
    message: str = ""
    source: str = ""
    stack_trace: str = ""
    raw: str = ""

    @property
    def is_error(self) -> bool:
        return self.level in ("ERROR", "FATAL", "CRITICAL")

    @property
    def is_warning(self) -> bool:
        return self.level == "WARN"


@dataclass
class LogAnalysis:
    """Analysis results for a set of logs."""
    total_entries: int = 0
    error_count: int = 0
    warning_count: int = 0
    unique_errors: list[str] = field(default_factory=list)
    error_patterns: dict[str, int] = field(default_factory=dict)
    time_range: str = ""
    sources: list[str] = field(default_factory=list)

    def to_prompt(self) -> str:
        """Convert to prompt for LLM analysis."""
        parts = [
            f"Log Analysis Summary:",
            f"Total entries: {self.total_entries}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
            f"Time range: {self.time_range}",
            f"Sources: {', '.join(self.sources) if self.sources else 'unknown'}",
            "",
        ]

        if self.unique_errors:
            parts.append("Unique Errors:")
            for error in self.unique_errors[:10]:
                parts.append(f"  - {error[:200]}")
            parts.append("")

        if self.error_patterns:
            parts.append("Error Patterns (by frequency):")
            for pattern, count in sorted(self.error_patterns.items(),
                                         key=lambda x: x[1], reverse=True)[:10]:
                parts.append(f"  [{count}x] {pattern[:100]}")

        return "\n".join(parts)


def parse_log_file(content: str) -> list[LogEntry]:
    """Parse log file content into structured entries."""
    entries = []
    current_entry = None

    for line in content.split("\n"):
        if not line.strip():
            continue

        # Try to parse as structured log (JSON)
        if line.strip().startswith("{"):
            entry = _parse_json_log(line)
            if entry:
                entries.append(entry)
                continue

        # Try to parse as common log format
        entry = _parse_text_log(line)
        if entry:
            if current_entry:
                entries.append(current_entry)
            current_entry = entry
        elif current_entry:
            # Continuation of previous entry (stack trace, etc.)
            if line.strip().startswith("at ") or line.strip().startswith("Caused by"):
                current_entry.stack_trace += line + "\n"
            else:
                current_entry.message += " " + line.strip()

    if current_entry:
        entries.append(current_entry)

    return entries


def _parse_json_log(line: str) -> Optional[LogEntry]:
    """Parse JSON-formatted log entry."""
    try:
        data = json.loads(line)
        return LogEntry(
            timestamp=data.get("timestamp", data.get("time", data.get("@timestamp", ""))),
            level=data.get("level", data.get("severity", data.get("loglevel", "INFO"))).upper(),
            message=data.get("message", data.get("msg", "")),
            source=data.get("logger", data.get("source", data.get("service", ""))),
            raw=line,
        )
    except json.JSONDecodeError:
        return None


def _parse_text_log(line: str) -> Optional[LogEntry]:
    """Parse text-formatted log entry."""
    # Common patterns
    patterns = [
        # 2024-01-15 10:30:45 ERROR message
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(ERROR|WARN|INFO|DEBUG|FATAL|CRITICAL)\s+(.*)',
        # [2024-01-15T10:30:45] [ERROR] message
        r'\[([\d\-T:\.]+)\]\s+\[(ERROR|WARN|INFO|DEBUG|FATAL|CRITICAL)\]\s+(.*)',
        # ERROR 2024-01-15 message
        r'(ERROR|WARN|INFO|DEBUG|FATAL|CRITICAL)\s+(\d{4}-\d{2}-\d{2}.*)',
        # 15/Jan/2024:10:30:45 ERROR message
        r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})\s+(ERROR|WARN|INFO|DEBUG|FATAL|CRITICAL)\s+(.*)',
    ]

    for pattern in patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                # Check if first group is timestamp or level
                if groups[1].upper() in ("ERROR", "WARN", "INFO", "DEBUG", "FATAL", "CRITICAL"):
                    return LogEntry(
                        timestamp=groups[0],
                        level=groups[1].upper(),
                        message=groups[2],
                        raw=line,
                    )
                else:
                    return LogEntry(
                        timestamp=groups[1],
                        level=groups[0].upper(),
                        message=groups[2],
                        raw=line,
                    )

    # Fallback: detect level only at the start of the line or after a timestamp
    level_match = re.match(r'^\s*(?:\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*\s+)?(?:\[[\d\-T:\.]+\]\s+)?\b(ERROR|WARN|WARNING|INFO|DEBUG|FATAL|CRITICAL)\b', line, re.IGNORECASE)
    if level_match:
        level = level_match.group(1).upper()
        if level == "WARNING":
            level = "WARN"
        return LogEntry(
            level=level,
            message=line,
            raw=line,
        )

    # Default to INFO
    return LogEntry(
        level="INFO",
        message=line,
        raw=line,
    )


def analyze_logs(entries: list[LogEntry]) -> LogAnalysis:
    """Analyze log entries and generate summary."""
    analysis = LogAnalysis(total_entries=len(entries))

    error_messages = []
    sources = set()

    for entry in entries:
        if entry.is_error:
            analysis.error_count += 1
            error_messages.append(entry.message)
        elif entry.is_warning:
            analysis.warning_count += 1

        if entry.source:
            sources.add(entry.source)

        # Extract error patterns
        if entry.is_error:
            # Normalize error message (remove numbers, paths, etc.)
            pattern = re.sub(r'\d+', 'N', entry.message)
            pattern = re.sub(r'/[\w/\.-]+', '/PATH', pattern)
            pattern = re.sub(r'0x[\da-fA-F]+', 'HEX', pattern)
            analysis.error_patterns[pattern] = analysis.error_patterns.get(pattern, 0) + 1

    analysis.sources = list(sources)

    # Deduplicate error messages
    seen = set()
    for msg in error_messages:
        normalized = msg[:100]
        if normalized not in seen:
            seen.add(normalized)
            analysis.unique_errors.append(msg)

    # Time range
    timestamps = [e.timestamp for e in entries if e.timestamp]
    if timestamps:
        analysis.time_range = f"{timestamps[0]} to {timestamps[-1]}"

    return analysis


def filter_logs(
    entries: list[LogEntry],
    level: str = "",
    source: str = "",
    keyword: str = "",
    limit: int = 100,
) -> list[LogEntry]:
    """Filter log entries."""
    filtered = entries

    if level:
        level = level.upper()
        filtered = [e for e in filtered if e.level == level]

    if source:
        filtered = [e for e in filtered if source.lower() in e.source.lower()]

    if keyword:
        keyword = keyword.lower()
        filtered = [e for e in filtered if keyword in e.message.lower()]

    return filtered[:limit]


def get_error_context(
    entries: list[LogEntry],
    context_lines: int = 5,
) -> list[dict]:
    """Get errors with surrounding context."""
    errors = []

    for i, entry in enumerate(entries):
        if entry.is_error:
            start = max(0, i - context_lines)
            end = min(len(entries), i + context_lines + 1)
            context = entries[start:end]

            errors.append({
                "error": entry,
                "context": context,
                "context_before": entries[start:i],
                "context_after": entries[i+1:end],
            })

    return errors
