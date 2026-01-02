"""Wikilink suggestion and insertion for Obsidian notes."""

import re
from pathlib import Path

from pydantic import BaseModel

from kobo_md.obsidian.vault import VaultIndex, scan_vault


class LinkSuggestion(BaseModel):
    """A suggested wikilink."""

    text: str  # The text to link
    target: str  # The link target (may be same as text)
    existing: bool  # Whether target exists in vault
    confidence: float = 1.0


class LinkedText(BaseModel):
    """Text with wikilinks inserted."""

    original_text: str
    linked_text: str
    suggestions: list[LinkSuggestion]
    new_links: list[str]  # Links to notes that don't exist yet
    existing_links: list[str]  # Links to existing notes


def insert_wikilinks(text: str, links: list[str]) -> str:
    """Insert wikilinks into text for specified terms.

    Args:
        text: Original text.
        links: List of terms to convert to [[wikilinks]].

    Returns:
        Text with wikilinks inserted.
    """
    result = text

    # Sort by length (longest first) to avoid partial replacements
    sorted_links = sorted(links, key=len, reverse=True)

    for link in sorted_links:
        if not link:
            continue

        # Skip if already a wikilink
        if f"[[{link}]]" in result:
            continue

        # Create pattern that matches the term but not inside existing wikilinks
        # Use word boundaries for cleaner matching
        pattern = rf"(?<!\[\[)\b({re.escape(link)})\b(?!\]\])"

        # Replace first occurrence only to avoid over-linking
        result = re.sub(pattern, rf"[[\1]]", result, count=1, flags=re.IGNORECASE)

    return result


def suggest_links_from_vault(
    text: str,
    vault_index: VaultIndex,
    min_word_length: int = 3,
) -> list[LinkSuggestion]:
    """Suggest wikilinks based on existing vault notes.

    Args:
        text: Text to analyze.
        vault_index: Index of the vault.
        min_word_length: Minimum word length to consider.

    Returns:
        List of link suggestions.
    """
    suggestions: list[LinkSuggestion] = []
    text_lower = text.lower()

    # Check each note title
    for title in vault_index.note_titles:
        if len(title) < min_word_length:
            continue

        title_lower = title.lower()

        # Check if title appears in text (case-insensitive)
        if title_lower in text_lower:
            # Verify it's not already linked
            if f"[[{title}]]" not in text and f"[[{title_lower}]]" not in text.lower():
                suggestions.append(
                    LinkSuggestion(
                        text=title,
                        target=title,
                        existing=True,
                        confidence=0.9,
                    )
                )

    # Check aliases
    for title, aliases in vault_index.aliases.items():
        for alias in aliases:
            if len(alias) < min_word_length:
                continue

            alias_lower = alias.lower()
            if alias_lower in text_lower:
                if f"[[{alias}]]" not in text and f"[[{title}]]" not in text:
                    suggestions.append(
                        LinkSuggestion(
                            text=alias,
                            target=title,  # Link to the actual note
                            existing=True,
                            confidence=0.85,
                        )
                    )

    return suggestions


def process_text_with_links(
    text: str,
    suggested_links: list[str],
    vault_index: VaultIndex | None = None,
) -> LinkedText:
    """Process text by inserting suggested wikilinks.

    Args:
        text: Original text.
        suggested_links: Links suggested by LLM or heuristics.
        vault_index: Optional vault index for matching existing notes.

    Returns:
        LinkedText with results.
    """
    suggestions: list[LinkSuggestion] = []
    new_links: list[str] = []
    existing_links: list[str] = []

    # Classify each suggested link
    for link in suggested_links:
        if not link:
            continue

        existing = False
        target = link

        if vault_index:
            # Check if it matches an existing note
            if link in vault_index.note_titles:
                existing = True
            else:
                # Check aliases
                for title, aliases in vault_index.aliases.items():
                    if link.lower() in [a.lower() for a in aliases]:
                        existing = True
                        target = title
                        break

                # Fuzzy match on titles
                if not existing:
                    link_lower = link.lower()
                    for title in vault_index.note_titles:
                        if title.lower() == link_lower:
                            existing = True
                            target = title
                            break

        suggestions.append(
            LinkSuggestion(
                text=link,
                target=target,
                existing=existing,
            )
        )

        if existing:
            existing_links.append(target)
        else:
            new_links.append(link)

    # Insert links into text
    links_to_insert = [s.text for s in suggestions]
    linked_text = insert_wikilinks(text, links_to_insert)

    return LinkedText(
        original_text=text,
        linked_text=linked_text,
        suggestions=suggestions,
        new_links=new_links,
        existing_links=existing_links,
    )


def auto_link_from_vault(
    text: str,
    vault_path: Path,
    exclude_dirs: list[str] | None = None,
) -> LinkedText:
    """Automatically add wikilinks based on vault contents.

    This is a simpler alternative to LLM-based linking that just
    looks for exact matches with existing note titles.

    Args:
        text: Text to process.
        vault_path: Path to the Obsidian vault.
        exclude_dirs: Directories to exclude from scanning.

    Returns:
        LinkedText with auto-linked content.
    """
    # Scan the vault
    index = scan_vault(vault_path, exclude_dirs)

    # Find suggestions
    suggestions = suggest_links_from_vault(text, index)

    # Process and return
    links = [s.text for s in suggestions]
    linked_text = insert_wikilinks(text, links)

    return LinkedText(
        original_text=text,
        linked_text=linked_text,
        suggestions=suggestions,
        new_links=[],
        existing_links=[s.target for s in suggestions],
    )
