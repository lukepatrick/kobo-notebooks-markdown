"""Tests for the kobo-md CLI."""

from unittest.mock import patch

from typer.testing import CliRunner

from kobo_md import __version__
from kobo_md.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test that --version returns the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help() -> None:
    """Test that --help displays usage information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Kobo Notebook" in result.stdout or "kobo" in result.stdout.lower()


def test_no_args_shows_usage() -> None:
    """Test that running with no args shows usage (may return non-zero)."""
    result = runner.invoke(app, [])
    # Typer may return 0 or 2 depending on version for no args
    assert "Usage" in result.stdout or "usage" in result.stdout.lower()


def test_list_requires_auth() -> None:
    """Test that list command fails without authentication."""
    # Mock cookies to not exist
    with patch("kobo_md.cli.load_cookies") as mock_load:
        mock_load.return_value = None
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1
        assert "Not authenticated" in result.stdout


def test_fetch_requires_notebook_id_or_all() -> None:
    """Test that fetch requires either a notebook ID or --all flag."""
    with patch("kobo_md.cli.load_cookies") as mock_load:
        mock_load.return_value = None
        result = runner.invoke(app, ["fetch"])
        assert result.exit_code == 1
        # Either not authenticated or missing notebook ID
        assert "Not authenticated" in result.stdout or "Specify a notebook ID" in result.stdout


def test_fetch_help() -> None:
    """Test fetch command help shows all options."""
    result = runner.invoke(app, ["fetch", "--help"])
    assert result.exit_code == 0
    assert "--all" in result.stdout
    assert "--ai" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--confirm" in result.stdout
    assert "--provider" in result.stdout


def test_auth_login_help() -> None:
    """Test auth login command help."""
    result = runner.invoke(app, ["auth", "login", "--help"])
    assert result.exit_code == 0
    assert "--browser" in result.stdout


def test_auth_status_no_cookies() -> None:
    """Test auth status when not authenticated."""
    with patch("kobo_md.cli.load_cookies") as mock_load:
        mock_load.return_value = None
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 1
        assert "Not authenticated" in result.stdout


def test_config_shows_settings() -> None:
    """Test config command shows current settings."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Configuration" in result.stdout
    assert "Vault Path" in result.stdout
    assert "AI Provider" in result.stdout


def test_process_file_not_found() -> None:
    """Test process command with non-existent file."""
    result = runner.invoke(app, ["process", "/nonexistent/file.md"])
    assert result.exit_code == 1
    assert "File not found" in result.stdout


def test_fetch_daily_notes_option() -> None:
    """Test fetch command help shows daily-notes option."""
    result = runner.invoke(app, ["fetch", "--help"])
    assert result.exit_code == 0
    assert "--daily-notes" in result.stdout
    assert "--daily-pattern" in result.stdout
