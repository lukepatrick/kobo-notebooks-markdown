"""Pytest configuration and shared fixtures for kobo-md tests."""

# Disable Rich colors for consistent test output across environments
# MUST be set before any imports that touch Rich/Typer
import os

os.environ["NO_COLOR"] = "1"
os.environ["TERM"] = "dumb"

from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for test artifacts."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary config directory for testing configuration."""
    config_dir = tmp_path / ".config" / "kobo-md"
    config_dir.mkdir(parents=True)
    yield config_dir


@pytest.fixture
def mock_annotation_data() -> dict[str, object]:
    """Provide sample annotation data for testing."""
    return {
        "book_id": "test-book-123",
        "book_title": "Test Book Title",
        "author": "Test Author",
        "annotations": [
            {
                "id": "annot-1",
                "text": "This is a highlighted passage.",
                "note": "My note about this passage.",
                "chapter": "Chapter 1",
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "id": "annot-2",
                "text": "Another important quote from the book.",
                "note": None,
                "chapter": "Chapter 2",
                "created_at": "2024-01-16T14:45:00Z",
            },
        ],
    }
