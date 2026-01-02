"""Kobo web portal API client.

This module provides a client for interacting with Kobo's unofficial web API
to fetch notebook data. The API is reverse-engineered from the Kobo web portal
and may change without notice.

Key features:
- Session-based authentication using browser cookies
- Automatic retry with exponential backoff for transient failures
- Support for listing, fetching metadata, and downloading notebook content
"""

import re
import time
from typing import Callable, TypeVar
from urllib.parse import quote

import httpx

from kobo_md.auth.cookies import KoboCookies
from kobo_md.kobo.models import NotebookListItem, NotebookMetadata, NotebookPage
from kobo_md.kobo.parser import (
    parse_notebook_content,
    parse_notebook_list_html,
    parse_notebook_metadata,
)

# UUID v4 pattern for validating notebook IDs
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class KoboClientError(Exception):
    """Base error for Kobo API communication failures."""

    pass


class AuthenticationError(KoboClientError):
    """Authentication failed - cookies are invalid or expired.

    This typically means the user needs to re-authenticate by logging
    into Kobo in their browser and re-extracting cookies.
    """

    pass


class RateLimitError(KoboClientError):
    """Request was rate-limited by the Kobo API.

    The client will automatically retry with exponential backoff,
    but if this error is raised, all retries have been exhausted.
    """

    pass


class NotFoundError(KoboClientError):
    """Requested notebook was not found.

    The notebook ID may be invalid, or the notebook may have been deleted.
    """

    pass


T = TypeVar("T")


def _validate_notebook_id(notebook_id: str) -> None:
    """Validate that a notebook ID is a valid UUID.

    Kobo uses UUID v4 identifiers for notebooks. Validating early prevents
    unnecessary API calls and provides clearer error messages.

    Args:
        notebook_id: The notebook ID to validate.

    Raises:
        ValueError: If the notebook ID is not a valid UUID.
    """
    if not _UUID_PATTERN.match(notebook_id):
        raise ValueError(
            f"Invalid notebook ID: {notebook_id!r}. "
            "Notebook IDs must be valid UUIDs (e.g., '12345678-1234-1234-1234-123456789abc')."
        )


def _retry_request(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> T:
    """Retry a request with exponential backoff.

    Uses exponential backoff to handle transient failures gracefully.
    The delay doubles with each attempt: 1s, 2s, 4s, etc., capped at max_delay.

    Retryable errors:
    - 429 Too Many Requests (rate limiting)
    - 5xx Server errors
    - Network/connection errors

    Non-retryable errors (raised immediately):
    - 401 Unauthorized (auth failure)
    - 403 Forbidden
    - 404 Not Found
    - Other 4xx client errors

    Args:
        func: Function to call that returns a response.
        max_retries: Maximum number of retry attempts after the first failure.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries (caps exponential growth).

    Returns:
        Result of the function call.

    Raises:
        httpx.HTTPStatusError: For non-retryable HTTP errors.
        KoboClientError: If all retries are exhausted.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except httpx.HTTPStatusError as e:
            # Don't retry client errors (4xx) except 429 (rate limit)
            if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                raise
            last_error = e
        except httpx.RequestError as e:
            # Network errors (timeout, connection refused, etc.) are retryable
            last_error = e

        if attempt < max_retries:
            # Exponential backoff: 1s, 2s, 4s, 8s... capped at max_delay
            delay = min(base_delay * (2**attempt), max_delay)
            time.sleep(delay)

    raise KoboClientError(f"Request failed after {max_retries + 1} attempts: {last_error}")


class KoboClient:
    """Client for Kobo web portal API.

    Provides methods to interact with Kobo's notebook storage:
    - List all notebooks in the user's library
    - Fetch notebook metadata (title, page count, etc.)
    - Download individual pages with text content
    - Retrieve notebook thumbnails

    The client handles authentication via browser cookies and automatically
    retries failed requests with exponential backoff.

    Usage:
        cookies = extract_cookies("firefox")
        with KoboClient(cookies) as client:
            notebooks = client.list_notebooks()
            for nb in notebooks:
                metadata = client.get_notebook_metadata(nb.id)
                pages = client.get_all_notebook_pages(nb.id, metadata)
    """

    BASE_URL = "https://www.kobo.com"

    def __init__(
        self,
        cookies: KoboCookies,
        region: str = "us",
        language: str = "en",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize the Kobo client.

        Args:
            cookies: Authentication cookies extracted from browser.
            region: Kobo region code. Determines the store/content region.
                Common values: "us", "ca", "uk", "au", "nz".
            language: Language code for API responses (e.g., "en", "fr").
            timeout: Request timeout in seconds. Increase for slow connections.
            max_retries: Maximum retry attempts for transient failures.
                Uses exponential backoff between attempts.
        """
        self.cookies = cookies
        self.region = region
        self.language = language
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.Client | None = None

    @property
    def _path_prefix(self) -> str:
        """URL path prefix for region/language.

        Kobo's API routes are prefixed with /{region}/{language}/.
        """
        return f"/{self.region}/{self.language}"

    @property
    def _headers(self) -> dict[str, str]:
        """HTTP headers required for API requests.

        Includes XMLHttpRequest header to indicate AJAX request,
        which is required by Kobo's API endpoints.
        """
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
        """Get or create the HTTP client (lazy initialization)."""
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
        """Close the HTTP client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "KoboClient":
        """Context manager entry - returns self for use in with statement."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - ensures client is closed."""
        self.close()

    def list_notebooks(self) -> list[NotebookListItem]:
        """List all notebooks from the user's library.

        Fetches the notebooks page from Kobo's web portal and parses
        the HTML to extract notebook information.

        Returns:
            List of notebook items with basic info (ID, title, preview status).

        Raises:
            AuthenticationError: If cookies are invalid or expired.
            KoboClientError: If the request fails for other reasons.
        """
        url = f"{self._path_prefix}/library/notebooks"

        def do_request() -> httpx.Response:
            response = self.client.get(url)
            response.raise_for_status()
            return response

        try:
            response = _retry_request(do_request, max_retries=self.max_retries)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Your browser cookies may have expired. "
                    "Please log into kobo.com in your browser and run 'kobo-md auth login' again."
                ) from e
            raise KoboClientError(f"Failed to list notebooks: {e}") from e

        return parse_notebook_list_html(response.text)

    def get_notebook_metadata(self, notebook_id: str) -> NotebookMetadata:
        """Get detailed metadata for a specific notebook.

        Args:
            notebook_id: UUID of the notebook (e.g., "12345678-1234-1234-1234-123456789abc").

        Returns:
            Notebook metadata including title, page count, content type, and timestamps.

        Raises:
            ValueError: If notebook_id is not a valid UUID.
            NotFoundError: If the notebook does not exist.
            AuthenticationError: If cookies are invalid or expired.
            KoboClientError: If the request fails for other reasons.
        """
        _validate_notebook_id(notebook_id)

        url = f"{self._path_prefix}/Library/GetNotebookMetadata"
        params = {"notebookId": notebook_id}

        def do_request() -> httpx.Response:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response

        try:
            response = _retry_request(do_request, max_retries=self.max_retries)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Please refresh your browser cookies."
                ) from e
            if e.response.status_code == 404:
                raise NotFoundError(f"Notebook not found: {notebook_id}") from e
            raise KoboClientError(f"Failed to get notebook metadata: {e}") from e

        return parse_notebook_metadata(response.json())

    def get_notebook_page(
        self, notebook_id: str, page: int, etag: str
    ) -> NotebookPage:
        """Get content for a specific notebook page.

        The page content includes both raw HTML and extracted text.
        The etag parameter is required for cache validation by Kobo's API.

        Args:
            notebook_id: UUID of the notebook.
            page: 0-indexed page number.
            etag: ETag from notebook metadata (used for cache validation).

        Returns:
            Page content with HTML and extracted text.

        Raises:
            ValueError: If notebook_id is not a valid UUID or page is negative.
            NotFoundError: If the notebook or page does not exist.
            KoboClientError: If the request fails.
        """
        _validate_notebook_id(notebook_id)
        if page < 0:
            raise ValueError(f"Page number must be non-negative, got: {page}")

        url = f"{self._path_prefix}/Library/GetNotebookContent"
        # ETag needs to be URL-encoded - Kobo expects the quoted format
        encoded_etag = quote(etag, safe="")
        params = {
            "notebookId": notebook_id,
            "page": str(page),
            "etag": encoded_etag,
        }

        def do_request() -> httpx.Response:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response

        try:
            response = _retry_request(do_request, max_retries=self.max_retries)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NotFoundError(
                    f"Page {page} not found in notebook {notebook_id}"
                ) from e
            raise KoboClientError(f"Failed to get notebook page: {e}") from e

        return parse_notebook_content(response.json(), page)

    def get_all_notebook_pages(
        self, notebook_id: str, metadata: NotebookMetadata | None = None
    ) -> list[NotebookPage]:
        """Get all pages from a notebook.

        Convenience method that fetches all pages sequentially.
        For large notebooks, consider using get_notebook_page() with
        progress tracking instead.

        Args:
            notebook_id: UUID of the notebook.
            metadata: Optional pre-fetched metadata. If None, metadata
                will be fetched automatically.

        Returns:
            List of all pages in order.

        Raises:
            ValueError: If notebook_id is not a valid UUID.
            NotFoundError: If the notebook does not exist.
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

        Returns the notebook's cover/preview image as PNG bytes.

        Args:
            notebook_id: UUID of the notebook.
            etag: ETag from notebook metadata.

        Returns:
            Image bytes (PNG format).

        Raises:
            ValueError: If notebook_id is not a valid UUID.
            NotFoundError: If the notebook does not exist.
            KoboClientError: If the request fails.
        """
        _validate_notebook_id(notebook_id)

        url = f"{self._path_prefix}/Library/GetNotebookThumbnailImage"
        encoded_etag = quote(etag, safe="")
        params = {
            "notebookId": notebook_id,
            "etag": encoded_etag,
        }

        def do_request() -> httpx.Response:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response

        try:
            response = _retry_request(do_request, max_retries=self.max_retries)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NotFoundError(f"Thumbnail not found for notebook: {notebook_id}") from e
            raise KoboClientError(f"Failed to get notebook thumbnail: {e}") from e

        return response.content
