"""Obsidian markdown output formatting."""

from kobo_md.obsidian.linker import (
    LinkedText,
    LinkSuggestion,
    auto_link_from_vault,
    insert_wikilinks,
    process_text_with_links,
    suggest_links_from_vault,
)
from kobo_md.obsidian.vault import VaultIndex, find_matching_notes, scan_vault
from kobo_md.obsidian.writer import (
    append_to_daily_note,
    get_daily_note_path,
    notebook_to_markdown,
    sanitize_filename,
    write_notebook,
)

__all__ = [
    "LinkSuggestion",
    "LinkedText",
    "VaultIndex",
    "append_to_daily_note",
    "auto_link_from_vault",
    "find_matching_notes",
    "get_daily_note_path",
    "insert_wikilinks",
    "notebook_to_markdown",
    "process_text_with_links",
    "sanitize_filename",
    "scan_vault",
    "suggest_links_from_vault",
    "write_notebook",
]
