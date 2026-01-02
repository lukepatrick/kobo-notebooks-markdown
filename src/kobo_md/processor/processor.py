"""Unified text processor combining LLM, vault scanning, and linking.

This module provides the main processing pipeline for notebook content.
It orchestrates multiple components to transform raw notebook text into
enhanced markdown with wikilinks and tags.

Processing modes:
1. AI-enhanced (default when enabled): Uses LLM to clean text, suggest
   contextually appropriate wikilinks, and recommend tags
2. Heuristic-only: Uses pattern matching to find potential links without
   AI processing - faster and free, but less accurate

The processor integrates with:
- Obsidian vault scanning for existing note/tag discovery
- LLM providers (Anthropic/OpenAI) for intelligent suggestions
- Wikilink insertion for proper Obsidian formatting

Usage:
    processor = NotebookProcessor(
        vault_path=Path("~/vault"),
        ai_enabled=True,
        ai_provider="anthropic",
    )
    result = processor.process_text("Some notebook content...")
"""

from pathlib import Path

from pydantic import BaseModel

from kobo_md.kobo.models import Notebook, NotebookPage
from kobo_md.obsidian.linker import LinkedText, insert_wikilinks, process_text_with_links
from kobo_md.obsidian.vault import VaultIndex, scan_vault
from kobo_md.processor.llm import LLMProvider, ProcessedText, get_llm_provider


class ProcessingResult(BaseModel):
    """Result of notebook text processing.

    Contains both the processed output and metadata about what was
    changed. This enables downstream code to:
    - Display the enhanced text to users
    - Show which links will create new notes vs link to existing ones
    - Apply suggested tags to the output markdown

    Attributes:
        original_text: The input text before any processing.
        processed_text: Text with [[wikilinks]] inserted.
        wikilinks: All wikilink targets (combined new + existing).
        new_wikilinks: Links pointing to notes that don't exist yet.
            Users may want to create these notes or review the suggestions.
        existing_wikilinks: Links pointing to notes already in the vault.
        tags: Suggested tags for the content (AI-generated or empty).
        ai_processed: Whether AI was used (affects confidence in results).
    """

    original_text: str
    processed_text: str
    wikilinks: list[str]
    new_wikilinks: list[str]
    existing_wikilinks: list[str]
    tags: list[str]
    ai_processed: bool = False


class NotebookProcessor:
    """Processor for notebook content with optional AI enhancement.

    The processor can operate in two modes:
    1. AI mode: Uses LLM to clean handwriting artifacts, suggest
       contextually relevant wikilinks, and recommend tags
    2. Heuristic mode: Uses pattern matching for basic link detection

    The processor optionally integrates with an Obsidian vault to:
    - Provide context to the LLM about existing notes/tags
    - Classify suggested links as new vs existing
    - Enable smarter link suggestions that match vault contents

    The vault index is lazily loaded on first access to avoid
    unnecessary I/O when processing without vault integration.
    """

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
                If None, link suggestions won't be matched against
                existing notes.
            ai_enabled: Whether to use AI for processing. Requires
                valid API credentials for the chosen provider.
            ai_provider: AI provider name ("anthropic" or "openai").
            ai_model: Model to use. If None, uses the provider's default
                (claude-sonnet-4-20250514 for Anthropic, gpt-4o-mini for OpenAI).
            api_key: API key for the LLM provider. If None, reads from
                environment (ANTHROPIC_API_KEY or OPENAI_API_KEY).
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
        """Get or build the vault index (lazy loading).

        The index is built on first access and cached for subsequent calls.
        This avoids scanning the vault when it's not needed.

        Returns:
            VaultIndex if vault_path was provided, None otherwise.
        """
        if self._vault_index is None and self.vault_path:
            self._vault_index = scan_vault(self.vault_path)
        return self._vault_index

    def process_text(self, text: str) -> ProcessingResult:
        """Process a piece of text, adding wikilinks and optionally tags.

        This is the main entry point for text processing. The method
        routes to either AI-based or heuristic-based processing
        depending on configuration.

        Args:
            text: Raw text content to process (e.g., from a notebook page).

        Returns:
            ProcessingResult containing the enhanced text and metadata
            about what links and tags were suggested.
        """
        if self.ai_enabled and self._llm:
            return self._process_with_ai(text)
        else:
            return self._process_without_ai(text)

    def _process_with_ai(self, text: str) -> ProcessingResult:
        """Process text using AI for intelligent enhancement.

        The AI processing pipeline:
        1. Provide vault context (existing notes/tags) to help the LLM
           make relevant suggestions that integrate with the vault
        2. Send text to LLM for cleaning and link/tag suggestion
        3. Classify each suggested link as new or existing
        4. Package results with full metadata

        The LLM receives context about existing notes so it can:
        - Suggest links to notes that already exist
        - Use consistent naming with existing content
        - Avoid suggesting redundant new notes
        """
        # Gather vault context to inform the LLM's suggestions
        existing_notes = None
        existing_tags = None

        if self.vault_index:
            existing_notes = self.vault_index.note_titles
            existing_tags = self.vault_index.tags

        # Send to LLM for processing - the LLM cleans the text,
        # suggests wikilinks, and recommends tags
        assert self._llm is not None
        llm_result: ProcessedText = self._llm.process_text(
            text=text,
            existing_notes=existing_notes,
            existing_tags=existing_tags,
        )

        # Classify each suggested wikilink as new or existing
        # This helps users understand which links will create new notes
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
        """Process text using pattern-based heuristics (no AI).

        This fallback mode uses regex patterns to identify potential
        wikilink candidates. It's faster and free but less accurate
        than AI-based processing.

        Heuristics used:
        - Multi-word capitalized phrases (proper nouns, titles)
        - Quoted text (often titles or special terms)
        - Author attributions after "by"

        If a vault is configured, the heuristic suggestions are matched
        against existing notes to classify as new vs existing.
        """
        from kobo_md.kobo.parser import find_potential_wikilinks

        # Use regex patterns to find potential link candidates
        potential_links = find_potential_wikilinks(text)

        # If we have vault access, match suggestions against existing notes
        # This provides the same new/existing classification as AI mode
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
                tags=[],  # No tags without AI
                ai_processed=False,
            )
        else:
            # No vault - just insert links without classification
            # All links are treated as "new" since we can't verify
            processed = insert_wikilinks(text, potential_links)
            return ProcessingResult(
                original_text=text,
                processed_text=processed,
                wikilinks=potential_links,
                new_wikilinks=potential_links,  # All unknown = new
                existing_wikilinks=[],
                tags=[],
                ai_processed=False,
            )

    def process_notebook(self, notebook: Notebook) -> Notebook:
        """Process all pages in a notebook.

        Iterates through each page, processes the text content, and
        returns a new Notebook with enhanced content. Empty pages
        are passed through unchanged.

        The original notebook is not modified - a new instance is
        returned with processed pages.

        Args:
            notebook: Notebook to process (from Kobo API).

        Returns:
            New Notebook instance with [[wikilinks]] inserted in
            each page's text_content. Metadata is preserved unchanged.
        """
        processed_pages: list[NotebookPage] = []

        for page in notebook.pages:
            if page.text_content:
                # Process non-empty pages to add wikilinks
                result = self.process_text(page.text_content)
                processed_page = NotebookPage(
                    page_number=page.page_number,
                    html_content=page.html_content,  # Preserve original HTML
                    text_content=result.processed_text,
                    blocks=page.blocks,
                )
            else:
                # Pass through empty pages unchanged
                processed_page = page

            processed_pages.append(processed_page)

        return Notebook(
            metadata=notebook.metadata,
            pages=processed_pages,
        )
