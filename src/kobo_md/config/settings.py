"""Application configuration and settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and config file."""

    model_config = SettingsConfigDict(
        env_prefix="KOBO_MD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Authentication
    browser: Literal["firefox", "chrome", "chromium"] = "firefox"
    kobo_region: str = Field(default="us", description="Kobo region code")

    # Output paths
    vault_path: Path = Field(
        default=Path.home() / "Documents" / "Vault",
        description="Path to Obsidian vault",
    )
    output_dir: str = Field(
        default="kobo",
        description="Output directory relative to vault",
    )
    daily_notes_pattern: str = Field(
        default="Daily/{year}/{month:02d}-{month_name}/{year}-{month:02d}-{day:02d}.md",
        description="Pattern for daily notes path",
    )

    # AI settings
    ai_enabled: bool = Field(default=False, description="Enable AI processing")
    ai_provider: Literal["anthropic", "openai"] = "anthropic"
    ai_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="AI model to use",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (or set OPENAI_API_KEY env var)",
    )

    # Processing
    suggest_wikilinks: bool = Field(
        default=True,
        description="Suggest wikilinks for proper nouns and titles",
    )
    cleanup_text: bool = Field(
        default=True,
        description="Clean up text with AI",
    )
    skip_existing: bool = Field(
        default=True,
        description="Skip notebooks that already exist in output",
    )

    @property
    def output_path(self) -> Path:
        """Full path to output directory."""
        return self.vault_path / self.output_dir

    @property
    def cookies_path(self) -> Path:
        """Path to cached cookies file."""
        return self.config_dir / "cookies.json"

    @property
    def config_dir(self) -> Path:
        """Path to config directory."""
        config = Path.home() / ".config" / "kobo-md"
        config.mkdir(parents=True, exist_ok=True)
        return config


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
