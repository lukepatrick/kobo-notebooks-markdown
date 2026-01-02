"""Wikilink suggestion and insertion for Obsidian notes.

This module handles the core linking functionality:
1. Inserting [[wikilinks]] into plain text
2. Suggesting links based on vault contents
3. Classifying links as existing or new

The linking process:
1. LLM or heuristics suggest terms to link (e.g., "Machine Learning")
2. Terms are matched against existing vault notes
3. Wikilinks are inserted into the text at appropriate locations
4. Results track which links are new vs existing

Key design decisions:
- Only the first occurrence of each term is linked (to avoid over-linking)
- Longer terms are matched first (to prevent partial matches)
- Matching is case-insensitive but preserves original case in output
"""

import re
from pathlib import Path

from pydantic import BaseModel

from kobo_md.obsidian.vault import VaultIndex, scan_vault


class LinkSuggestion(BaseModel):
    """A suggested wikilink with metadata.

    Attributes:
        text: The text in the document to convert to a link.
        target: The note to link to (may differ from text for aliases).
        existing: Whether the target note already exists in the vault.
        confidence: Confidence score (0-1) for AI-generated suggestions.
    """

    text: str
    target: str
    existing: bool
    confidence: float = 1.0


class LinkedText(BaseModel):
    """Result of processing text with wikilink insertion.

    Contains the original and modified text, plus metadata about
    what links were added.

    Attributes:
        original_text: The input text before processing.
        linked_text: The text with [[wikilinks]] inserted.
        suggestions: All link suggestions that were processed.
        new_links: Links pointing to notes that don't exist yet.
        existing_links: Links pointing to existing vault notes.
    """

    original_text: str
    linked_text: str
    suggestions: list[LinkSuggestion]
    new_links: list[str]
    existing_links: list[str]


def insert_wikilinks(text: str, links: list[str]) -> str:
    """Insert [[wikilinks]] into text for specified terms.

    Converts plain text terms to Obsidian wikilinks. Uses smart matching
    to avoid issues with overlapping terms and existing links.

    Algorithm:
    1. Sort links by length (longest first) to prevent partial matches
       e.g., "Machine Learning" before "Machine"
    2. For each term, find first occurrence not already in a wikilink
    3. Replace only first occurrence to avoid over-linking

    Args:
        text: Original text content.
        links: List of terms to convert to [[wikilinks]].

    Returns:
        Text with wikilinks inserted. Original text returned if
        no links can be inserted.
    """
    result = text

    # Sort longest-first to prevent "Machine" from matching before "Machine Learning"
    sorted_links = sorted(links, key=len, reverse=True)

    for link in sorted_links:
        if not link:
            continue

        # Skip if this exact link already exists
        if f"[[{link}]]" in result:
            continue

        # Pattern: word boundaries, not already inside [[brackets]]
        # (?<!\[\[) = not preceded by [[
        # \b = word boundary
        # (?!\]\]) = not followed by ]]
        pattern = rf"(?<!\[\[)\b({re.escape(link)})\b(?!\]\])"

        # Replace only first occurrence to avoid over-linking
        # (linking every instance of "Python" would be noisy)
        result = re.sub(pattern, rf"[[\1]]", result, count=1, flags=re.IGNORECASE)

    return result


def suggest_links_from_vault(
    text: str,
    vault_index: VaultIndex,
    min_word_length: int = 3,
) -> list[LinkSuggestion]:
    """Suggest wikilinks based on existing vault notes.

    Scans the text for mentions of existing note titles or their aliases.
    This enables automatic linking to related notes without AI processing.

    Args:
        text: Text to analyze for potential links.
        vault_index: Index of the vault (from scan_vault).
        min_word_length: Minimum term length to consider (filters noise).

    Returns:
        List of LinkSuggestion objects for terms found in the text
        that match existing notes. Suggestions have existing=True
        since they match vault contents.
    """
    suggestions: list[LinkSuggestion] = []
    text_lower = text.lower()

    # Check each note title against the text
    for title in vault_index.note_titles:
        if len(title) < min_word_length:
            continue

        title_lower = title.lower()

        # Case-insensitive check for title in text
        if title_lower in text_lower:
            # Skip if already linked
            if f"[[{title}]]" not in text and f"[[{title_lower}]]" not in text.lower():
                suggestions.append(
                    LinkSuggestion(
                        text=title,
                        target=title,
                        existing=True,
                        confidence=0.9,  # High confidence for exact title match
                    )
                )

    # Check aliases - link to the actual note, not the alias
    for title, aliases in vault_index.aliases.items():
        for alias in aliases:
            if len(alias) < min_word_length:
                continue

            alias_lower = alias.lower()
            if alias_lower in text_lower:
                # Check both alias and target aren't already linked
                if f"[[{alias}]]" not in text and f"[[{title}]]" not in text:
                    suggestions.append(
                        LinkSuggestion(
                            text=alias,
                            target=title,  # Link resolves to the actual note
                            existing=True,
                            confidence=0.85,  # Slightly lower for alias match
                        )
                    )

    return suggestions


def process_text_with_links(
    text: str,
    suggested_links: list[str],
    vault_index: VaultIndex | None = None,
) -> LinkedText:
    """Process text by inserting suggested wikilinks.

    This is the main entry point for processing text with link suggestions.
    It handles the full pipeline:
    1. Classify each suggested link as new or existing
    2. Resolve aliases to their target notes
    3. Insert wikilinks into the text
    4. Return comprehensive results for downstream processing

    The classification against vault_index enables features like:
    - Highlighting which links will create new notes
    - Using proper note titles for case-insensitive matches
    - Resolving aliases to actual note names

    Args:
        text: Original text content to process.
        suggested_links: Links suggested by LLM or heuristics. These are
            the terms that should become [[wikilinks]].
        vault_index: Optional vault index for matching existing notes.
            If None, all links are treated as new.

    Returns:
        LinkedText containing the processed text, list of suggestions
        with metadata, and categorized new/existing links.
    """
    suggestions: list[LinkSuggestion] = []
    new_links: list[str] = []
    existing_links: list[str] = []

    # Classify each suggested link by checking against vault contents
    # Priority: exact title match > alias match > case-insensitive title match
    for link in suggested_links:
        if not link:
            continue

        existing = False
        target = link

        if vault_index:
            # Step 1: Check for exact title match (case-sensitive)
            if link in vault_index.note_titles:
                existing = True
            else:
                # Step 2: Check if link matches any note's aliases
                # If so, resolve to the actual note title for proper linking
                for title, aliases in vault_index.aliases.items():
                    if link.lower() in [a.lower() for a in aliases]:
                        existing = True
                        target = title
                        break

                # Step 3: Case-insensitive title match (fuzzy)
                # Handles "machine learning" matching "Machine Learning"
                if not existing:
                    link_lower = link.lower()
                    for title in vault_index.note_titles:
                        if title.lower() == link_lower:
                            existing = True
                            target = title  # Use the properly-cased title
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

    This is a simpler, non-AI alternative to LLM-based linking. It scans
    the text for mentions of existing note titles and aliases, then
    converts those mentions to wikilinks.

    Use cases:
    - Quick linking without API costs
    - Offline operation
    - Integration with existing vault content

    The function scans the vault on each call. For repeated operations,
    consider using suggest_links_from_vault() with a cached VaultIndex
    for better performance.

    Args:
        text: Text to process for potential links.
        vault_path: Path to the Obsidian vault root directory.
        exclude_dirs: Directories to exclude from scanning
            (default: .obsidian, .git, .trash, node_modules).

    Returns:
        LinkedText with wikilinks inserted. All links are marked as
        existing since they're derived from vault contents.
    """
    # Build index of all notes, tags, and aliases in the vault
    index = scan_vault(vault_path, exclude_dirs)

    # Find note titles and aliases that appear in the text
    suggestions = suggest_links_from_vault(text, index)

    # Convert suggestions to wikilinks and build result
    # All links are existing since they came from vault contents
    links = [s.text for s in suggestions]
    linked_text = insert_wikilinks(text, links)

    return LinkedText(
        original_text=text,
        linked_text=linked_text,
        suggestions=suggestions,
        new_links=[],  # No new links - all matched existing notes
        existing_links=[s.target for s in suggestions],
    )
