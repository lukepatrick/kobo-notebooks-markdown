# kobo-md

Read Kobo Notebooks and Parse to Markdown

## Overview

kobo-md is a command-line tool for extracting annotations and highlights from Kobo e-readers and converting them to Markdown format. It is designed to integrate with note-taking applications like Obsidian.

## Features

- Sync annotations from Kobo cloud
- Export highlights and notes to Markdown
- Obsidian-compatible output format
- Configurable templates and output structure

## Installation

### From source (development)

```bash
# Clone the repository
git clone https://github.com/lukepatrick/kobo-notebooks-markdown.git
cd kobo-notebooks-markdown

# Install with uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### Optional AI features

To enable AI-powered features for summarization and organization:

```bash
uv pip install -e ".[ai]"
```

## Usage

```bash
# Show help
kobo-md --help

# Show version
kobo-md --version

# List books with annotations
kobo-md list-books

# Sync all annotations
kobo-md sync --output ./notes

# Export a specific book
kobo-md export <book-id> --output ./notes/book.md

# Manage configuration
kobo-md config --init
kobo-md config --show
```

## Development

### Setup

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src tests

# Run type checker
mypy src
```

### Project Structure

```
src/kobo_md/
    __init__.py       # Package version and metadata
    __main__.py       # Module entry point
    cli.py            # Typer CLI commands
    auth/             # Authentication handling
    kobo/             # Kobo API client
    processor/        # Annotation processing
    obsidian/         # Markdown output formatting
    config/           # Configuration management
tests/
    conftest.py       # Pytest fixtures
```

## License

MIT License - see LICENSE file for details.
