#!/usr/bin/env python3
"""
Development script for code quality checks.
Usage:
  python lint.py check    # Run Ruff checks
  python lint.py fix      # Auto-fix issues and format
  python lint.py format   # Format code only

Configuration:
  - Line length: 100 characters
  - Single linter: Ruff (replaces flake8, black, isort)
  - Auto-formatting enabled
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run command and return exit code."""
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode


def check() -> int:
    """Run Ruff checks only."""
    print("Running Ruff checks...")
    cmd = ["uvx", "ruff", "check", ".", "--statistics"]
    return run_command(cmd)


def fix() -> int:
    """Auto-fix issues and format code."""
    print("Auto-fixing Ruff issues...")
    exit_code = run_command(["uvx", "ruff", "check", ".", "--fix"])

    print("Formatting code...")
    format_code = run_command(["uvx", "ruff", "format", "."])

    return max(exit_code, format_code)


def format_code() -> int:
    """Format code only."""
    print("Formatting code...")
    return run_command(["uvx", "ruff", "format", "."])


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1]

    if command == "check":
        return check()
    elif command == "fix":
        return fix()
    elif command == "format":
        return format_code()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
