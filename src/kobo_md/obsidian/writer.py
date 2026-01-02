"""Markdown file writer for Obsidian vault."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from kobo_md.kobo.models import Notebook, NotebookMetadata


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Prevents path traversal attacks and ensures the result is a safe filename.

    Args:
        name: Original name.

    Returns:
        Safe filename.
    """
    # Replace path separators to prevent directory traversal
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    # Explicitly remove path traversal sequences (defense in depth)
    name = name.replace("..", "")
    # Remove leading/trailing whitespace and dots
    name = name.strip(". ")
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name or "untitled"


def format_frontmatter(metadata: dict[str, Any]) -> str:
    """Format YAML frontmatter for a note.

    Args:
        metadata: Dictionary of frontmatter fields.

    Returns:
        Formatted YAML frontmatter block.
    """
    lines = ["---"]
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, datetime):
            lines.append(f"{key}: {value.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Quote strings that might cause YAML issues
            if isinstance(value, str) and any(c in value for c in ":{}[]#&*!|>'\"%@`"):
                value = f'"{value}"'
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def notebook_to_markdown(
    notebook: Notebook,
    include_frontmatter: bool = True,
    include_source_info: bool = True,
) -> str:
    """Convert a notebook to markdown format.

    Args:
        notebook: Notebook to convert.
        include_frontmatter: Include YAML frontmatter.
        include_source_info: Include source information blockquote.

    Returns:
        Markdown string.
    """
    parts: list[str] = []

    # Frontmatter
    if include_frontmatter:
        frontmatter = {
            "title": notebook.metadata.display_name,
            "source": "kobo",
            "kobo_id": notebook.metadata.id,
            "created": notebook.metadata.last_modified_utc,
            "exported": datetime.now(),
            "tags": ["kobo", "notebook"],
        }
        parts.append(format_frontmatter(frontmatter))
        parts.append("")

    # Title
    parts.append(f"# {notebook.metadata.display_name}")
    parts.append("")

    # Source info
    if include_source_info:
        parts.append(
            f"> Exported from Kobo on {datetime.now().strftime('%Y-%m-%d')}"
        )
        parts.append(
            f"> Last modified: {notebook.metadata.last_modified_utc.strftime('%Y-%m-%d %H:%M')}"
        )
        parts.append("")
        parts.append("---")
        parts.append("")

    # Content from each page
    for i, page in enumerate(notebook.pages):
        if notebook.metadata.total_pages > 1:
            parts.append(f"## Page {i + 1}")
            parts.append("")

        if page.text_content:
            parts.append(page.text_content)
            parts.append("")

    return "\n".join(parts)


def write_notebook(
    notebook: Notebook,
    output_dir: Path,
    overwrite: bool = False,
) -> Path:
    """Write a notebook to a markdown file.

    Args:
        notebook: Notebook to write.
        output_dir: Directory to write to.
        overwrite: Whether to overwrite existing files.

    Returns:
        Path to the written file.

    Raises:
        FileExistsError: If file exists and overwrite is False.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(notebook.metadata.display_name) + ".md"
    filepath = output_dir / filename

    if filepath.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {filepath}")

    content = notebook_to_markdown(notebook)
    filepath.write_text(content, encoding="utf-8")

    return filepath


def append_to_daily_note(
    notebook: Notebook,
    daily_note_path: Path,
    section_heading: str = "## Kobo Notes",
) -> None:
    """Append notebook content to a daily note.

    Args:
        notebook: Notebook to append.
        daily_note_path: Path to the daily note.
        section_heading: Heading for the Kobo notes section.
    """
    # Read existing content if file exists
    existing_content = ""
    if daily_note_path.exists():
        existing_content = daily_note_path.read_text(encoding="utf-8")

    # Check if section already exists
    if section_heading in existing_content:
        # Append after the section heading
        parts = existing_content.split(section_heading, 1)
        new_content = (
            parts[0]
            + section_heading
            + "\n\n"
            + f"### {notebook.metadata.display_name}\n\n"
            + notebook.full_text
            + "\n\n"
            + parts[1]
            if len(parts) > 1
            else parts[0]
            + section_heading
            + "\n\n"
            + f"### {notebook.metadata.display_name}\n\n"
            + notebook.full_text
        )
    else:
        # Add new section at the end
        new_content = (
            existing_content
            + "\n\n"
            + section_heading
            + "\n\n"
            + f"### {notebook.metadata.display_name}\n\n"
            + notebook.full_text
        )

    daily_note_path.parent.mkdir(parents=True, exist_ok=True)
    daily_note_path.write_text(new_content.strip() + "\n", encoding="utf-8")


def get_daily_note_path(
    vault_path: Path,
    pattern: str,
    date: datetime | None = None,
) -> Path:
    """Get the path to a daily note based on the pattern.

    Args:
        vault_path: Path to the vault.
        pattern: Pattern with placeholders like {year}, {month}, {day}, {month_name}.
        date: Date for the note (defaults to today).

    Returns:
        Full path to the daily note.
    """
    if date is None:
        date = datetime.now()

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    formatted = pattern.format(
        year=date.year,
        month=date.month,
        day=date.day,
        month_name=month_names[date.month - 1],
    )

    return vault_path / formatted
