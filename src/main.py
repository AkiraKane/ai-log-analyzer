#!/usr/bin/env python3
"""AI Log Analyzer — analyze logs and provide root cause analysis using AI."""

import argparse
import sys
import os

from log_parser import parse_log_file, analyze_logs, filter_logs, get_error_context
from llm import analyze_logs as analyze_with_llm, check_ollama


def main():
    parser = argparse.ArgumentParser(
        description="Analyze application logs using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s app.log                        # Analyze log file
  %(prog)s app.log --level ERROR          # Filter by level
  %(prog)s app.log --keyword timeout      # Filter by keyword
  %(prog)s app.log --summary              # Summary only (no AI)
  %(prog)s app.log --output json          # Output as JSON
  tail -f app.log | %(prog)s -            # Read from stdin
        """,
    )
    parser.add_argument("file", help="Path to log file (use '-' for stdin)")
    parser.add_argument("--level", help="Filter by log level (ERROR, WARN, INFO)")
    parser.add_argument("--source", help="Filter by source/logger")
    parser.add_argument("--keyword", help="Filter by keyword")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max entries to analyze")
    parser.add_argument("--ollama-url", default="http://localhost:11434",
                        help="Ollama API URL")
    parser.add_argument("--model", default="llama3.2",
                        help="Ollama model to use")
    parser.add_argument("--output", choices=["markdown", "json"],
                        default="markdown", help="Output format")
    parser.add_argument("--summary", action="store_true",
                        help="Show summary only (no AI)")
    parser.add_argument("--context", type=int, default=5,
                        help="Context lines around errors")

    args = parser.parse_args()

    # Read input
    if args.file == "-":
        content = sys.stdin.read()
    else:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file) as f:
            content = f.read()

    # Parse logs
    entries = parse_log_file(content)
    if not entries:
        print("No log entries found.", file=sys.stderr)
        sys.exit(1)

    # Filter
    if args.level or args.source or args.keyword:
        entries = filter_logs(entries, args.level, args.source, args.keyword, args.limit)

    # Analyze
    analysis = analyze_logs(entries)

    # Show summary
    print(f"Total entries: {analysis.total_entries}")
    print(f"Errors: {analysis.error_count}")
    print(f"Warnings: {analysis.warning_count}")
    if analysis.time_range:
        print(f"Time range: {analysis.time_range}")
    if analysis.sources:
        print(f"Sources: {', '.join(analysis.sources)}")
    print()

    # Summary mode
    if args.summary:
        print(analysis.to_prompt())
        return

    # JSON output
    if args.output == "json":
        import json
        data = {
            "total_entries": analysis.total_entries,
            "error_count": analysis.error_count,
            "warning_count": analysis.warning_count,
            "time_range": analysis.time_range,
            "sources": analysis.sources,
            "unique_errors": analysis.unique_errors[:10],
            "error_patterns": dict(sorted(analysis.error_patterns.items(),
                                          key=lambda x: x[1], reverse=True)[:10]),
        }
        print(json.dumps(data, indent=2))
        return

    # Check Ollama
    if not check_ollama(args.ollama_url):
        if not os.environ.get("OPENAI_API_KEY"):
            print("Error: Neither Ollama nor OPENAI_API_KEY available.",
                  file=sys.stderr)
            print("Use --summary to see data without AI.", file=sys.stderr)
            sys.exit(1)

    # Get error context
    errors_with_context = get_error_context(entries, args.context)

    # Build prompt
    prompt = analysis.to_prompt()
    if errors_with_context:
        prompt += "\n\nErrors with context:\n"
        for i, error_info in enumerate(errors_with_context[:5]):
            error = error_info["error"]
            prompt += f"\n--- Error {i+1} ---\n"
            prompt += f"Time: {error.timestamp}\n"
            prompt += f"Message: {error.message}\n"
            if error.stack_trace:
                prompt += f"Stack trace:\n{error.stack_trace[:500]}\n"

    # Generate analysis
    print("Analyzing logs...")
    try:
        explanation = analyze_with_llm(prompt, args.ollama_url, args.model)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(explanation)


if __name__ == "__main__":
    main()
