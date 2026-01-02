"""HTML and JSON parsing for Kobo notebook content.

This module handles parsing of both HTML pages (notebook listings) and
JSON API responses (metadata and content). Kobo's notebook content uses
the MyScript Nebo format embedded in HTML.

Key functions:
- parse_notebook_list_html: Parse notebook listing from library page
- parse_notebook_metadata: Parse JSON metadata response
- parse_notebook_content: Parse page content and extract text

The text extraction handles various HTML structures including paragraphs,
lists, and headings, converting them to clean markdown-like text.
"""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from kobo_md.kobo.models import NotebookListItem, NotebookMetadata, NotebookPage


class ParseError(Exception):
    """Error parsing Kobo response data.

    Raised when the response structure doesn't match expected format,
    indicating either an API change or malformed data.
    """

    pass


def parse_notebook_list_html(html: str) -> list[NotebookListItem]:
    """Parse notebook list from the library HTML page.

    Kobo's notebook library is server-side rendered HTML, not a JSON API.
    This function extracts notebook information from the HTML structure.

    Expected HTML structure:
        <li class="notebook-item-wrapper">
            <a class="notebook-item-detail"
               data-notebook-id="uuid"
               data-notebook-can-be-previewed="True">
                <div class="notebook-title">
                    <p>Notebook Title</p>
                </div>
            </a>
        </li>

    Args:
        html: HTML content of the notebooks library page.

    Returns:
        List of NotebookListItem objects, one per notebook found.
        Returns empty list if no notebooks are found.
    """
    # Use lxml parser for speed and robust handling of malformed HTML
    soup = BeautifulSoup(html, "lxml")
    notebooks: list[NotebookListItem] = []

    # CSS selector targets anchor tags with notebook data attributes
    notebook_links = soup.select("a.notebook-item-detail[data-notebook-id]")

    for link in notebook_links:
        if not isinstance(link, Tag):
            continue

        notebook_id = link.get("data-notebook-id")
        if not notebook_id or not isinstance(notebook_id, str):
            # Skip malformed entries without valid IDs
            continue

        # Title is nested in .notebook-title > p
        title_elem = link.select_one(".notebook-title p")
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"

        # Preview status determines if we can export text content
        can_preview = link.get("data-notebook-can-be-previewed", "True")
        can_be_previewed = str(can_preview).lower() == "true"

        # These attributes may not always be present
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
    """Parse notebook metadata from the GetNotebookMetadata API response.

    Kobo's API wraps responses in a standard envelope with "result" and "data"
    fields. This function validates the envelope and extracts the metadata.

    Args:
        response: JSON response dict from GetNotebookMetadata endpoint.
            Expected format: {"result": "success", "data": {...metadata...}}

    Returns:
        NotebookMetadata object with validated fields.

    Raises:
        ParseError: If response indicates an error or has invalid structure.
    """
    # Validate the response envelope
    if response.get("result") != "success":
        raise ParseError(f"API returned error: {response}")

    data = response.get("data")
    if not data:
        raise ParseError("No data in response - notebook may not exist")

    try:
        return NotebookMetadata.model_validate(data)
    except Exception as e:
        # Wrap validation errors for consistent error handling
        raise ParseError(f"Failed to parse metadata: {e}") from e


def parse_notebook_content(response: dict[str, Any], page_number: int) -> NotebookPage:
    """Parse notebook page content from the GetNotebookContent API response.

    Extracts text from Kobo's HTML content format. The content uses MyScript
    Nebo's format with text in <div class="block-text"> elements. Each block
    can contain paragraphs, lists, and headings.

    The extraction process:
    1. Validate the API response envelope
    2. Parse the HTML content
    3. Extract text blocks preserving structure (lists, headings)
    4. Convert to markdown-like plain text

    Args:
        response: JSON response dict from GetNotebookContent endpoint.
        page_number: 0-indexed page number (for tracking in the result).

    Returns:
        NotebookPage with raw HTML and extracted text content.

    Raises:
        ParseError: If response indicates an error.
    """
    # Validate the response envelope
    if response.get("result") != "success":
        raise ParseError(f"API returned error: {response}")

    data = response.get("data", {})
    html_content = data.get("notebookContent", "")

    # Handle empty pages gracefully
    if not html_content:
        return NotebookPage(
            page_number=page_number,
            html_content="",
            text_content="",
            blocks=[],
        )

    # Parse the HTML content using lxml for robust handling
    soup = BeautifulSoup(html_content, "lxml")

    # Extract text blocks - each div.block-text is a logical text block
    blocks: list[str] = []
    block_elements = soup.select("div.block-text")

    for block in block_elements:
        block_text = _extract_block_text(block)
        if block_text.strip():
            blocks.append(block_text)

    # Join blocks with double newlines for paragraph separation
    text_content = "\n\n".join(blocks)

    return NotebookPage(
        page_number=page_number,
        html_content=html_content,
        text_content=text_content,
        blocks=blocks,
    )


def _extract_block_text(block: Tag) -> str:
    """Extract text from a block element, preserving semantic structure.

    Converts HTML elements to markdown-like plain text:
    - Paragraphs become plain lines
    - Bullet paragraphs (starting with •, -, *, ·) become "- item"
    - <ul>/<ol> lists are formatted as markdown lists
    - Headings become "# Heading" (with appropriate level)

    This preserves the logical structure of handwritten notes while
    producing clean, readable plain text.

    Args:
        block: BeautifulSoup Tag for a div.block-text element.

    Returns:
        Extracted text with markdown-like formatting.
    """
    lines: list[str] = []

    for elem in block.children:
        if not isinstance(elem, Tag):
            continue

        if elem.name == "p":
            text = elem.get_text(strip=True)
            if text:
                # Detect bullet-style paragraphs (common in handwritten lists)
                if text.startswith(("•", "-", "*", "·")):
                    # Convert to markdown list item
                    lines.append(f"- {text[1:].strip()}")
                else:
                    lines.append(text)

        elif elem.name == "ul":
            # Unordered list - convert to markdown bullets
            for li in elem.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"- {text}")

        elif elem.name == "ol":
            # Ordered list - convert to numbered markdown
            for i, li in enumerate(elem.find_all("li"), 1):
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"{i}. {text}")

        elif elem.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # Headings - convert to markdown heading syntax
            level = int(elem.name[1])
            text = elem.get_text(strip=True)
            if text:
                lines.append(f"{'#' * level} {text}")

    # Fallback: if no structured elements found, extract all text
    if not lines:
        text = block.get_text(separator="\n", strip=True)
        if text:
            lines = [text]

    return "\n".join(lines)


def extract_wikilinks(text: str) -> list[str]:
    """Extract existing [[wikilinks]] from text.

    Useful for identifying which terms are already linked to avoid
    duplicating links during processing.

    Args:
        text: Text content that may contain [[wikilinks]].

    Returns:
        List of wikilink targets (the text between brackets).
        Returns empty list if no wikilinks found.
    """
    # Match [[anything]] but not nested brackets
    pattern = r"\[\[([^\]]+)\]\]"
    return re.findall(pattern, text)


def find_potential_wikilinks(text: str) -> list[str]:
    """Find potential wikilink candidates using heuristics.

    This provides a basic, non-AI approach to identifying linkable content.
    It looks for patterns that commonly represent entities worth linking:

    1. Capitalized phrases (2+ words): Names like "Martin Luther King",
       titles like "The Great Gatsby"
    2. Quoted text: Often indicates titles or special terms
    3. Author attributions: Text following "by " (e.g., "by Cal Newport")

    This is a fallback when AI processing is not available. The AI-based
    approach in the LLM providers produces much better results.

    Args:
        text: Text to analyze for potential links.

    Returns:
        List of potential link targets (without duplicates).
    """
    candidates: set[str] = set()

    # Pattern: Multi-word capitalized phrases (proper nouns, titles)
    # Matches: "John Smith", "Deep Work", "New York Times"
    cap_phrase = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    for match in re.findall(cap_phrase, text):
        if f"[[{match}]]" not in text:  # Skip if already linked
            candidates.add(match)

    # Pattern: Quoted text (often titles or emphasized terms)
    # Matches: "The Great Gatsby", "flow state"
    quoted = r'"([^"]+)"'
    for match in re.findall(quoted, text):
        if len(match) > 2 and f"[[{match}]]" not in text:
            candidates.add(match)

    # Pattern: Author attributions after "by"
    # Matches: "by Cal Newport", "by Marcus Aurelius"
    by_pattern = r"\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
    for match in re.findall(by_pattern, text):
        if f"[[{match}]]" not in text:
            candidates.add(match)

    return list(candidates)
