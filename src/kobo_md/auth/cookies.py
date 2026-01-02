"""Browser cookie extraction for Kobo authentication."""

import contextlib
import json
import os
import stat
from http.cookiejar import CookieJar
from pathlib import Path

import browser_cookie3
from pydantic import BaseModel, ValidationError


class KoboCookies(BaseModel):
    """Required cookies for Kobo authentication."""

    kobo_session: str
    session: str
    session_id: str | None = None

    def to_header(self) -> str:
        """Convert cookies to a Cookie header value."""
        parts = [
            f"KoboSession={self.kobo_session}",
            f"session={self.session}",
        ]
        if self.session_id:
            parts.append(f"sessionId={self.session_id}")
        return "; ".join(parts)

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for httpx."""
        cookies = {
            "KoboSession": self.kobo_session,
            "session": self.session,
        }
        if self.session_id:
            cookies["sessionId"] = self.session_id
        return cookies


class CookieError(Exception):
    """Error extracting cookies from browser."""

    pass


def extract_firefox_cookies(domain: str = "kobo.com") -> KoboCookies:
    """Extract Kobo cookies from Firefox.

    Args:
        domain: Domain to extract cookies for.

    Returns:
        KoboCookies with required authentication cookies.

    Raises:
        CookieError: If cookies cannot be extracted.
    """
    try:
        cj: CookieJar = browser_cookie3.firefox(domain_name=domain)
        return _extract_from_cookiejar(cj, domain)
    except browser_cookie3.BrowserCookieError as e:
        raise CookieError(f"Failed to extract Firefox cookies: {e}") from e
    except PermissionError as e:
        raise CookieError(
            f"Permission denied accessing Firefox cookies: {e}. "
            "Try closing Firefox first."
        ) from e


def extract_chrome_cookies(domain: str = "kobo.com") -> KoboCookies:
    """Extract Kobo cookies from Chrome/Chromium.

    Args:
        domain: Domain to extract cookies for.

    Returns:
        KoboCookies with required authentication cookies.

    Raises:
        CookieError: If cookies cannot be extracted.
    """
    try:
        cj: CookieJar = browser_cookie3.chrome(domain_name=domain)
        return _extract_from_cookiejar(cj, domain)
    except browser_cookie3.BrowserCookieError as e:
        raise CookieError(f"Failed to extract Chrome cookies: {e}") from e
    except Exception as e:
        raise CookieError(f"Failed to extract Chrome cookies: {e}") from e


def _extract_from_cookiejar(cj: CookieJar, domain: str) -> KoboCookies:
    """Extract required cookies from a CookieJar.

    Args:
        cj: CookieJar containing browser cookies.
        domain: Domain to filter cookies.

    Returns:
        KoboCookies with required authentication cookies.

    Raises:
        CookieError: If required cookies are missing.
    """
    cookies: dict[str, str] = {}

    for cookie in cj:
        if domain in cookie.domain:
            if cookie.name == "KoboSession":
                cookies["kobo_session"] = cookie.value
            elif cookie.name == "session":
                cookies["session"] = cookie.value
            elif cookie.name == "sessionId":
                cookies["session_id"] = cookie.value

    if "kobo_session" not in cookies:
        raise CookieError(
            "KoboSession cookie not found. "
            "Please log in to kobo.com in your browser first."
        )

    if "session" not in cookies:
        raise CookieError(
            "session cookie not found. "
            "Please log in to kobo.com in your browser first."
        )

    return KoboCookies(**cookies)


def extract_cookies(browser: str = "firefox", domain: str = "kobo.com") -> KoboCookies:
    """Extract Kobo cookies from the specified browser.

    Args:
        browser: Browser to extract from ("firefox", "chrome", "chromium").
        domain: Domain to extract cookies for.

    Returns:
        KoboCookies with required authentication cookies.

    Raises:
        CookieError: If cookies cannot be extracted.
        ValueError: If browser is not supported.
    """
    browser = browser.lower()

    if browser == "firefox":
        return extract_firefox_cookies(domain)
    elif browser in ("chrome", "chromium"):
        return extract_chrome_cookies(domain)
    else:
        raise ValueError(f"Unsupported browser: {browser}. Use 'firefox' or 'chrome'.")


def save_cookies(cookies: KoboCookies, path: Path) -> None:
    """Save cookies to a file for reuse.

    Cookies are stored with restricted file permissions (0600) to prevent
    unauthorized access by other users on the system.

    Args:
        cookies: Cookies to save.
        path: Path to save cookies to.
    """
    # Create parent directory with restricted permissions (0700)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Best effort on systems that don't support chmod
    with contextlib.suppress(OSError):
        os.chmod(path.parent, stat.S_IRWXU)  # 0700: owner rwx only

    # Write file with restricted permissions
    # Use atomic write pattern: write to temp, then rename
    temp_path = path.with_suffix(".tmp")
    try:
        temp_path.write_text(cookies.model_dump_json(indent=2))
        # Set restrictive permissions before the file is in final location
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600: owner rw only
        temp_path.rename(path)
    except OSError:
        # Fallback for systems where chmod fails
        path.write_text(cookies.model_dump_json(indent=2))
        with contextlib.suppress(OSError):
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        # Clean up temp file if it still exists
        if temp_path.exists():
            temp_path.unlink()


def load_cookies(path: Path) -> KoboCookies | None:
    """Load cookies from a file.

    Args:
        path: Path to load cookies from.

    Returns:
        KoboCookies if file exists and is valid, None otherwise.
    """
    if not path.exists():
        return None

    try:
        return KoboCookies.model_validate_json(path.read_text())
    except (json.JSONDecodeError, ValidationError, PermissionError, OSError):
        return None
