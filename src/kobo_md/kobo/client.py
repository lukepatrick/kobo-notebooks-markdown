"""Kobo web portal API client."""

from urllib.parse import quote

import httpx

from kobo_md.auth.cookies import KoboCookies
from kobo_md.kobo.models import NotebookListItem, NotebookMetadata, NotebookPage
from kobo_md.kobo.parser import (
    parse_notebook_content,
    parse_notebook_list_html,
    parse_notebook_metadata,
)


class KoboClientError(Exception):
    """Error communicating with Kobo API."""

    pass


class KoboClient:
    """Client for Kobo web portal API."""

    BASE_URL = "https://www.kobo.com"

    def __init__(
        self,
        cookies: KoboCookies,
        region: str = "us",
        language: str = "en",
        timeout: float = 30.0,
    ):
        """Initialize the Kobo client.

        Args:
            cookies: Authentication cookies.
            region: Kobo region (e.g., "us", "ca", "uk").
            language: Language code (e.g., "en").
            timeout: Request timeout in seconds.
        """
        self.cookies = cookies
        self.region = region
        self.language = language
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def _path_prefix(self) -> str:
        """URL path prefix for region/language."""
        return f"/{self.region}/{self.language}"

    @property
    def _headers(self) -> dict[str, str]:
        """Headers required for API requests."""
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) "
                "Gecko/20100101 Firefox/146.0"
            ),
        }

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                cookies=self.cookies.to_dict(),
                headers=self._headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "KoboClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def list_notebooks(self) -> list[NotebookListItem]:
        """List all notebooks from the library.

        Returns:
            List of notebook items with basic info.

        Raises:
            KoboClientError: If the request fails.
        """
        url = f"{self._path_prefix}/library/notebooks"

        try:
            response = self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise KoboClientError(
                    "Authentication failed. Please refresh your browser cookies."
                ) from e
            raise KoboClientError(f"Failed to list notebooks: {e}") from e
        except httpx.RequestError as e:
            raise KoboClientError(f"Request failed: {e}") from e

        return parse_notebook_list_html(response.text)

    def get_notebook_metadata(self, notebook_id: str) -> NotebookMetadata:
        """Get metadata for a specific notebook.

        Args:
            notebook_id: UUID of the notebook.

        Returns:
            Notebook metadata.

        Raises:
            KoboClientError: If the request fails.
        """
        url = f"{self._path_prefix}/Library/GetNotebookMetadata"
        params = {"notebookId": notebook_id}

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise KoboClientError(f"Failed to get notebook metadata: {e}") from e
        except httpx.RequestError as e:
            raise KoboClientError(f"Request failed: {e}") from e

        return parse_notebook_metadata(response.json())

    def get_notebook_page(
        self, notebook_id: str, page: int, etag: str
    ) -> NotebookPage:
        """Get content for a specific notebook page.

        Args:
            notebook_id: UUID of the notebook.
            page: 0-indexed page number.
            etag: ETag from notebook metadata.

        Returns:
            Page content.

        Raises:
            KoboClientError: If the request fails.
        """
        url = f"{self._path_prefix}/Library/GetNotebookContent"
        # ETag needs to be URL-encoded with quotes
        encoded_etag = quote(etag, safe="")
        params = {
            "notebookId": notebook_id,
            "page": str(page),
            "etag": encoded_etag,
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise KoboClientError(f"Failed to get notebook page: {e}") from e
        except httpx.RequestError as e:
            raise KoboClientError(f"Request failed: {e}") from e

        return parse_notebook_content(response.json(), page)

    def get_all_notebook_pages(
        self, notebook_id: str, metadata: NotebookMetadata | None = None
    ) -> list[NotebookPage]:
        """Get all pages from a notebook.

        Args:
            notebook_id: UUID of the notebook.
            metadata: Optional pre-fetched metadata.

        Returns:
            List of all pages.

        Raises:
            KoboClientError: If any request fails.
        """
        if metadata is None:
            metadata = self.get_notebook_metadata(notebook_id)

        pages = []
        for page_num in range(metadata.total_pages):
            page = self.get_notebook_page(notebook_id, page_num, metadata.etag)
            pages.append(page)

        return pages

    def get_notebook_thumbnail(self, notebook_id: str, etag: str) -> bytes:
        """Get thumbnail image for a notebook.

        Args:
            notebook_id: UUID of the notebook.
            etag: ETag from notebook metadata.

        Returns:
            Image bytes.

        Raises:
            KoboClientError: If the request fails.
        """
        url = f"{self._path_prefix}/Library/GetNotebookThumbnailImage"
        encoded_etag = quote(etag, safe="")
        params = {
            "notebookId": notebook_id,
            "etag": encoded_etag,
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise KoboClientError(f"Failed to get notebook thumbnail: {e}") from e
        except httpx.RequestError as e:
            raise KoboClientError(f"Request failed: {e}") from e

        return response.content
