"""Tests for log parser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from log_parser import parse_log_file, analyze_logs, filter_logs, LogEntry, LogAnalysis


class TestLogEntry:
    def test_is_error(self):
        entry = LogEntry(level="ERROR", message="test")
        assert entry.is_error

    def test_is_warning(self):
        entry = LogEntry(level="WARN", message="test")
        assert entry.is_warning

    def test_not_error(self):
        entry = LogEntry(level="INFO", message="test")
        assert not entry.is_error


class TestParseLogFile:
    def test_empty(self):
        entries = parse_log_file("")
        assert entries == []

    def test_json_logs(self):
        content = '{"timestamp":"2024-01-15T10:00:00Z","level":"ERROR","message":"Connection failed"}'
        entries = parse_log_file(content)
        assert len(entries) == 1
        assert entries[0].level == "ERROR"
        assert entries[0].message == "Connection failed"

    def test_text_logs(self):
        content = """2024-01-15 10:00:00 INFO Application started
2024-01-15 10:01:00 ERROR Database connection failed
2024-01-15 10:02:00 WARN Retry attempt 1"""
        entries = parse_log_file(content)
        assert len(entries) == 3
        assert entries[1].level == "ERROR"

    def test_bracket_format(self):
        content = "[2024-01-15T10:00:00] [ERROR] Something went wrong"
        entries = parse_log_file(content)
        assert len(entries) == 1
        assert entries[0].level == "ERROR"


class TestAnalyzeLogs:
    def test_empty(self):
        analysis = analyze_logs([])
        assert analysis.total_entries == 0
        assert analysis.error_count == 0

    def test_with_entries(self):
        entries = [
            LogEntry(level="INFO", message="Started"),
            LogEntry(level="ERROR", message="Connection failed"),
            LogEntry(level="ERROR", message="Connection failed"),
            LogEntry(level="WARN", message="Retry"),
        ]
        analysis = analyze_logs(entries)
        assert analysis.total_entries == 4
        assert analysis.error_count == 2
        assert analysis.warning_count == 1

    def test_unique_errors(self):
        entries = [
            LogEntry(level="ERROR", message="Error A"),
            LogEntry(level="ERROR", message="Error A"),
            LogEntry(level="ERROR", message="Error B"),
        ]
        analysis = analyze_logs(entries)
        assert len(analysis.unique_errors) == 2


class TestFilterLogs:
    def test_by_level(self):
        entries = [
            LogEntry(level="INFO", message="info"),
            LogEntry(level="ERROR", message="error"),
            LogEntry(level="WARN", message="warn"),
        ]
        filtered = filter_logs(entries, level="ERROR")
        assert len(filtered) == 1
        assert filtered[0].level == "ERROR"

    def test_by_keyword(self):
        entries = [
            LogEntry(level="INFO", message="connection timeout"),
            LogEntry(level="INFO", message="server started"),
        ]
        filtered = filter_logs(entries, keyword="timeout")
        assert len(filtered) == 1
        assert "timeout" in filtered[0].message

    def test_by_source(self):
        entries = [
            LogEntry(level="INFO", message="test", source="app.main"),
            LogEntry(level="INFO", message="test", source="db.pool"),
        ]
        filtered = filter_logs(entries, source="app")
        assert len(filtered) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
