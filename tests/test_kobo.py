"""Tests for Kobo API client and models."""

from datetime import datetime

from kobo_md.kobo.models import ContentType, Notebook, NotebookMetadata, NotebookPage
from kobo_md.kobo.parser import find_potential_wikilinks


class TestNotebookModels:
    """Tests for Kobo data models."""

    def test_notebook_page_text_content(self) -> None:
        """Test that page text_content is available."""
        page = NotebookPage(
            page_number=0,
            html_content="<p>Hello world</p>",
            text_content="Hello world",
            blocks=[],
        )
        assert page.text_content == "Hello world"

    def test_notebook_metadata_is_advanced(self) -> None:
        """Test is_advanced property."""
        metadata = NotebookMetadata(
            id="test-id",
            display_name="Test Notebook",
            last_modified_utc=datetime.now(),
            etag="etag",
            file_size="1024",
            content_type=ContentType.ADVANCED.value,
            total_pages=1,
        )
        assert metadata.is_advanced is True

    def test_notebook_metadata_is_basic(self) -> None:
        """Test is_advanced is False for basic notebooks."""
        metadata = NotebookMetadata(
            id="test-id",
            display_name="Basic Notebook",
            last_modified_utc=datetime.now(),
            etag="etag",
            file_size="512",
            content_type=ContentType.BASIC.value,
            total_pages=1,
        )
        assert metadata.is_advanced is False

    def test_notebook_full_text(self) -> None:
        """Test that notebook full_text combines pages."""
        metadata = NotebookMetadata(
            id="test-id",
            display_name="Test",
            last_modified_utc=datetime.now(),
            etag="etag",
            file_size="2048",
            content_type=ContentType.ADVANCED.value,
            total_pages=2,
        )
        pages = [
            NotebookPage(page_number=0, html_content="", text_content="Page 1", blocks=[]),
            NotebookPage(page_number=1, html_content="", text_content="Page 2", blocks=[]),
        ]
        notebook = Notebook(metadata=metadata, pages=pages)
        assert "Page 1" in notebook.full_text
        assert "Page 2" in notebook.full_text


class TestFindPotentialWikilinks:
    """Tests for heuristic wikilink detection."""

    def test_finds_capitalized_names(self) -> None:
        """Test detection of proper nouns."""
        text = "I met John Smith at the conference."
        links = find_potential_wikilinks(text)
        assert "John Smith" in links

    def test_finds_quoted_titles(self) -> None:
        """Test detection of quoted titles."""
        text = 'I read "The Great Gatsby" last week.'
        links = find_potential_wikilinks(text)
        assert "The Great Gatsby" in links

    def test_ignores_common_words(self) -> None:
        """Test that common words are excluded."""
        text = "The Monday and January were busy."
        links = find_potential_wikilinks(text)
        # Should not include "The", "Monday", etc. in isolation
        assert "The" not in links
