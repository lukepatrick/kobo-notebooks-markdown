"""LLM integration for text processing and wikilink suggestions."""

import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


def _retry_api_call(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Retry an API call with exponential backoff.

    Args:
        func: Function to call.
        max_retries: Maximum retry attempts.
        base_delay: Initial delay between retries.

    Returns:
        Result of the function.

    Raises:
        Exception: The last exception if all retries fail.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_str = str(e).lower()
            # Retry on rate limits, server errors, timeouts
            if any(term in error_str for term in ["rate", "limit", "429", "500", "502", "503", "timeout", "overloaded"]):
                last_error = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                continue
            # Don't retry other errors (auth, bad request, etc.)
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Retry failed without error")


class ProcessedText(BaseModel):
    """Result of LLM text processing."""

    cleaned_text: str
    suggested_wikilinks: list[str]
    suggested_tags: list[str]
    confidence: float = 1.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def process_text(
        self,
        text: str,
        existing_notes: list[str] | None = None,
        existing_tags: list[str] | None = None,
    ) -> ProcessedText:
        """Process text with the LLM.

        Args:
            text: Raw notebook text to process.
            existing_notes: List of existing note titles in the vault.
            existing_tags: List of existing tags in the vault.

        Returns:
            ProcessedText with cleaned text and suggestions.
        """
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider for text processing."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        """Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Model to use.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.model = model
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise ImportError(
                    "anthropic package required. Install with: pip install 'kobo-md[ai]'"
                ) from e
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def process_text(
        self,
        text: str,
        existing_notes: list[str] | None = None,
        existing_tags: list[str] | None = None,
    ) -> ProcessedText:
        """Process text with Claude."""
        system_prompt = self._build_system_prompt(existing_notes, existing_tags)
        user_prompt = self._build_user_prompt(text)

        def do_request() -> Any:
            return self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

        response = _retry_api_call(do_request)
        return self._parse_response(response.content[0].text, text)

    def _build_system_prompt(
        self,
        existing_notes: list[str] | None,
        existing_tags: list[str] | None,
    ) -> str:
        """Build the system prompt for text processing."""
        prompt = """You are an expert at processing handwritten notes that have been converted to text.
Your task is to:
1. Clean up any recognition errors or formatting issues
2. Identify proper nouns, titles, concepts, and other terms that should become [[wikilinks]]
3. Suggest relevant tags for the content

Guidelines for wikilinks:
- People's names: [[John Smith]], [[Marcus Aurelius]]
- Book/article titles: [[The Great Gatsby]], [[Deep Work]]
- Concepts and ideas: [[Stoicism]], [[Spaced Repetition]]
- Places and organizations: [[MIT]], [[San Francisco]]
- Projects or specific topics mentioned

Guidelines for cleanup:
- Fix obvious OCR/handwriting recognition errors
- Preserve the original meaning and tone
- Keep the author's voice and style
- Fix punctuation and capitalization issues
- Don't add content that wasn't there

Output format:
Return your response in this exact format:

<cleaned_text>
[The cleaned up text with [[wikilinks]] inserted where appropriate]
</cleaned_text>

<wikilinks>
[Comma-separated list of all wikilink targets you suggested, without brackets]
</wikilinks>

<tags>
[Comma-separated list of suggested tags, without # symbol]
</tags>
"""

        if existing_notes:
            # Limit to avoid token overflow
            notes_sample = existing_notes[:100]
            prompt += f"""

EXISTING NOTES IN VAULT (prefer linking to these when relevant):
{', '.join(notes_sample)}
"""

        if existing_tags:
            tags_sample = existing_tags[:50]
            prompt += f"""

EXISTING TAGS IN VAULT (prefer using these when relevant):
{', '.join(tags_sample)}
"""

        return prompt

    def _build_user_prompt(self, text: str) -> str:
        """Build the user prompt with the text to process."""
        return f"""Please process the following notebook text:

<notebook_text>
{text}
</notebook_text>

Clean up the text, add appropriate [[wikilinks]], and suggest tags."""

    def _parse_response(self, response: str, original_text: str) -> ProcessedText:
        """Parse the LLM response into structured output."""
        cleaned_text = original_text
        wikilinks: list[str] = []
        tags: list[str] = []

        # Extract cleaned text
        if "<cleaned_text>" in response and "</cleaned_text>" in response:
            start = response.index("<cleaned_text>") + len("<cleaned_text>")
            end = response.index("</cleaned_text>")
            cleaned_text = response[start:end].strip()

        # Extract wikilinks
        if "<wikilinks>" in response and "</wikilinks>" in response:
            start = response.index("<wikilinks>") + len("<wikilinks>")
            end = response.index("</wikilinks>")
            links_str = response[start:end].strip()
            if links_str:
                wikilinks = [link.strip() for link in links_str.split(",") if link.strip()]

        # Extract tags
        if "<tags>" in response and "</tags>" in response:
            start = response.index("<tags>") + len("<tags>")
            end = response.index("</tags>")
            tags_str = response[start:end].strip()
            if tags_str:
                tags = [tag.strip().lstrip("#") for tag in tags_str.split(",") if tag.strip()]

        return ProcessedText(
            cleaned_text=cleaned_text,
            suggested_wikilinks=wikilinks,
            suggested_tags=tags,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI provider for text processing."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        """Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: Model to use.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.model = model
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                import openai
            except ImportError as e:
                raise ImportError(
                    "openai package required. Install with: pip install 'kobo-md[ai]'"
                ) from e
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def process_text(
        self,
        text: str,
        existing_notes: list[str] | None = None,
        existing_tags: list[str] | None = None,
    ) -> ProcessedText:
        """Process text with OpenAI."""
        system_prompt = self._build_system_prompt(existing_notes, existing_tags)
        user_prompt = self._build_user_prompt(text)

        def do_request() -> Any:
            return self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        response = _retry_api_call(do_request)
        return self._parse_response(response.choices[0].message.content or "", text)

    # Reuse the same prompt building and parsing logic
    _build_system_prompt = AnthropicProvider._build_system_prompt
    _build_user_prompt = AnthropicProvider._build_user_prompt
    _parse_response = AnthropicProvider._parse_response


class ClaudeCodeProvider(LLMProvider):
    """Claude Code CLI provider for text processing.

    Uses the Claude Code CLI as a subprocess, leveraging existing
    Claude Code authentication instead of requiring a separate API key.
    """

    def __init__(self, model: str | None = None):
        """Initialize the Claude Code provider.

        Args:
            model: Model to use (optional, uses Claude Code default if not specified).
        """
        self.model = model
        self._verify_claude_cli()

    def _verify_claude_cli(self) -> None:
        """Verify that claude CLI is available."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("claude CLI returned non-zero exit code")
        except FileNotFoundError:
            raise RuntimeError(
                "Claude Code CLI not found. Install it from: "
                "https://docs.anthropic.com/en/docs/claude-code"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code CLI timed out during version check")

    def process_text(
        self,
        text: str,
        existing_notes: list[str] | None = None,
        existing_tags: list[str] | None = None,
    ) -> ProcessedText:
        """Process text using Claude Code CLI."""
        prompt = self._build_prompt(text, existing_notes, existing_tags)

        # Build command
        cmd = ["claude", "-p", "--output-format", "json"]
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout for processing
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                raise RuntimeError(f"Claude Code CLI error: {error_msg}")

            # Parse JSON response
            try:
                response_data = json.loads(result.stdout)
                response_text = response_data.get("result", "")
            except json.JSONDecodeError:
                # Fall back to raw output if not JSON
                response_text = result.stdout

            return self._parse_response(response_text, text)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code CLI timed out during processing")

    def _build_prompt(
        self,
        text: str,
        existing_notes: list[str] | None,
        existing_tags: list[str] | None,
    ) -> str:
        """Build a combined prompt for Claude Code CLI."""
        prompt = """You are an expert at processing handwritten notes that have been converted to text.
Your task is to:
1. Clean up any recognition errors or formatting issues
2. Identify proper nouns, titles, concepts, and other terms that should become [[wikilinks]]
3. Suggest relevant tags for the content

Guidelines for wikilinks:
- People's names: [[John Smith]], [[Marcus Aurelius]]
- Book/article titles: [[The Great Gatsby]], [[Deep Work]]
- Concepts and ideas: [[Stoicism]], [[Spaced Repetition]]
- Places and organizations: [[MIT]], [[San Francisco]]
- Projects or specific topics mentioned

Guidelines for cleanup:
- Fix obvious OCR/handwriting recognition errors
- Preserve the original meaning and tone
- Keep the author's voice and style
- Fix punctuation and capitalization issues
- Don't add content that wasn't there

Output format:
Return your response in this exact format:

<cleaned_text>
[The cleaned up text with [[wikilinks]] inserted where appropriate]
</cleaned_text>

<wikilinks>
[Comma-separated list of all wikilink targets you suggested, without brackets]
</wikilinks>

<tags>
[Comma-separated list of suggested tags, without # symbol]
</tags>
"""

        if existing_notes:
            notes_sample = existing_notes[:100]
            prompt += f"""
EXISTING NOTES IN VAULT (prefer linking to these when relevant):
{', '.join(notes_sample)}
"""

        if existing_tags:
            tags_sample = existing_tags[:50]
            prompt += f"""
EXISTING TAGS IN VAULT (prefer using these when relevant):
{', '.join(tags_sample)}
"""

        prompt += f"""
Please process the following notebook text:

<notebook_text>
{text}
</notebook_text>

Clean up the text, add appropriate [[wikilinks]], and suggest tags."""

        return prompt

    # Reuse the same response parsing logic
    _parse_response = AnthropicProvider._parse_response


def get_llm_provider(
    provider: str = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
) -> LLMProvider:
    """Get an LLM provider instance.

    Args:
        provider: Provider name ("anthropic", "openai", or "claude-code").
        api_key: API key (optional, will use env var if not provided).
            Not used for claude-code provider.
        model: Model to use (optional, will use default if not provided).

    Returns:
        LLMProvider instance.

    Raises:
        ValueError: If provider is not supported.
    """
    if provider == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
        )
    elif provider == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4o",
        )
    elif provider == "claude-code":
        return ClaudeCodeProvider(model=model)
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            "Use 'anthropic', 'openai', or 'claude-code'."
        )
