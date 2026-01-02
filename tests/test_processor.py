"""Tests for the processor module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kobo_md.processor.llm import (
    ProcessedText,
    get_llm_provider,
)
from kobo_md.processor.processor import NotebookProcessor, ProcessingResult


class TestProcessedText:
    """Tests for ProcessedText model."""

    def test_create_processed_text(self) -> None:
        """Test creating a ProcessedText instance."""
        result = ProcessedText(
            cleaned_text="Clean text",
            suggested_wikilinks=["Link1", "Link2"],
            suggested_tags=["tag1", "tag2"],
            confidence=0.95,
        )
        assert result.cleaned_text == "Clean text"
        assert len(result.suggested_wikilinks) == 2
        assert len(result.suggested_tags) == 2
        assert result.confidence == 0.95


class TestGetLLMProvider:
    """Tests for provider factory function."""

    def test_invalid_provider_raises(self) -> None:
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider("invalid-provider")
        assert "Unsupported provider" in str(exc_info.value)

    def test_anthropic_requires_key(self) -> None:
        """Test that anthropic provider requires API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_llm_provider("anthropic")
            assert "API key required" in str(exc_info.value)

    def test_openai_requires_key(self) -> None:
        """Test that openai provider requires API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_llm_provider("openai")
            assert "API key required" in str(exc_info.value)


class TestNotebookProcessor:
    """Tests for NotebookProcessor."""

    def test_process_without_ai(self, tmp_path: Path) -> None:
        """Test processing without AI enabled."""
        processor = NotebookProcessor(
            vault_path=None,
            ai_enabled=False,
        )
        result = processor.process_text("Some text about [[Python]] programming.")

        assert isinstance(result, ProcessingResult)
        assert result.ai_processed is False
        assert result.original_text == "Some text about [[Python]] programming."

    def test_vault_index_lazy_loaded(self, tmp_path: Path) -> None:
        """Test that vault index is lazily loaded."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Note.md").write_text("# Note")

        processor = NotebookProcessor(vault_path=vault_path, ai_enabled=False)

        # Index not loaded yet
        assert processor._vault_index is None

        # Access triggers load
        index = processor.vault_index
        assert index is not None
        assert "Note" in index.note_titles

    def test_process_with_vault_finds_existing(self, tmp_path: Path) -> None:
        """Test that processing with vault identifies existing notes."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Python.md").write_text("# Python")
        (vault_path / "Machine Learning.md").write_text("# ML")

        processor = NotebookProcessor(vault_path=vault_path, ai_enabled=False)
        result = processor.process_text("Learning Python and Machine Learning.")

        # Should identify existing notes
        assert "Python" in result.existing_wikilinks or "Machine Learning" in result.existing_wikilinks


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_create_result(self) -> None:
        """Test creating a ProcessingResult."""
        result = ProcessingResult(
            original_text="Original",
            processed_text="Processed",
            wikilinks=["Link1"],
            new_wikilinks=["Link1"],
            existing_wikilinks=[],
            tags=["tag1"],
            ai_processed=True,
        )
        assert result.original_text == "Original"
        assert result.ai_processed is True
        assert len(result.new_wikilinks) == 1
