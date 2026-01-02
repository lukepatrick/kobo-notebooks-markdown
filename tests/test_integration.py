"""Integration tests for the kobo-md pipeline."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kobo_md.kobo.models import ContentType, Notebook, NotebookMetadata, NotebookPage
from kobo_md.obsidian import notebook_to_markdown
from kobo_md.obsidian.linker import process_text_with_links
from kobo_md.obsidian.vault import VaultIndex, scan_vault
from kobo_md.obsidian.writer import write_notebook
from kobo_md.processor.processor import NotebookProcessor, ProcessingResult


class TestEndToEndPipeline:
    """Tests for the full notebook processing pipeline."""

    def _create_test_notebook(
        self,
        notebook_id: str = "test-notebook",
        display_name: str = "Test Notebook",
        pages_content: list[str] | None = None,
    ) -> Notebook:
        """Create a test notebook with given content."""
        if pages_content is None:
            pages_content = ["This is page 1 content.", "This is page 2 content."]

        metadata = NotebookMetadata(
            id=notebook_id,
            display_name=display_name,
            file_size="1024",
            etag="test-etag",
            content_type=ContentType.ADVANCED.value,
            total_pages=len(pages_content),
            last_modified_utc=datetime.now(),
        )

        pages = [
            NotebookPage(
                page_number=i,
                html_content=f"<p>{content}</p>",
                text_content=content,
                blocks=[],
            )
            for i, content in enumerate(pages_content)
        ]

        return Notebook(metadata=metadata, pages=pages)

    def test_notebook_to_markdown_basic(self) -> None:
        """Test basic notebook to markdown conversion."""
        notebook = self._create_test_notebook()
        markdown = notebook_to_markdown(notebook)

        assert "---" in markdown  # Has frontmatter
        assert "Test Notebook" in markdown  # Has title
        assert "page 1 content" in markdown
        assert "page 2 content" in markdown

    def test_notebook_to_markdown_with_wikilinks(self) -> None:
        """Test markdown conversion with wikilinks."""
        notebook = self._create_test_notebook(
            pages_content=[
                "I read [[Deep Work]] by Cal Newport.",
                "It discusses [[focused work]] and [[deliberate practice]].",
            ]
        )
        markdown = notebook_to_markdown(notebook)

        assert "[[Deep Work]]" in markdown
        assert "[[focused work]]" in markdown
        assert "[[deliberate practice]]" in markdown

    def test_pipeline_with_vault_integration(self, tmp_path: Path) -> None:
        """Test full pipeline with vault scanning and link suggestions."""
        # Create a test vault with existing notes
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Deep Work.md").write_text("# Deep Work\nBook by Cal Newport")
        (vault_path / "Cal Newport.md").write_text("# Cal Newport\nAuthor and professor")
        (vault_path / "Productivity.md").write_text("---\ntags: [productivity, focus]\n---\n# Productivity")

        # Scan the vault
        vault_index = scan_vault(vault_path)

        assert "Deep Work" in vault_index.note_titles
        assert "Cal Newport" in vault_index.note_titles
        assert "Productivity" in vault_index.note_titles
        assert "productivity" in vault_index.tags

        # Process text with vault context
        text = "I read Deep Work by Cal Newport. Great book about productivity."
        suggested_links = ["Deep Work", "Cal Newport", "Productivity", "New Concept"]

        result = process_text_with_links(text, suggested_links, vault_index)

        # Should identify existing vs new links
        assert "Deep Work" in result.existing_links
        assert "Cal Newport" in result.existing_links
        assert "New Concept" in result.new_links

    def test_processor_without_ai(self, tmp_path: Path) -> None:
        """Test NotebookProcessor without AI processing."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Python.md").write_text("# Python")
        (vault_path / "Machine Learning.md").write_text("# Machine Learning")

        processor = NotebookProcessor(vault_path=vault_path, ai_enabled=False)

        result = processor.process_text(
            "Learning Python for Machine Learning projects."
        )

        assert isinstance(result, ProcessingResult)
        assert result.ai_processed is False
        # Should still identify existing notes from vault
        assert "Python" in result.existing_wikilinks or "Machine Learning" in result.existing_wikilinks

    def test_write_notebook_to_vault(self, tmp_path: Path) -> None:
        """Test writing notebook to vault creates correct file."""
        output_dir = tmp_path / "vault" / "Kobo Notes"
        output_dir.mkdir(parents=True)

        notebook = self._create_test_notebook(
            display_name="My Test Note",
            pages_content=["Important notes about testing."],
        )

        filepath = write_notebook(
            notebook=notebook,
            output_dir=output_dir,
        )

        assert filepath.exists()
        assert filepath.name == "My Test Note.md"
        assert filepath.parent.name == "Kobo Notes"

        content = filepath.read_text()
        assert "My Test Note" in content
        assert "Important notes about testing" in content

    def test_write_with_existing_file_raises(self, tmp_path: Path) -> None:
        """Test that writing with existing file raises without overwrite."""
        output_dir = tmp_path / "vault" / "Kobo Notes"
        output_dir.mkdir(parents=True)

        # Create existing file
        (output_dir / "Duplicate Note.md").write_text("# Existing note")

        notebook = self._create_test_notebook(
            display_name="Duplicate Note",
            pages_content=["New content."],
        )

        # Should raise FileExistsError without overwrite=True
        with pytest.raises(FileExistsError):
            write_notebook(
                notebook=notebook,
                output_dir=output_dir,
                overwrite=False,
            )

    def test_write_with_overwrite(self, tmp_path: Path) -> None:
        """Test that writing with overwrite=True replaces existing file."""
        output_dir = tmp_path / "vault" / "Kobo Notes"
        output_dir.mkdir(parents=True)

        # Create existing file
        existing_file = output_dir / "Overwrite Note.md"
        existing_file.write_text("# Old content")

        notebook = self._create_test_notebook(
            display_name="Overwrite Note",
            pages_content=["New content that should replace old."],
        )

        filepath = write_notebook(
            notebook=notebook,
            output_dir=output_dir,
            overwrite=True,
        )

        assert filepath.exists()
        content = filepath.read_text()
        assert "New content that should replace old" in content
        assert "Old content" not in content


class TestVaultSafety:
    """Tests for vault write safety features."""

    def test_output_path_validation(self, tmp_path: Path) -> None:
        """Test that output path validation works."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Valid path within vault
        output_in_vault = vault_path / "notes"
        output_in_vault.mkdir()

        from kobo_md.cli import _validate_output_path

        assert _validate_output_path(output_in_vault, vault_path) is True

        # Path outside vault
        outside_vault = tmp_path / "other"
        outside_vault.mkdir()

        assert _validate_output_path(outside_vault, vault_path) is False

    def test_sanitize_filename_prevents_traversal(self) -> None:
        """Test that filename sanitization prevents path traversal."""
        from kobo_md.obsidian.writer import sanitize_filename

        # Should sanitize path separators - this makes path traversal ineffective
        # because / and \ are replaced, so even if ".." remains, it's just part of the filename
        result = sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result

        # The result can't be used for path traversal since separators are gone
        from pathlib import Path
        # Verify it's a safe filename (no path components)
        assert Path(result).name == result  # No directory components

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """Test that dry run preview doesn't create files."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        from kobo_md.cli import _show_write_preview
        from rich.console import Console
        from io import StringIO

        notebook = NotebookMetadata(
            id="test",
            display_name="Test",
            file_size="100",
            etag="etag",
            content_type=ContentType.ADVANCED.value,
            total_pages=1,
            last_modified_utc=datetime.now(),
        )
        pages = [NotebookPage(page_number=0, html_content="", text_content="Test", blocks=[])]
        full_notebook = Notebook(metadata=notebook, pages=pages)

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        filepath = vault_path / "Test.md"

        _show_write_preview(full_notebook, filepath, console)

        # Should not create any files
        assert not filepath.exists()
        # Should show preview output
        assert len(output.getvalue()) > 0


class TestDailyNotes:
    """Tests for daily notes integration."""

    def test_get_daily_note_path(self, tmp_path: Path) -> None:
        """Test daily note path generation."""
        from datetime import datetime
        from kobo_md.obsidian.writer import get_daily_note_path

        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Test with a fixed date
        test_date = datetime(2024, 3, 15)
        path = get_daily_note_path(
            vault_path,
            "Daily/{year}/{month_name}/{day}.md",
            date=test_date,
        )

        assert path == vault_path / "Daily" / "2024" / "Mar" / "15.md"

    def test_append_to_daily_note_creates_file(self, tmp_path: Path) -> None:
        """Test that append creates file if it doesn't exist."""
        from kobo_md.obsidian.writer import append_to_daily_note
        from kobo_md.kobo.models import ContentType, Notebook, NotebookMetadata, NotebookPage
        from datetime import datetime

        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        daily_note_path = vault_path / "Daily" / "2024-03-15.md"

        metadata = NotebookMetadata(
            id="test",
            display_name="Test Note",
            file_size="100",
            etag="etag",
            content_type=ContentType.ADVANCED.value,
            total_pages=1,
            last_modified_utc=datetime.now(),
        )
        pages = [
            NotebookPage(
                page_number=0,
                html_content="",
                text_content="Important note content",
                blocks=[],
            )
        ]
        notebook = Notebook(metadata=metadata, pages=pages)

        append_to_daily_note(notebook, daily_note_path)

        assert daily_note_path.exists()
        content = daily_note_path.read_text()
        assert "Test Note" in content
        assert "Important note content" in content

    def test_append_to_daily_note_appends_to_existing(self, tmp_path: Path) -> None:
        """Test that append adds to existing file."""
        from kobo_md.obsidian.writer import append_to_daily_note
        from kobo_md.kobo.models import ContentType, Notebook, NotebookMetadata, NotebookPage
        from datetime import datetime

        vault_path = tmp_path / "vault" / "Daily"
        vault_path.mkdir(parents=True)

        daily_note_path = vault_path / "2024-03-15.md"
        daily_note_path.write_text("# Daily Note\n\nExisting content.\n")

        metadata = NotebookMetadata(
            id="test",
            display_name="New Note",
            file_size="100",
            etag="etag",
            content_type=ContentType.ADVANCED.value,
            total_pages=1,
            last_modified_utc=datetime.now(),
        )
        pages = [
            NotebookPage(
                page_number=0,
                html_content="",
                text_content="New content",
                blocks=[],
            )
        ]
        notebook = Notebook(metadata=metadata, pages=pages)

        append_to_daily_note(notebook, daily_note_path)

        content = daily_note_path.read_text()
        assert "# Daily Note" in content  # Original preserved
        assert "Existing content" in content
        assert "New Note" in content
        assert "New content" in content


class TestMarkdownFormatting:
    """Tests for markdown output formatting."""

    def test_frontmatter_format(self) -> None:
        """Test that frontmatter is properly formatted."""
        from kobo_md.obsidian.writer import format_frontmatter

        frontmatter = format_frontmatter({
            "title": "Test Note",
            "source": "Kobo",
            "tags": ["kobo", "notes"],
            "created": "2024-01-15",
        })

        assert frontmatter.startswith("---\n")
        assert frontmatter.endswith("---")  # No trailing newline
        assert "title: Test Note" in frontmatter
        assert "source: Kobo" in frontmatter
        assert "  - kobo" in frontmatter
        assert "  - notes" in frontmatter

    def test_wikilink_insertion_preserves_content(self) -> None:
        """Test that wikilink insertion doesn't corrupt content."""
        from kobo_md.obsidian.linker import insert_wikilinks

        original = "I learned about Machine Learning and Deep Learning today. Both are exciting fields."
        result = insert_wikilinks(original, ["Machine Learning", "Deep Learning"])

        # Should have wikilinks
        assert "[[Machine Learning]]" in result
        assert "[[Deep Learning]]" in result

        # Should preserve other content
        assert "today" in result
        assert "exciting fields" in result

        # Should not duplicate links
        assert result.count("[[Machine Learning]]") == 1

    def test_special_characters_in_content(self) -> None:
        """Test handling of special characters in notebook content."""
        from datetime import datetime

        metadata = NotebookMetadata(
            id="test",
            display_name="Test: Special & Characters",
            file_size="100",
            etag="etag",
            content_type=ContentType.ADVANCED.value,
            total_pages=1,
            last_modified_utc=datetime.now(),
        )
        pages = [
            NotebookPage(
                page_number=0,
                html_content="<p>Test &amp; content with <special> chars</p>",
                text_content="Test & content with <special> chars",
                blocks=[],
            )
        ]
        notebook = Notebook(metadata=metadata, pages=pages)

        markdown = notebook_to_markdown(notebook)

        # Should handle special characters appropriately
        assert "Test" in markdown
        assert "content" in markdown
