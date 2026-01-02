"""Unified text processor combining LLM, vault scanning, and linking."""

from pathlib import Path

from pydantic import BaseModel

from kobo_md.kobo.models import Notebook, NotebookPage
from kobo_md.obsidian.linker import LinkedText, insert_wikilinks, process_text_with_links
from kobo_md.obsidian.vault import VaultIndex, scan_vault
from kobo_md.processor.llm import LLMProvider, ProcessedText, get_llm_provider


class ProcessingResult(BaseModel):
    """Result of notebook processing."""

    original_text: str
    processed_text: str
    wikilinks: list[str]
    new_wikilinks: list[str]  # Links to notes that don't exist
    existing_wikilinks: list[str]  # Links to existing notes
    tags: list[str]
    ai_processed: bool = False


class NotebookProcessor:
    """Processor for notebook content with optional AI enhancement."""

    def __init__(
        self,
        vault_path: Path | None = None,
        ai_enabled: bool = False,
        ai_provider: str = "anthropic",
        ai_model: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the processor.

        Args:
            vault_path: Path to Obsidian vault for link suggestions.
            ai_enabled: Whether to use AI for processing.
            ai_provider: AI provider ("anthropic" or "openai").
            ai_model: Model to use (uses default if None).
            api_key: API key (uses env var if None).
        """
        self.vault_path = vault_path
        self.ai_enabled = ai_enabled
        self._vault_index: VaultIndex | None = None
        self._llm: LLMProvider | None = None

        if ai_enabled:
            self._llm = get_llm_provider(
                provider=ai_provider,
                api_key=api_key,
                model=ai_model,
            )

    @property
    def vault_index(self) -> VaultIndex | None:
        """Get or build the vault index."""
        if self._vault_index is None and self.vault_path:
            self._vault_index = scan_vault(self.vault_path)
        return self._vault_index

    def process_text(self, text: str) -> ProcessingResult:
        """Process a piece of text.

        Args:
            text: Raw text to process.

        Returns:
            ProcessingResult with processed content.
        """
        if self.ai_enabled and self._llm:
            return self._process_with_ai(text)
        else:
            return self._process_without_ai(text)

    def _process_with_ai(self, text: str) -> ProcessingResult:
        """Process text using AI."""
        # Get existing notes and tags for context
        existing_notes = None
        existing_tags = None

        if self.vault_index:
            existing_notes = self.vault_index.note_titles
            existing_tags = self.vault_index.tags

        # Process with LLM
        assert self._llm is not None
        llm_result: ProcessedText = self._llm.process_text(
            text=text,
            existing_notes=existing_notes,
            existing_tags=existing_tags,
        )

        # Classify wikilinks as new or existing
        new_links: list[str] = []
        existing_links: list[str] = []

        for link in llm_result.suggested_wikilinks:
            if self.vault_index and link in self.vault_index.note_titles:
                existing_links.append(link)
            else:
                new_links.append(link)

        return ProcessingResult(
            original_text=text,
            processed_text=llm_result.cleaned_text,
            wikilinks=llm_result.suggested_wikilinks,
            new_wikilinks=new_links,
            existing_wikilinks=existing_links,
            tags=llm_result.suggested_tags,
            ai_processed=True,
        )

    def _process_without_ai(self, text: str) -> ProcessingResult:
        """Process text using heuristics only."""
        from kobo_md.kobo.parser import find_potential_wikilinks

        # Find potential links using heuristics
        potential_links = find_potential_wikilinks(text)

        # Match against vault if available
        linked_result: LinkedText | None = None
        if self.vault_index:
            linked_result = process_text_with_links(
                text=text,
                suggested_links=potential_links,
                vault_index=self.vault_index,
            )

        if linked_result:
            return ProcessingResult(
                original_text=text,
                processed_text=linked_result.linked_text,
                wikilinks=[s.target for s in linked_result.suggestions],
                new_wikilinks=linked_result.new_links,
                existing_wikilinks=linked_result.existing_links,
                tags=[],
                ai_processed=False,
            )
        else:
            # Just insert the heuristic links
            processed = insert_wikilinks(text, potential_links)
            return ProcessingResult(
                original_text=text,
                processed_text=processed,
                wikilinks=potential_links,
                new_wikilinks=potential_links,
                existing_wikilinks=[],
                tags=[],
                ai_processed=False,
            )

    def process_notebook(self, notebook: Notebook) -> Notebook:
        """Process an entire notebook.

        Args:
            notebook: Notebook to process.

        Returns:
            New Notebook with processed content.
        """
        processed_pages: list[NotebookPage] = []

        for page in notebook.pages:
            if page.text_content:
                result = self.process_text(page.text_content)
                processed_page = NotebookPage(
                    page_number=page.page_number,
                    html_content=page.html_content,
                    text_content=result.processed_text,
                    blocks=page.blocks,
                )
            else:
                processed_page = page

            processed_pages.append(processed_page)

        return Notebook(
            metadata=notebook.metadata,
            pages=processed_pages,
        )
