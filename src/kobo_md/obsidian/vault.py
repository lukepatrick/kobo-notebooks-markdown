"""Obsidian vault scanning and indexing."""

import re
from pathlib import Path

from pydantic import BaseModel


class VaultIndex(BaseModel):
    """Index of an Obsidian vault's contents."""

    vault_path: Path
    note_titles: list[str]
    tags: list[str]
    aliases: dict[str, list[str]]  # note title -> list of aliases

    @property
    def all_linkable(self) -> list[str]:
        """Get all linkable targets (titles + aliases)."""
        linkable = set(self.note_titles)
        for alias_list in self.aliases.values():
            linkable.update(alias_list)
        return sorted(linkable)


def scan_vault(vault_path: Path, exclude_dirs: list[str] | None = None) -> VaultIndex:
    """Scan an Obsidian vault for notes and tags.

    Args:
        vault_path: Path to the vault root.
        exclude_dirs: Directory names to exclude (e.g., [".obsidian", ".git"]).

    Returns:
        VaultIndex with discovered notes and tags.
    """
    if exclude_dirs is None:
        exclude_dirs = [".obsidian", ".git", ".trash", "node_modules"]

    note_titles: list[str] = []
    tags: set[str] = set()
    aliases: dict[str, list[str]] = {}

    # Pattern for tags in content
    tag_pattern = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)")

    # Pattern for YAML frontmatter
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

    # Pattern for aliases in frontmatter
    alias_pattern = re.compile(r"aliases?:\s*\[([^\]]*)\]|aliases?:\s*\n((?:\s*-\s*.+\n)*)")

    for md_file in vault_path.rglob("*.md"):
        # Skip excluded directories
        if any(excluded in md_file.parts for excluded in exclude_dirs):
            continue

        # Get note title from filename
        title = md_file.stem
        note_titles.append(title)

        # Read file content for tags and aliases
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Extract tags from content
        found_tags = tag_pattern.findall(content)
        tags.update(found_tags)

        # Extract frontmatter
        frontmatter_match = frontmatter_pattern.match(content)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)

            # Extract tags from frontmatter
            if "tags:" in frontmatter:
                # Handle both list and inline formats
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
                        # List format
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
                    # List format
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
    threshold: float = 0.8,
) -> list[str]:
    """Find notes that match a query string.

    Uses simple substring matching. For fuzzy matching,
    consider using rapidfuzz library.

    Args:
        query: String to search for.
        index: VaultIndex to search in.
        threshold: Minimum similarity threshold (0-1).

    Returns:
        List of matching note titles.
    """
    query_lower = query.lower()
    matches: list[str] = []

    for title in index.note_titles:
        title_lower = title.lower()

        # Exact match
        if query_lower == title_lower:
            matches.append(title)
            continue

        # Substring match
        if query_lower in title_lower or title_lower in query_lower:
            matches.append(title)
            continue

    # Also check aliases
    for title, alias_list in index.aliases.items():
        for alias in alias_list:
            alias_lower = alias.lower()
            if query_lower == alias_lower or query_lower in alias_lower:
                if title not in matches:
                    matches.append(title)
                break

    return matches


def get_note_context(note_path: Path, max_chars: int = 500) -> str:
    """Get context from a note for LLM processing.

    Args:
        note_path: Path to the markdown note.
        max_chars: Maximum characters to return.

    Returns:
        First portion of the note content.
    """
    try:
        content = note_path.read_text(encoding="utf-8", errors="ignore")

        # Remove frontmatter
        if content.startswith("---"):
            end_match = re.search(r"\n---\n", content[3:])
            if end_match:
                content = content[end_match.end() + 3:]

        # Remove headings and get body text
        content = re.sub(r"^#+\s+.*$", "", content, flags=re.MULTILINE)
        content = content.strip()

        if len(content) > max_chars:
            content = content[:max_chars] + "..."

        return content
    except Exception:
        return ""
