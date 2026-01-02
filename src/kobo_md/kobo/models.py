"""Data models for Kobo notebooks."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Kobo notebook content types."""

    ADVANCED = "application/vnd.myscript.nebo+text"  # Has text recognition
    BASIC = "application/vnd.myscript.nebo"  # Images only
    BASIC_RAW = "application/vnd.myscript.nebo+raw"  # Images only variant


class NotebookMetadata(BaseModel):
    """Metadata for a Kobo notebook."""

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
        """Check if this is an advanced notebook with text recognition."""
        return self.content_type == ContentType.ADVANCED.value

    @property
    def clean_etag(self) -> str:
        """Return ETag without escaped quotes."""
        return self.etag.replace('\\"', '"').strip('"')


class NotebookListItem(BaseModel):
    """Basic notebook info extracted from HTML list."""

    id: str
    title: str
    can_be_previewed: bool = True
    etag: str | None = None
    last_modified_utc: str | None = None


class NotebookPage(BaseModel):
    """Content of a single notebook page."""

    page_number: int
    html_content: str
    text_content: str = ""
    blocks: list[str] = Field(default_factory=list)


class Notebook(BaseModel):
    """Complete notebook with metadata and content."""

    metadata: NotebookMetadata
    pages: list[NotebookPage] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Get all text content from all pages."""
        return "\n\n".join(page.text_content for page in self.pages if page.text_content)

    @property
    def markdown(self) -> str:
        """Convert notebook to markdown format."""
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
