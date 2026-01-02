"""Tests for the kobo-md CLI."""

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
    assert "Read Kobo Notebooks" in result.stdout


def test_sync_not_implemented() -> None:
    """Test that sync command shows not implemented message."""
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert "not yet implemented" in result.stdout


def test_list_books_not_implemented() -> None:
    """Test that list-books command shows not implemented message."""
    result = runner.invoke(app, ["list-books"])
    assert result.exit_code == 0
    assert "not yet implemented" in result.stdout


def test_export_not_implemented() -> None:
    """Test that export command shows not implemented message."""
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 0
    assert "not yet implemented" in result.stdout
