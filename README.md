# kobo-md

**Export Kobo Sage Advanced Notebooks to Obsidian-compatible Markdown**

A command-line tool for extracting handwritten notes and sketches from the Kobo web portal and converting them to clean, organized Markdown files for use with Obsidian or any Markdown-based note-taking system.

## Features

- **Kobo Integration**: Seamlessly connects to your Kobo account via browser cookies (Firefox, Chrome, Chromium)
- **Advanced Notebook Support**: Extracts content from Kobo Sage "Advanced Notebooks" including handwritten text
- **Text Extraction**: Converts handwritten content to searchable text
- **Markdown Conversion**: Generates clean, properly formatted Markdown with YAML frontmatter
- **Obsidian Integration**:
  - Vault-aware output paths
  - Automatic wikilink suggestions based on existing notes
  - Daily notes integration with customizable path patterns
  - Tag suggestions from existing vault taxonomy
- **Optional AI Enhancement**:
  - Text cleanup and formatting improvements
  - Intelligent wikilink suggestions for proper nouns and concepts
  - Tag recommendations based on content
  - Support for Anthropic (Claude) and OpenAI APIs
- **Batch Processing**: Export single notebooks or all notebooks at once
- **Flexible Output**: Configure output paths, enable dry-run mode, interactive confirmation
- **Rich CLI**: Beautiful terminal output with progress indicators and tables

## Requirements

- **Python**: 3.11 or higher
- **Kobo Account**: An active Kobo account with notebooks created on Kobo Sage
- **Browser**: Firefox or Chrome/Chromium (for cookie extraction)
- **Optional**: Anthropic or OpenAI API key for AI enhancement features

## Installation

### Basic Installation

Install the core package without AI features:

```bash
# Clone the repository
git clone https://github.com/lukepatrick/kobo-notebooks-markdown.git
cd kobo-notebooks-markdown

# Install with pip
pip install -e .
```

### With AI Features

To enable AI-powered text cleanup and wikilink suggestions:

```bash
pip install -e ".[ai]"
```

This installs additional dependencies:
- `anthropic` - For Claude API integration
- `openai` - For OpenAI API integration

### Development Installation

For contributors and developers:

```bash
pip install -e ".[dev]"
```

This includes testing and linting tools:
- `pytest` and `pytest-asyncio` - Testing framework
- `ruff` - Fast Python linter
- `mypy` - Static type checker

## Quick Start

### 1. Authenticate with Kobo

First, log in to [kobo.com](https://www.kobo.com) in your browser (Firefox or Chrome). Then extract your authentication cookies:

```bash
# For Firefox (default)
kobo-md auth login

# For Chrome
kobo-md auth login --browser chrome

# Verify authentication
kobo-md auth status
```

Cookies are securely stored in `~/.config/kobo-md/cookies.json`.

### 2. List Your Notebooks

View all notebooks in your Kobo library:

```bash
kobo-md list
```

This displays a table with notebook IDs, titles, and preview availability.

### 3. Export a Notebook

Export a specific notebook to Markdown:

```bash
# Export by ID (supports prefix matching)
kobo-md fetch abc12345

# Export all notebooks
kobo-md fetch --all

# Export to custom location
kobo-md fetch abc12345 --output ~/Documents/Notes
```

### 4. Enable AI Enhancement (Optional)

For improved text quality and automatic wikilinks, enable AI processing:

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...

# Export with AI processing
kobo-md fetch abc12345 --ai

# Configure AI settings
export KOBO_MD_AI_ENABLED=true
export KOBO_MD_AI_PROVIDER=anthropic
export KOBO_MD_AI_MODEL=claude-sonnet-4-20250514
```

## CLI Reference

### Global Options

```bash
kobo-md --version              # Show version
kobo-md --help                 # Show help message
```

### Authentication Commands

#### `kobo-md auth login`

Extract and save authentication cookies from your browser.

**Options:**
- `--browser, -b TEXT`: Browser to extract from (`firefox`, `chrome`, `chromium`) [default: firefox]

**Example:**
```bash
kobo-md auth login --browser chrome
```

You must be logged in to kobo.com in your browser before running this command.

#### `kobo-md auth status`

Check current authentication status and validate session.

**Example:**
```bash
kobo-md auth status
# Output: Session valid! Found 5 notebooks.
```

#### `kobo-md auth clear`

Clear saved authentication cookies.

**Example:**
```bash
kobo-md auth clear
```

### Notebook Commands

#### `kobo-md list`

List all notebooks in your Kobo library.

**Example:**
```bash
kobo-md list
```

**Output:**
```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ ID          ┃ Title            ┃ Preview ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ abc12345... │ My Reading Notes │   Yes   │
│ def67890... │ Project Ideas    │   Yes   │
└─────────────┴──────────────────┴─────────┘
```

#### `kobo-md fetch`

Fetch and export notebooks to Markdown.

**Usage:**
```bash
kobo-md fetch [NOTEBOOK_ID] [OPTIONS]
```

**Arguments:**
- `NOTEBOOK_ID`: Notebook ID to fetch (supports prefix matching). Omit when using `--all`.

**Options:**
- `--all, -a`: Fetch all notebooks
- `--output, -o PATH`: Output directory (overrides config)
- `--overwrite, -f`: Overwrite existing files
- `--ai / --no-ai`: Enable/disable AI processing (overrides config)
- `--provider, -p TEXT`: AI provider: `anthropic`, `openai`
- `--dry-run, -n`: Preview without writing to vault
- `--confirm, -c`: Ask for confirmation before each write
- `--daily-notes, -d`: Append to today's daily note instead of creating files
- `--daily-pattern TEXT`: Daily notes path pattern (e.g., `Daily/{year}/{month_name}/{day}.md`)

**Examples:**

```bash
# Export single notebook
kobo-md fetch abc12345

# Export all notebooks
kobo-md fetch --all

# Export with AI enhancement
kobo-md fetch abc12345 --ai --provider anthropic

# Dry run to preview output
kobo-md fetch abc12345 --dry-run

# Interactive confirmation
kobo-md fetch --all --confirm

# Append to today's daily note
kobo-md fetch abc12345 --daily-notes

# Custom daily note pattern
kobo-md fetch abc12345 --daily-notes --daily-pattern "Journal/{year}-{month:02d}-{day:02d}.md"

# Overwrite existing files
kobo-md fetch abc12345 --overwrite
```

#### `kobo-md process`

Process an existing Markdown file with AI to add wikilinks and improve formatting.

**Usage:**
```bash
kobo-md process FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to Markdown file to process

**Options:**
- `--output, -o PATH`: Output file (default: overwrite input)
- `--provider, -p TEXT`: AI provider: `anthropic`, `openai`
- `--dry-run, -n`: Show changes without writing

**Examples:**

```bash
# Process a file with AI
kobo-md process notes.md

# Preview changes without modifying
kobo-md process notes.md --dry-run

# Save to new file
kobo-md process notes.md --output notes-enhanced.md

# Use specific provider
kobo-md process notes.md --provider openai
```

### Utility Commands

#### `kobo-md scan-vault`

Scan Obsidian vault and show statistics about notes, tags, and aliases.

**Options:**
- `--vault, -v PATH`: Vault path (uses config default if not specified)

**Example:**
```bash
kobo-md scan-vault
kobo-md scan-vault --vault ~/Documents/MyVault
```

#### `kobo-md config`

Show current configuration settings.

**Options:**
- `--show, -s`: Show current configuration (default behavior)

**Example:**
```bash
kobo-md config --show
```

**Output:**
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting           ┃ Value                        ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Browser           │ firefox                      │
│ Kobo Region       │ us                           │
│ Vault Path        │ /home/user/Documents/Vault   │
│ Output Dir        │ kobo                         │
│ AI Enabled        │ False                        │
│ AI Provider       │ anthropic                    │
└───────────────────┴──────────────────────────────┘
```

## Configuration

`kobo-md` can be configured via environment variables or a `.env` file in your project directory.

### Environment Variables

All settings use the `KOBO_MD_` prefix:

#### Authentication & Browser

```bash
export KOBO_MD_BROWSER=firefox              # Browser: firefox, chrome, chromium
export KOBO_MD_KOBO_REGION=us               # Kobo region code
```

#### Output Paths

```bash
export KOBO_MD_VAULT_PATH=~/Documents/Vault # Path to Obsidian vault
export KOBO_MD_OUTPUT_DIR=kobo              # Output directory within vault
```

#### Daily Notes

```bash
export KOBO_MD_DAILY_NOTES_PATTERN="Daily/{year}/{month:02d}-{month_name}/{year}-{month:02d}-{day:02d}.md"
```

The daily notes pattern supports the following variables:
- `{year}` - Four-digit year (e.g., 2024)
- `{month}` - Month number without padding (1-12)
- `{month:02d}` - Month number with zero padding (01-12)
- `{month_name}` - Full month name (e.g., January)
- `{day}` - Day without padding (1-31)
- `{day:02d}` - Day with zero padding (01-31)

**Examples:**
- `Daily/{year}-{month:02d}-{day:02d}.md` → `Daily/2024-01-15.md`
- `Journal/{year}/{month_name}/{day}.md` → `Journal/2024/January/15.md`
- `Notes/{year}/Week {week}/{year}-{month:02d}-{day:02d}.md`

#### AI Settings

```bash
export KOBO_MD_AI_ENABLED=true              # Enable AI processing by default
export KOBO_MD_AI_PROVIDER=anthropic        # Provider: anthropic, openai
export KOBO_MD_AI_MODEL=claude-sonnet-4-20250514  # Model name

# API Keys (required for AI features)
export ANTHROPIC_API_KEY=sk-ant-...         # Anthropic API key
export OPENAI_API_KEY=sk-...                # OpenAI API key
```

#### Processing Options

```bash
export KOBO_MD_SUGGEST_WIKILINKS=true       # Suggest wikilinks to existing notes
export KOBO_MD_CLEANUP_TEXT=true            # Clean up text with AI
export KOBO_MD_SKIP_EXISTING=true           # Skip existing files
```

### Using a .env File

Create a `.env` file in your project directory or home directory:

```bash
# .env
KOBO_MD_VAULT_PATH=/home/user/Documents/Vault
KOBO_MD_OUTPUT_DIR=kobo
KOBO_MD_AI_ENABLED=true
KOBO_MD_AI_PROVIDER=anthropic
KOBO_MD_AI_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...
```

### Configuration Priority

Settings are loaded in this order (later overrides earlier):
1. Default values
2. `.env` file
3. Environment variables
4. Command-line flags

## Optional AI Features

The AI enhancement features are entirely optional but can significantly improve the quality of exported notes.

### What AI Processing Does

When enabled with `--ai`, the tool will:

1. **Text Cleanup**:
   - Fix OCR errors from handwriting recognition
   - Improve sentence structure and formatting
   - Correct spelling and grammar issues
   - Preserve original meaning and content

2. **Wikilink Suggestions**:
   - Scan your vault to understand existing notes
   - Identify proper nouns, book titles, concepts
   - Suggest `[[wikilinks]]` to existing notes
   - Mark potential new note topics

3. **Tag Recommendations**:
   - Analyze note content and context
   - Suggest relevant tags from your existing taxonomy
   - Recommend new tags for uncategorized content

### Setup

#### Option 1: Anthropic (Claude)

```bash
# Install AI dependencies
pip install -e ".[ai]"

# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Use with fetch command
kobo-md fetch abc12345 --ai --provider anthropic
```

Get an API key from [Anthropic Console](https://console.anthropic.com/).

#### Option 2: OpenAI

```bash
# Install AI dependencies
pip install -e ".[ai]"

# Set API key
export OPENAI_API_KEY=sk-...

# Use with fetch command
kobo-md fetch abc12345 --ai --provider openai
```

Get an API key from [OpenAI Platform](https://platform.openai.com/).

### Vault-Aware Suggestions

The AI processor scans your Obsidian vault before processing to provide contextual suggestions:

```bash
# The tool will automatically:
# 1. Scan your vault for existing notes
# 2. Build an index of note titles and tags
# 3. Use this context when suggesting wikilinks
```

This means suggestions are tailored to YOUR vault structure and existing notes.

### Processing Existing Files

You can also process existing Markdown files:

```bash
# Add wikilinks and cleanup to any Markdown file
kobo-md process my-notes.md --ai

# Preview changes first
kobo-md process my-notes.md --ai --dry-run
```

### Cost Considerations

AI processing uses API calls which have associated costs:
- Anthropic Claude: ~$0.003 per notebook (varies by size)
- OpenAI GPT-4: ~$0.01 per notebook (varies by size)

Use `--dry-run` to preview before committing to API usage.

## Obsidian Integration

### Output Format

Exported notebooks are saved as Markdown files with YAML frontmatter:

```markdown
---
title: My Reading Notes
notebook_id: abc12345-67890
created: 2024-01-15T10:30:00Z
modified: 2024-01-15T14:22:00Z
tags:
  - kobo
  - reading
  - notes
---

# My Reading Notes

Content of the notebook with [[wikilinks]] to other notes...

Tags: #reading #book-notes
```

### Vault Structure

By default, notebooks are saved to `{vault}/kobo/`:

```
Vault/
├── kobo/
│   ├── My Reading Notes.md
│   ├── Project Ideas.md
│   └── Book Highlights.md
├── Daily/
│   └── 2024/
│       └── January/
│           └── 2024-01-15.md
└── ...
```

Customize the output directory with:
```bash
export KOBO_MD_OUTPUT_DIR=Imported/Kobo
```

### Daily Notes Integration

Append notebook content to your daily note instead of creating separate files:

```bash
# Append to today's daily note
kobo-md fetch abc12345 --daily-notes

# Result: Adds to Daily/2024/January/2024-01-15.md
```

The daily note path pattern is configurable via `KOBO_MD_DAILY_NOTES_PATTERN`.

### Wikilinks

When AI processing is enabled, the tool suggests wikilinks to existing notes:

```markdown
# Before
I read about quantum mechanics and Einstein's theories today.

# After (with --ai)
I read about [[Quantum Mechanics]] and [[Albert Einstein]]'s theories today.
```

The tool distinguishes between:
- **Existing wikilinks** (green): Links to notes already in your vault
- **New wikilinks** (yellow): Suggested topics for new notes

## Development

### Project Structure

```
kobo-md/
├── src/
│   └── kobo_md/
│       ├── __init__.py          # Package version and metadata
│       ├── __main__.py          # Module entry point
│       ├── cli.py               # Typer CLI commands and interface
│       ├── auth/                # Browser cookie extraction
│       │   ├── __init__.py
│       │   └── cookies.py       # Firefox/Chrome cookie handling
│       ├── kobo/                # Kobo API client
│       │   ├── __init__.py
│       │   ├── client.py        # HTTP client for Kobo API
│       │   ├── models.py        # Pydantic models for API responses
│       │   └── parser.py        # HTML/text parsing
│       ├── processor/           # Text processing and AI
│       │   ├── __init__.py
│       │   ├── processor.py     # Main processing pipeline
│       │   └── llm.py           # LLM integration (Anthropic/OpenAI)
│       ├── obsidian/            # Obsidian integration
│       │   ├── __init__.py
│       │   ├── writer.py        # Markdown file output
│       │   ├── vault.py         # Vault scanning and indexing
│       │   └── linker.py        # Wikilink generation
│       └── config/              # Configuration management
│           ├── __init__.py
│           └── settings.py      # Pydantic settings
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest fixtures
│   └── ...
├── pyproject.toml               # Project metadata and dependencies
├── LICENSE                      # MIT License
└── README.md                    # This file
```

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/lukepatrick/kobo-notebooks-markdown.git
cd kobo-notebooks-markdown

# Install development dependencies
pip install -e ".[dev,ai]"

# Run tests
pytest

# Run linter
ruff check src tests

# Run type checker
mypy src

# Auto-fix linting issues
ruff check --fix src tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kobo_md

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Code Quality

The project uses:
- **ruff**: Fast Python linter (replaces flake8, isort, etc.)
- **mypy**: Static type checking with strict mode
- **pytest**: Testing framework with async support

All code must pass type checking and linting before submission.

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`pytest && ruff check src tests && mypy src`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8 (enforced by ruff)
- Use type hints for all functions
- Write docstrings for public APIs
- Keep functions focused and testable
- Prefer explicit over implicit

## Troubleshooting

### Authentication Issues

**Problem**: "Not authenticated" error

**Solution**:
1. Ensure you're logged in to kobo.com in your browser
2. Run `kobo-md auth login` again
3. Try a different browser with `--browser chrome`
4. Check that cookies weren't cleared by browser settings

### Empty Notebooks

**Problem**: Notebook shows as empty after export

**Solution**:
- Ensure the notebook is an "Advanced Notebook" (created on Kobo Sage)
- Regular highlights/annotations are not supported (only Advanced Notebooks)
- Check that `can_be_previewed` is "Yes" in `kobo-md list` output

### AI Processing Errors

**Problem**: AI processing fails or produces errors

**Solution**:
1. Verify API key is set correctly:
   ```bash
   echo $ANTHROPIC_API_KEY  # Should show sk-ant-...
   ```
2. Check that `[ai]` dependencies are installed:
   ```bash
   pip install -e ".[ai]"
   ```
3. Verify API key has sufficient credits/quota
4. Use `--provider openai` to try alternative provider

### Permission Errors

**Problem**: Cannot write to output directory

**Solution**:
- Check that vault path exists and is writable
- Verify output directory path is correct
- Use `--output` flag to specify alternative location

## Privacy & Security

- **Credentials**: Your Kobo cookies are stored locally in `~/.config/kobo-md/cookies.json`
- **API Keys**: Never committed to git (add to `.gitignore`)
- **Data**: All processing is done locally except optional AI features
- **Network**: Only connects to:
  - `kobo.com` (for notebook data)
  - `api.anthropic.com` or `api.openai.com` (only when using `--ai`)

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Luke

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for the beautiful CLI
- Uses [Pydantic](https://pydantic.dev/) for robust data validation
- Powered by [httpx](https://www.python-httpx.org/) for async HTTP
- Text processing by [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- Cookie extraction via [browser-cookie3](https://github.com/borisbabic/browser_cookie3)

## Support

- **Issues**: [GitHub Issues](https://github.com/lukepatrick/kobo-notebooks-markdown/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lukepatrick/kobo-notebooks-markdown/discussions)


