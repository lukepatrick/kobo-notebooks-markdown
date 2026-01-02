# Kobo Notebooks to Obsidian - Project Plan

## Project Overview

A Python CLI tool that exports Kobo Sage "Advanced Notebooks" from the Kobo web portal and converts them to Obsidian-compatible Markdown with AI-powered cleanup and wikilink suggestions.

---

## Requirements Summary

| Requirement | Decision |
|-------------|----------|
| **Source** | Kobo web portal (kobo.com/library/notebooks) |
| **Content Type** | Advanced Notebooks (text already recognized by Kobo) |
| **Automation Level** | Manual CLI |
| **AI/LLM Use** | Post-processing: cleanup text, suggest [[wikilinks]] |
| **Initial Output** | Dedicated `kobo/` folder in vault |
| **Future Output** | Integration with Daily notes (`Daily/YYYY/MM-Mon/YYYY-MM-DD.md`) |
| **Obsidian Features** | Wikilinks `[[suggested]]` based on content |
| **Authentication** | Browser cookie extraction |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     kobo-notebooks-markdown                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Auth       │    │   Fetcher    │    │   Processor  │       │
│  │   Module     │───▶│   Module     │───▶│   Module     │       │
│  │              │    │              │    │              │       │
│  │ - Cookie     │    │ - List       │    │ - Parse      │       │
│  │   extraction │    │   notebooks  │    │   exports    │       │
│  │ - Session    │    │ - Download   │    │ - LLM        │       │
│  │   management │    │   exports    │    │   cleanup    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                 │                │
│                                                 ▼                │
│                                          ┌──────────────┐       │
│                                          │   Writer     │       │
│                                          │   Module     │       │
│                                          │              │       │
│                                          │ - Markdown   │       │
│                                          │   output     │       │
│                                          │ - Wikilink   │       │
│                                          │   injection  │       │
│                                          │ - Vault      │       │
│                                          │   integration│       │
│                                          └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (MVP)

**Goal:** Fetch notebooks from Kobo web and save as Markdown

#### 1.1 Project Setup
- [ ] Initialize Python project with `pyproject.toml`
- [ ] Set up CLI framework (Typer)
- [ ] Create basic project structure
- [ ] Configure development tools (ruff, pytest)

#### 1.2 Authentication Module
- [ ] Research Kobo web portal authentication mechanism
- [ ] Implement browser cookie extraction (Firefox/Chrome)
- [ ] Session validation and refresh handling
- [ ] Secure credential storage

#### 1.3 Notebook Fetcher
- [ ] Discover Kobo web portal API endpoints
- [ ] List available notebooks
- [ ] Download notebook exports (Text/HTML format)
- [ ] Handle pagination and rate limiting

#### 1.4 Basic Markdown Writer
- [ ] Parse downloaded notebook content
- [ ] Convert to clean Markdown
- [ ] Save to configured output directory
- [ ] Basic frontmatter (date, source, notebook name)

### Phase 2: AI Enhancement

**Goal:** Intelligent text processing and Obsidian integration

#### 2.1 LLM Integration
- [ ] Configure LLM provider (Claude/OpenAI)
- [ ] Implement text cleanup prompts
- [ ] Handle API errors and rate limits
- [ ] Optional: offline mode without AI

#### 2.2 Wikilink Suggestions
- [ ] Scan existing vault for note titles and tags
- [ ] Build index of linkable content
- [ ] LLM prompt for contextual link suggestions
- [ ] Insert `[[wikilinks]]` into output

#### 2.3 Enhanced Output
- [ ] Tag extraction and suggestion
- [ ] Improved Markdown formatting
- [ ] Handle different notebook types

### Phase 3: Vault Integration

**Goal:** Seamless Obsidian workflow

#### 3.1 Daily Notes Integration
- [ ] Parse daily note path pattern (`Daily/YYYY/MM-Mon/YYYY-MM-DD.md`)
- [ ] Append notebook content to existing daily notes
- [ ] Create daily notes if they don't exist
- [ ] Configurable insertion point (top/bottom/section)

#### 3.2 Advanced Features
- [ ] Incremental sync (track processed notebooks)
- [ ] Duplicate detection
- [ ] Notebook organization by date/topic
- [ ] Export format preferences (Text vs HTML vs PDF)

---

## Project Structure

```
kobo-notebooks-markdown/
├── pyproject.toml
├── README.md
├── LICENSE
├── PLAN.md                     # This file
├── Kobo Sage to Obsidian Research.md  # Original research
│
├── src/
│   └── kobo_md/
│       ├── __init__.py
│       ├── __main__.py         # Entry point
│       ├── cli.py              # Typer CLI commands
│       │
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── cookies.py      # Browser cookie extraction
│       │   └── session.py      # Kobo session management
│       │
│       ├── kobo/
│       │   ├── __init__.py
│       │   ├── client.py       # Kobo web API client
│       │   ├── models.py       # Notebook data models
│       │   └── parser.py       # Response parsing
│       │
│       ├── processor/
│       │   ├── __init__.py
│       │   ├── cleaner.py      # Text cleanup
│       │   └── llm.py          # LLM integration
│       │
│       ├── obsidian/
│       │   ├── __init__.py
│       │   ├── vault.py        # Vault operations
│       │   ├── linker.py       # Wikilink suggestions
│       │   └── daily.py        # Daily notes integration
│       │
│       └── config/
│           ├── __init__.py
│           └── settings.py     # Pydantic settings
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth/
│   ├── test_kobo/
│   └── test_obsidian/
│
└── docs/
    └── setup.md
```

---

## CLI Commands

```bash
# Authentication
kobo-md auth login              # Extract cookies from browser
kobo-md auth status             # Check authentication status
kobo-md auth clear              # Clear stored credentials

# Notebook Operations
kobo-md list                    # List available notebooks
kobo-md fetch [NOTEBOOK_ID]     # Fetch specific notebook
kobo-md fetch --all             # Fetch all notebooks
kobo-md sync                    # Sync new/updated notebooks

# Configuration
kobo-md config show             # Show current configuration
kobo-md config set KEY VALUE    # Update configuration
kobo-md config init             # Interactive setup

# Processing
kobo-md process FILE            # Process downloaded notebook
kobo-md process --ai            # Process with AI enhancement
```

---

## Configuration

```toml
# ~/.config/kobo-md/config.toml

[auth]
browser = "firefox"  # or "chrome", "chromium", "edge"
profile = "default"  # browser profile name

[kobo]
region = "us"  # kobo.com region
export_format = "text"  # "text", "html", "pdf"

[output]
vault_path = "~/Documents/Vault"
output_dir = "kobo"  # relative to vault
daily_notes_pattern = "Daily/{year}/{month:02d}-{month_name}/{date}.md"

[ai]
enabled = true
provider = "anthropic"  # or "openai"
model = "claude-sonnet-4-20250514"
cleanup = true
suggest_links = true

[ai.anthropic]
api_key_env = "ANTHROPIC_API_KEY"  # environment variable name

[processing]
skip_existing = true
```

---

## Dependencies

```toml
[project]
dependencies = [
    "typer[all]>=0.9.0",      # CLI framework
    "httpx>=0.27.0",          # HTTP client
    "pydantic>=2.0",          # Settings/models
    "browser-cookie3>=0.19",  # Cookie extraction
    "rich>=13.0",             # Pretty CLI output
    "python-dateutil>=2.8",   # Date parsing
    "toml>=0.10",             # Config files
]

[project.optional-dependencies]
ai = [
    "anthropic>=0.40.0",      # Claude API
    "openai>=1.0",            # OpenAI API (optional)
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.6",
    "mypy>=1.0",
]
```

---

## Research Items

### Kobo Web Portal Investigation

**Questions to answer:**
1. What API endpoints does the notebook portal use?
2. How are notebooks exported? (direct download vs async job)
3. What authentication headers/cookies are required?
4. Rate limiting and session expiry behavior?

**Investigation approach:**
- Browser DevTools network inspection
- Document API endpoints and request/response formats
- Test cookie-based authentication

### Cookie Extraction

**Libraries to evaluate:**
- `browser-cookie3` - Cross-platform cookie extraction
- `pycookiecheat` - Chrome-specific, simpler
- Manual SQLite reading for edge cases

**Security considerations:**
- Store credentials securely (keyring or encrypted file)
- Handle session refresh gracefully
- Don't log sensitive tokens

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Can authenticate using browser cookies
- [ ] Can list notebooks from Kobo portal
- [ ] Can download notebook as text
- [ ] Saves clean Markdown to configured directory
- [ ] Basic CLI works end-to-end

### Phase 2 Complete When:
- [ ] LLM cleans up notebook text
- [ ] Wikilinks suggested based on vault content
- [ ] Output integrates well with Obsidian

### Phase 3 Complete When:
- [ ] Notebooks append to daily notes
- [ ] Incremental sync avoids duplicates
- [ ] Fully automated workflow possible

---

## Open Questions

1. **Kobo API Stability**: Is the web portal API stable enough to rely on, or could it change without notice?

2. **Export Format**: Should we prioritize Text (cleanest) or HTML (preserves some formatting)?

3. **Vault Scanning**: How large is the vault? Should we optimize link suggestions for large vaults?

4. **Offline Mode**: Should Phase 1 work completely offline (no AI), with AI as an optional enhancement?

5. **Multi-notebook handling**: Should notebooks export to separate files or be merged by date?

---

## Next Steps

1. **Initialize Python project** with basic structure
2. **Research Kobo web portal** API using browser DevTools
3. **Implement cookie extraction** with `browser-cookie3`
4. **Build minimal fetch** to prove authentication works
5. **Iterate** based on what we learn about the API

---

*Plan created: 2026-01-02*
