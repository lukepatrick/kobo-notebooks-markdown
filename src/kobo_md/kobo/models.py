"""Data models for Kobo notebooks.

This module defines Pydantic models for representing Kobo notebook data.
The models handle JSON deserialization from Kobo's API responses and provide
convenient properties for working with the data.

Model hierarchy:
- NotebookListItem: Basic info from library listing (HTML-parsed)
- NotebookMetadata: Detailed metadata from API (JSON-parsed)
- NotebookPage: Single page content with HTML and extracted text
- Notebook: Complete notebook combining metadata and all pages
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Kobo notebook content types.

    Kobo notebooks come in different formats depending on how they were created:
    - ADVANCED: Created with text recognition enabled (MyScript Nebo format)
    - BASIC: Simple notebooks without text recognition
    - BASIC_RAW: Variant of basic format

    Only ADVANCED notebooks contain extractable text content.
    BASIC notebooks only contain image data.
    """

    ADVANCED = "application/vnd.myscript.nebo+text"
    BASIC = "application/vnd.myscript.nebo"
    BASIC_RAW = "application/vnd.myscript.nebo+raw"


class NotebookMetadata(BaseModel):
    """Detailed metadata for a Kobo notebook.

    Populated from the GetNotebookMetadata API endpoint. Field names use
    aliases to match Kobo's PascalCase JSON format while exposing
    snake_case in Python.

    Attributes:
        id: UUID identifier for the notebook.
        display_name: User-visible notebook title.
        file_size: Size in bytes (as string from API).
        etag: Entity tag for cache validation. May contain escaped quotes.
        content_type: MIME type indicating notebook format (see ContentType).
        total_pages: Number of pages in the notebook.
        last_modified_utc: Timestamp of last modification.
        can_be_previewed: Whether the notebook supports preview/export.
    """

    id: str = Field(alias="Id")
    display_name: str = Field(alias="DisplayName")
    file_size: str = Field(alias="FileSize")
    etag: str = Field(alias="ETag")
    content_type: str = Field(alias="ContentType")
    total_pages: int = Field(alias="TotalPages")
    last_modified_utc: datetime = Field(alias="LastModifiedUtc")
    can_be_previewed: bool = Field(default=True, alias="CanBePreviewed")

    model_config = {"populate_by_name": True}

    @property
    def is_advanced(self) -> bool:
        """Check if this notebook has extractable text content.

        Only 'advanced' notebooks (ContentType.ADVANCED) contain text
        recognition data. Basic notebooks only have image data.
        """
        return self.content_type == ContentType.ADVANCED.value

    @property
    def clean_etag(self) -> str:
        """Return ETag without escaped quotes.

        Kobo's API sometimes returns ETags with escaped quotes (\\").
        This property provides the cleaned version for display.
        """
        return self.etag.replace('\\"', '"').strip('"')


class NotebookListItem(BaseModel):
    """Basic notebook info extracted from library listing HTML.

    This is a lightweight model used when listing notebooks. It contains
    just enough information to display a list and identify notebooks
    for further operations.

    Attributes:
        id: UUID identifier for the notebook.
        title: Display title of the notebook.
        can_be_previewed: Whether the notebook can be exported/previewed.
        etag: Optional cache validation tag.
        last_modified_utc: Optional timestamp as string (format varies).
    """

    id: str
    title: str
    can_be_previewed: bool = True
    etag: str | None = None
    last_modified_utc: str | None = None


class NotebookPage(BaseModel):
    """Content of a single notebook page.

    Contains both the raw HTML from Kobo and the extracted plain text.
    The blocks list contains individual text blocks extracted from the page,
    useful for more granular processing.

    Attributes:
        page_number: 0-indexed page number.
        html_content: Raw HTML content from Kobo's API.
        text_content: Extracted and cleaned plain text.
        blocks: Individual text blocks for granular processing.
    """

    page_number: int
    html_content: str
    text_content: str = ""
    blocks: list[str] = Field(default_factory=list)


class Notebook(BaseModel):
    """Complete notebook combining metadata and page content.

    This is the main model for working with notebook data. It combines
    the metadata (title, dates, etc.) with all page content.

    Attributes:
        metadata: Notebook metadata (title, page count, timestamps).
        pages: List of all pages with their content.
    """

    metadata: NotebookMetadata
    pages: list[NotebookPage] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Get all text content from all pages, joined with blank lines.

        Useful for processing the entire notebook as a single text block.
        Empty pages are skipped.
        """
        return "\n\n".join(page.text_content for page in self.pages if page.text_content)

    @property
    def markdown(self) -> str:
        """Convert notebook to basic markdown format.

        Generates a simple markdown representation with:
        - Title as H1
        - Export metadata as blockquote
        - Each page as H2 section (if multi-page)
        - Page content as body text

        For more control over formatting, use notebook_to_markdown() instead.
        """
        lines = [
            f"# {self.metadata.display_name}",
            "",
            f"> Exported from Kobo on {datetime.now().strftime('%Y-%m-%d')}",
            f"> Last modified: {self.metadata.last_modified_utc.strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]

        for page in self.pages:
            if self.metadata.total_pages > 1:
                lines.append(f"## Page {page.page_number + 1}")
                lines.append("")

            if page.text_content:
                lines.append(page.text_content)
                lines.append("")

        return "\n".join(lines)
