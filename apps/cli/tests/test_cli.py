"""Tests for the CLI module."""

import subprocess
import sys


def test_cli_help() -> None:
    """Verify that the CLI can be invoked and shows help."""
    result = subprocess.run(
        [sys.executable, "-m", "cortexflow_cli.main", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ETL Pipeline" in result.stdout  # noqa: S101


def test_cli_import() -> None:
    """Verify that the CLI package is importable."""
    import cortexflow_cli.main

    assert cortexflow_cli.main.main is not None  # noqa: S101
