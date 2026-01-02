"""Obsidian vault scanning and indexing.

This module provides functionality to scan an Obsidian vault and build
an index of its contents. The index includes:
- Note titles (derived from filenames)
- Tags (from frontmatter and inline #tags)
- Aliases (from frontmatter)

The index is used to:
1. Suggest links to existing notes when processing new content
2. Identify which suggested links already have corresponding notes
3. Provide context to LLMs about the vault's content

Performance note: For large vaults, consider caching the index rather
than rescanning on every operation.
"""

import re
from pathlib import Path

from pydantic import BaseModel


class VaultIndex(BaseModel):
    """Index of an Obsidian vault's contents.

    Provides a searchable index of notes, tags, and aliases in the vault.
    Used by the linker to match suggested links against existing notes.

    Attributes:
        vault_path: Path to the vault root directory.
        note_titles: List of all note titles (filenames without .md).
        tags: List of all unique tags found in the vault.
        aliases: Mapping of note title to its aliases from frontmatter.
    """

    vault_path: Path
    note_titles: list[str]
    tags: list[str]
    aliases: dict[str, list[str]]

    @property
    def all_linkable(self) -> list[str]:
        """Get all linkable targets (titles + aliases).

        Returns a combined, sorted list of all terms that can be linked to:
        both note titles and their aliases.
        """
        linkable = set(self.note_titles)
        for alias_list in self.aliases.values():
            linkable.update(alias_list)
        return sorted(linkable)


def scan_vault(vault_path: Path, exclude_dirs: list[str] | None = None) -> VaultIndex:
    """Scan an Obsidian vault to build an index of notes, tags, and aliases.

    Walks through all .md files in the vault, extracting:
    - Note titles from filenames
    - Tags from both frontmatter and inline #tags in content
    - Aliases from frontmatter (both "alias" and "aliases" keys)

    The scan excludes common non-content directories by default (.obsidian,
    .git, .trash, node_modules).

    Args:
        vault_path: Path to the vault root directory.
        exclude_dirs: Directory names to exclude from scanning.
            Defaults to [".obsidian", ".git", ".trash", "node_modules"].

    Returns:
        VaultIndex with discovered notes, tags, and aliases.

    Note:
        Files that cannot be read (permissions, encoding issues) are
        silently skipped. The note title is still recorded from the filename.
    """
    if exclude_dirs is None:
        exclude_dirs = [".obsidian", ".git", ".trash", "node_modules"]

    note_titles: list[str] = []
    tags: set[str] = set()
    aliases: dict[str, list[str]] = {}

    # Regex: Inline tags like #tag-name (must start with letter)
    tag_pattern = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)")

    # Regex: YAML frontmatter block at start of file
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

    # Regex: Aliases in frontmatter (supports "alias" or "aliases" key)
    # Matches both inline [a, b] and list format
    alias_pattern = re.compile(r"aliases?:\s*\[([^\]]*)\]|aliases?:\s*\n((?:\s*-\s*.+\n)*)")

    for md_file in vault_path.rglob("*.md"):
        # Skip files in excluded directories
        if any(excluded in md_file.parts for excluded in exclude_dirs):
            continue

        # Note title is the filename without .md extension
        title = md_file.stem
        note_titles.append(title)

        # Read file content for tags and aliases
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            # Skip unreadable files but still record the title
            continue

        # Extract inline tags from content body
        found_tags = tag_pattern.findall(content)
        tags.update(found_tags)

        # Extract frontmatter if present
        frontmatter_match = frontmatter_pattern.match(content)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)

            # Extract tags from frontmatter "tags:" field
            if "tags:" in frontmatter:
                tag_line_match = re.search(
                    r"tags:\s*\[([^\]]*)\]|tags:\s*\n((?:\s*-\s*.+\n)*)",
                    frontmatter,
                )
                if tag_line_match:
                    if tag_line_match.group(1):
                        # Inline format: tags: [tag1, tag2]
                        inline_tags = tag_line_match.group(1)
                        tags.update(
                            t.strip().strip("'\"")
                            for t in inline_tags.split(",")
                            if t.strip()
                        )
                    elif tag_line_match.group(2):
                        # List format: tags:\n  - tag1\n  - tag2
                        list_tags = tag_line_match.group(2)
                        tags.update(
                            line.strip().lstrip("-").strip().strip("'\"")
                            for line in list_tags.split("\n")
                            if line.strip()
                        )

            # Extract aliases from frontmatter
            alias_match = alias_pattern.search(frontmatter)
            if alias_match:
                note_aliases: list[str] = []
                if alias_match.group(1):
                    # Inline format: aliases: [alias1, alias2]
                    inline_aliases = alias_match.group(1)
                    note_aliases = [
                        a.strip().strip("'\"")
                        for a in inline_aliases.split(",")
                        if a.strip()
                    ]
                elif alias_match.group(2):
                    # List format: aliases:\n  - alias1\n  - alias2
                    list_aliases = alias_match.group(2)
                    note_aliases = [
                        line.strip().lstrip("-").strip().strip("'\"")
                        for line in list_aliases.split("\n")
                        if line.strip()
                    ]
                if note_aliases:
                    aliases[title] = note_aliases

    return VaultIndex(
        vault_path=vault_path,
        note_titles=sorted(note_titles),
        tags=sorted(tags),
        aliases=aliases,
    )


def find_matching_notes(
    query: str,
    index: VaultIndex,
    _threshold: float = 0.8,
) -> list[str]:
    """Find notes that match a query string.

    Performs case-insensitive matching against note titles and aliases.
    Uses substring matching for flexible results.

    Matching priority:
    1. Exact match (case-insensitive)
    2. Query is substring of title
    3. Title is substring of query
    4. Match against aliases (same rules)

    Args:
        query: String to search for (e.g., "Machine Learning").
        index: VaultIndex to search in.
        threshold: Similarity threshold (reserved for future fuzzy matching).

    Returns:
        List of matching note titles. Returns actual note titles even
        when matching was against an alias.

    Note:
        For fuzzy matching, consider using rapidfuzz library.
        The threshold parameter is currently unused but reserved
        for future implementation.
    """
    query_lower = query.lower()
    matches: list[str] = []

    # First, check note titles
    for title in index.note_titles:
        title_lower = title.lower()

        # Exact match (highest priority)
        if query_lower == title_lower:
            matches.append(title)
            continue

        # Substring match (query in title or title in query)
        if query_lower in title_lower or title_lower in query_lower:
            matches.append(title)
            continue

    # Then, check aliases (link to the actual note title)
    for title, alias_list in index.aliases.items():
        for alias in alias_list:
            alias_lower = alias.lower()
            if query_lower == alias_lower or query_lower in alias_lower:
                if title not in matches:
                    matches.append(title)
                break  # Found a match for this note, move to next

    return matches


def get_note_context(note_path: Path, max_chars: int = 500) -> str:
    """Extract a context snippet from a note for LLM processing.

    Reads the beginning of a note (after frontmatter) to provide
    context about what the note contains. Useful for helping LLMs
    understand existing notes when suggesting links.

    Args:
        note_path: Path to the markdown note file.
        max_chars: Maximum characters to return (default 500).

    Returns:
        First portion of the note's body content, or empty string
        if the file cannot be read.
    """
    try:
        content = note_path.read_text(encoding="utf-8", errors="ignore")

        # Strip YAML frontmatter if present
        if content.startswith("---"):
            end_match = re.search(r"\n---\n", content[3:])
            if end_match:
                content = content[end_match.end() + 3:]

        # Remove headings to get just body text
        content = re.sub(r"^#+\s+.*$", "", content, flags=re.MULTILINE)
        content = content.strip()

        # Truncate if too long
        if len(content) > max_chars:
            content = content[:max_chars] + "..."

        return content
    except Exception:
        return ""
