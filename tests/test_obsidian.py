"""Tests for Obsidian vault operations."""

from pathlib import Path

from kobo_md.obsidian.linker import (
    insert_wikilinks,
    process_text_with_links,
    suggest_links_from_vault,
)
from kobo_md.obsidian.vault import VaultIndex, scan_vault
from kobo_md.obsidian.writer import (
    format_frontmatter,
    sanitize_filename,
)


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_simple_name(self) -> None:
        """Test that simple names pass through unchanged."""
        assert sanitize_filename("My Note") == "My Note"

    def test_removes_invalid_chars(self) -> None:
        """Test that invalid characters are replaced."""
        assert sanitize_filename("file/with:invalid*chars") == "file-with-invalid-chars"

    def test_strips_dots_and_spaces(self) -> None:
        """Test that leading/trailing dots and spaces are stripped."""
        assert sanitize_filename("  ..file..  ") == "file"

    def test_truncates_long_names(self) -> None:
        """Test that long names are truncated."""
        long_name = "a" * 250
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_empty_becomes_untitled(self) -> None:
        """Test that empty string becomes 'untitled'."""
        assert sanitize_filename("...") == "untitled"


class TestFormatFrontmatter:
    """Tests for YAML frontmatter formatting."""

    def test_simple_values(self) -> None:
        """Test formatting simple key-value pairs."""
        result = format_frontmatter({"title": "Test", "author": "Me"})
        assert "---" in result
        assert "title: Test" in result
        assert "author: Me" in result

    def test_list_values(self) -> None:
        """Test formatting list values."""
        result = format_frontmatter({"tags": ["a", "b", "c"]})
        assert "tags:" in result
        assert "  - a" in result
        assert "  - b" in result

    def test_skips_none_values(self) -> None:
        """Test that None values are skipped."""
        result = format_frontmatter({"title": "Test", "author": None})
        assert "title: Test" in result
        assert "author" not in result

    def test_quotes_special_chars(self) -> None:
        """Test that strings with special chars are quoted."""
        result = format_frontmatter({"title": "Test: with colon"})
        assert '"Test: with colon"' in result


class TestInsertWikilinks:
    """Tests for wikilink insertion."""

    def test_inserts_link(self) -> None:
        """Test that links are inserted correctly."""
        text = "I read Deep Work by Cal Newport."
        result = insert_wikilinks(text, ["Deep Work"])
        assert "[[Deep Work]]" in result

    def test_case_insensitive(self) -> None:
        """Test that matching is case-insensitive."""
        text = "I discussed stoicism today."
        result = insert_wikilinks(text, ["Stoicism"])
        assert "[[stoicism]]" in result or "[[Stoicism]]" in result

    def test_does_not_duplicate(self) -> None:
        """Test that already-linked terms are not re-linked."""
        text = "I read [[Deep Work]] yesterday."
        result = insert_wikilinks(text, ["Deep Work"])
        assert result.count("[[Deep Work]]") == 1

    def test_longest_first(self) -> None:
        """Test that longer matches take precedence."""
        text = "I saw San Francisco Bay."
        result = insert_wikilinks(text, ["San Francisco", "San Francisco Bay"])
        assert "[[San Francisco Bay]]" in result
        assert "[[San Francisco]] Bay" not in result


class TestScanVault:
    """Tests for vault scanning."""

    def test_scan_empty_vault(self, tmp_path: Path) -> None:
        """Test scanning an empty vault."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        index = scan_vault(vault_path)
        assert index.note_titles == []
        assert index.tags == []

    def test_scan_finds_notes(self, tmp_path: Path) -> None:
        """Test that scan finds markdown files."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Note 1.md").write_text("# Note 1\nContent")
        (vault_path / "Note 2.md").write_text("# Note 2\nContent")

        index = scan_vault(vault_path)
        assert "Note 1" in index.note_titles
        assert "Note 2" in index.note_titles

    def test_scan_finds_tags_inline(self, tmp_path: Path) -> None:
        """Test that scan finds inline tags in frontmatter."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Note.md").write_text("---\ntags: [python, coding]\n---\nContent")

        index = scan_vault(vault_path)
        assert "python" in index.tags
        assert "coding" in index.tags

    def test_scan_finds_tags_in_content(self, tmp_path: Path) -> None:
        """Test that scan finds hashtag tags in content."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Note.md").write_text("# Note\nThis is about #python and #coding")

        index = scan_vault(vault_path)
        assert "python" in index.tags
        assert "coding" in index.tags

    def test_scan_excludes_obsidian_dir(self, tmp_path: Path) -> None:
        """Test that .obsidian directory is excluded."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        obsidian_dir = vault_path / ".obsidian"
        obsidian_dir.mkdir()
        (obsidian_dir / "config.md").write_text("# Config")
        (vault_path / "Real Note.md").write_text("# Real")

        index = scan_vault(vault_path)
        assert "Real Note" in index.note_titles
        assert "config" not in index.note_titles


class TestSuggestLinksFromVault:
    """Tests for vault-based link suggestions."""

    def test_suggests_matching_notes(self) -> None:
        """Test that matching note titles are suggested."""
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            note_titles=["Python", "Machine Learning", "Deep Learning"],
            tags=[],
            aliases={},
        )
        text = "I learned about Python and Machine Learning today."
        suggestions = suggest_links_from_vault(text, vault_index)

        targets = [s.target for s in suggestions]
        assert "Python" in targets
        assert "Machine Learning" in targets

    def test_respects_min_word_length(self) -> None:
        """Test that short terms are ignored."""
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            note_titles=["AI", "Python"],
            tags=[],
            aliases={},
        )
        text = "AI and Python are related."
        suggestions = suggest_links_from_vault(text, vault_index, min_word_length=3)

        targets = [s.target for s in suggestions]
        assert "AI" not in targets  # Too short
        assert "Python" in targets


class TestProcessTextWithLinks:
    """Tests for full text processing with links."""

    def test_processes_and_inserts(self) -> None:
        """Test full processing pipeline."""
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            note_titles=["Stoicism", "Marcus Aurelius"],
            tags=[],
            aliases={},
        )
        suggested_links = ["Stoicism", "Marcus Aurelius", "New Concept"]
        text = "I studied Stoicism and Marcus Aurelius."

        result = process_text_with_links(text, suggested_links, vault_index)

        assert "[[Stoicism]]" in result.linked_text
        assert "[[Marcus Aurelius]]" in result.linked_text
        assert "Stoicism" in result.existing_links
        assert "New Concept" in result.new_links
