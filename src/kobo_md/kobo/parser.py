"""HTML and JSON parsing for Kobo notebook content."""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from kobo_md.kobo.models import NotebookListItem, NotebookMetadata, NotebookPage


class ParseError(Exception):
    """Error parsing Kobo response."""

    pass


def parse_notebook_list_html(html: str) -> list[NotebookListItem]:
    """Parse notebook list from HTML page.

    The notebook list page is server-side rendered HTML, not JSON.
    Notebooks are in elements like:
        <li class="notebook-item-wrapper">
            <a class="notebook-item-detail"
               data-notebook-id="uuid"
               data-notebook-can-be-previewed="True">

    Args:
        html: HTML content of the notebooks page.

    Returns:
        List of notebook items.
    """
    soup = BeautifulSoup(html, "lxml")
    notebooks: list[NotebookListItem] = []

    # Find all notebook items
    notebook_links = soup.select("a.notebook-item-detail[data-notebook-id]")

    for link in notebook_links:
        if not isinstance(link, Tag):
            continue

        notebook_id = link.get("data-notebook-id")
        if not notebook_id or not isinstance(notebook_id, str):
            continue

        # Get title from nested element
        title_elem = link.select_one(".notebook-title p")
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"

        # Get preview status
        can_preview = link.get("data-notebook-can-be-previewed", "True")
        can_be_previewed = str(can_preview).lower() == "true"

        # Get optional metadata
        etag = link.get("data-notebook-etag")
        last_modified = link.get("data-notebook-last-modified-utc")

        notebooks.append(
            NotebookListItem(
                id=notebook_id,
                title=title,
                can_be_previewed=can_be_previewed,
                etag=str(etag) if etag else None,
                last_modified_utc=str(last_modified) if last_modified else None,
            )
        )

    return notebooks


def parse_notebook_metadata(response: dict[str, Any]) -> NotebookMetadata:
    """Parse notebook metadata from API response.

    Args:
        response: JSON response from GetNotebookMetadata endpoint.

    Returns:
        NotebookMetadata object.

    Raises:
        ParseError: If response is invalid.
    """
    if response.get("result") != "success":
        raise ParseError(f"API returned error: {response}")

    data = response.get("data")
    if not data:
        raise ParseError("No data in response")

    try:
        return NotebookMetadata.model_validate(data)
    except Exception as e:
        raise ParseError(f"Failed to parse metadata: {e}") from e


def parse_notebook_content(response: dict[str, Any], page_number: int) -> NotebookPage:
    """Parse notebook page content from API response.

    The content is HTML with text in <div class="block-text"> elements.
    Each block contains paragraphs and spans with styling.

    Args:
        response: JSON response from GetNotebookContent endpoint.
        page_number: 0-indexed page number.

    Returns:
        NotebookPage with extracted content.

    Raises:
        ParseError: If response is invalid.
    """
    if response.get("result") != "success":
        raise ParseError(f"API returned error: {response}")

    data = response.get("data", {})
    html_content = data.get("notebookContent", "")

    if not html_content:
        return NotebookPage(
            page_number=page_number,
            html_content="",
            text_content="",
            blocks=[],
        )

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "lxml")

    # Extract text blocks
    blocks: list[str] = []
    block_elements = soup.select("div.block-text")

    for block in block_elements:
        # Get text content, preserving some structure
        block_text = _extract_block_text(block)
        if block_text.strip():
            blocks.append(block_text)

    # Combine all text
    text_content = "\n\n".join(blocks)

    return NotebookPage(
        page_number=page_number,
        html_content=html_content,
        text_content=text_content,
        blocks=blocks,
    )


def _extract_block_text(block: Tag) -> str:
    """Extract text from a block element, preserving structure.

    Handles lists, headings, and paragraphs.

    Args:
        block: BeautifulSoup Tag for a block element.

    Returns:
        Extracted text with markdown-like formatting.
    """
    lines: list[str] = []

    for elem in block.children:
        if not isinstance(elem, Tag):
            continue

        if elem.name == "p":
            # Check for list items (bullets)
            text = elem.get_text(strip=True)
            if text:
                # Check if it looks like a list item (starts with bullet-like chars)
                if text.startswith(("•", "-", "*", "·")):
                    lines.append(f"- {text[1:].strip()}")
                else:
                    lines.append(text)

        elif elem.name == "ul":
            for li in elem.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"- {text}")

        elif elem.name == "ol":
            for i, li in enumerate(elem.find_all("li"), 1):
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"{i}. {text}")

        elif elem.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(elem.name[1])
            text = elem.get_text(strip=True)
            if text:
                lines.append(f"{'#' * level} {text}")

    # If no structured elements found, just get all text
    if not lines:
        text = block.get_text(separator="\n", strip=True)
        if text:
            lines = [text]

    return "\n".join(lines)


def extract_wikilinks(text: str) -> list[str]:
    """Extract existing wikilinks from text.

    Args:
        text: Text content that may contain [[wikilinks]].

    Returns:
        List of wikilink targets (without brackets).
    """
    pattern = r"\[\[([^\]]+)\]\]"
    return re.findall(pattern, text)


def find_potential_wikilinks(text: str) -> list[str]:
    """Find potential wikilink candidates in text.

    Looks for proper nouns, titles, and other linkable content.
    This is a basic heuristic - AI enhancement will do better.

    Args:
        text: Text to analyze.

    Returns:
        List of potential link targets.
    """
    candidates: set[str] = set()

    # Pattern for capitalized phrases (2+ words starting with capitals)
    # This catches names like "Martin Luther King", titles like "The Great Gatsby"
    cap_phrase = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    for match in re.findall(cap_phrase, text):
        # Skip if already a wikilink
        if f"[[{match}]]" not in text:
            candidates.add(match)

    # Pattern for quoted titles
    quoted = r'"([^"]+)"'
    for match in re.findall(quoted, text):
        if len(match) > 2 and f"[[{match}]]" not in text:
            candidates.add(match)

    # Pattern for book/article titles in italics (if converted from HTML)
    # Pattern for phrases after "by " (author attribution)
    by_pattern = r"\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
    for match in re.findall(by_pattern, text):
        if f"[[{match}]]" not in text:
            candidates.add(match)

    return list(candidates)
