"""Command-line interface for kobo-md."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kobo_md import __version__
from kobo_md.auth import CookieError, extract_cookies, load_cookies, save_cookies
from kobo_md.config import get_settings
from kobo_md.kobo import KoboClient, KoboClientError, Notebook
from kobo_md.obsidian import write_notebook

app = typer.Typer(
    name="kobo-md",
    help="Export Kobo Notebooks to Obsidian-compatible Markdown.",
    no_args_is_help=True,
)

auth_app = typer.Typer(help="Authentication commands.")
app.add_typer(auth_app, name="auth")

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"kobo-md version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Kobo Notebook to Markdown converter."""
    pass


@auth_app.command("login")
def auth_login(
    browser: Annotated[
        str,
        typer.Option("--browser", "-b", help="Browser to extract cookies from."),
    ] = "firefox",
) -> None:
    """Extract and save authentication cookies from browser.

    You must be logged in to kobo.com in your browser before running this command.
    """
    settings = get_settings()

    console.print(f"[blue]Extracting cookies from {browser}...[/blue]")

    try:
        cookies = extract_cookies(browser=browser)
        save_cookies(cookies, settings.cookies_path)
        console.print("[green]Cookies saved successfully![/green]")
        console.print(f"Saved to: {settings.cookies_path}")
    except CookieError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@auth_app.command("status")
def auth_status() -> None:
    """Check authentication status."""
    settings = get_settings()

    cookies = load_cookies(settings.cookies_path)
    if cookies is None:
        console.print("[yellow]Not authenticated.[/yellow]")
        console.print("Run 'kobo-md auth login' to authenticate.")
        raise typer.Exit(1)

    console.print("[green]Authentication cookies found.[/green]")

    # Try to validate by listing notebooks
    console.print("[blue]Validating session...[/blue]")
    try:
        with KoboClient(cookies, region=settings.kobo_region) as client:
            notebooks = client.list_notebooks()
            console.print(f"[green]Session valid! Found {len(notebooks)} notebooks.[/green]")
    except KoboClientError as e:
        console.print(f"[red]Session invalid:[/red] {e}")
        console.print("Run 'kobo-md auth login' to refresh cookies.")
        raise typer.Exit(1) from e


@auth_app.command("clear")
def auth_clear() -> None:
    """Clear saved authentication cookies."""
    settings = get_settings()

    if settings.cookies_path.exists():
        settings.cookies_path.unlink()
        console.print("[green]Cookies cleared.[/green]")
    else:
        console.print("[yellow]No cookies to clear.[/yellow]")


@app.command("list")
def list_notebooks() -> None:
    """List all notebooks in your Kobo library."""
    settings = get_settings()

    cookies = load_cookies(settings.cookies_path)
    if cookies is None:
        console.print("[red]Not authenticated.[/red] Run 'kobo-md auth login' first.")
        raise typer.Exit(1)

    try:
        with KoboClient(cookies, region=settings.kobo_region) as client:
            notebooks = client.list_notebooks()

            if not notebooks:
                console.print("[yellow]No notebooks found.[/yellow]")
                return

            table = Table(title="Kobo Notebooks")
            table.add_column("ID", style="dim")
            table.add_column("Title")
            table.add_column("Preview", justify="center")

            for nb in notebooks:
                preview = "[green]Yes[/green]" if nb.can_be_previewed else "[red]No[/red]"
                # Truncate ID for display
                short_id = nb.id[:8] + "..."
                table.add_row(short_id, nb.title, preview)

            console.print(table)
            console.print(f"\nTotal: {len(notebooks)} notebooks")

    except KoboClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("fetch")
def fetch_notebook(
    notebook_id: Annotated[
        str | None,
        typer.Argument(help="Notebook ID to fetch (use 'list' to see IDs). Prefix match supported."),
    ] = None,
    all_notebooks: Annotated[
        bool,
        typer.Option("--all", "-a", help="Fetch all notebooks."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory (overrides config)."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", "-f", help="Overwrite existing files."),
    ] = False,
    ai: Annotated[
        bool | None,
        typer.Option("--ai/--no-ai", help="Enable/disable AI processing (overrides config)."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", "-p", help="AI provider: 'anthropic', 'openai', or 'claude-code'."),
    ] = None,
) -> None:
    """Fetch and export notebooks to markdown.

    You can specify a notebook ID (prefix match supported) or use --all.

    Use --ai to enable AI-powered text cleanup and wikilink suggestions.
    Requires ANTHROPIC_API_KEY, OPENAI_API_KEY, or Claude Code CLI installed.
    """
    if not notebook_id and not all_notebooks:
        console.print("[red]Error:[/red] Specify a notebook ID or use --all")
        raise typer.Exit(1)

    settings = get_settings()
    output_dir = output or settings.output_path

    # Determine AI settings
    use_ai = ai if ai is not None else settings.ai_enabled
    ai_provider = provider or settings.ai_provider

    cookies = load_cookies(settings.cookies_path)
    if cookies is None:
        console.print("[red]Not authenticated.[/red] Run 'kobo-md auth login' first.")
        raise typer.Exit(1)

    # Initialize processor if AI is enabled
    processor = None
    if use_ai:
        try:
            from kobo_md.processor import NotebookProcessor

            console.print(f"[blue]AI processing enabled ({ai_provider})[/blue]")
            console.print("[blue]Scanning vault for existing notes...[/blue]")

            processor = NotebookProcessor(
                vault_path=settings.vault_path,
                ai_enabled=True,
                ai_provider=ai_provider,
                ai_model=settings.ai_model,
            )

            if processor.vault_index:
                console.print(
                    f"[dim]Found {len(processor.vault_index.note_titles)} notes, "
                    f"{len(processor.vault_index.tags)} tags[/dim]"
                )
        except ImportError as e:
            console.print(f"[red]AI processing unavailable:[/red] {e}")
            console.print("[yellow]Install AI dependencies: pip install 'kobo-md[ai]'[/yellow]")
            use_ai = False
        except ValueError as e:
            console.print(f"[red]AI configuration error:[/red] {e}")
            use_ai = False

    try:
        with KoboClient(cookies, region=settings.kobo_region) as client:
            notebooks = client.list_notebooks()

            if not notebooks:
                console.print("[yellow]No notebooks found.[/yellow]")
                return

            # Filter notebooks
            to_fetch = []
            if all_notebooks:
                to_fetch = [nb for nb in notebooks if nb.can_be_previewed]
            elif notebook_id:
                # Support prefix matching
                for nb in notebooks:
                    if nb.id.startswith(notebook_id):
                        to_fetch.append(nb)
                        break
                if not to_fetch:
                    console.print(f"[red]No notebook found with ID starting with '{notebook_id}'[/red]")
                    raise typer.Exit(1)

            console.print(f"[blue]Fetching {len(to_fetch)} notebook(s)...[/blue]")

            for nb_info in to_fetch:
                console.print(f"  Fetching: {nb_info.title}")

                try:
                    # Get full metadata
                    metadata = client.get_notebook_metadata(nb_info.id)

                    if not metadata.is_advanced:
                        console.print("    [yellow]Skipping (not an Advanced notebook)[/yellow]")
                        continue

                    # Get all pages
                    pages = client.get_all_notebook_pages(nb_info.id, metadata)

                    # Create notebook object
                    notebook = Notebook(metadata=metadata, pages=pages)

                    # Process with AI if enabled
                    if use_ai and processor:
                        console.print("    [blue]Processing with AI...[/blue]")
                        try:
                            notebook = processor.process_notebook(notebook)
                            console.print("    [green]AI processing complete[/green]")
                        except Exception as e:
                            console.print(f"    [yellow]AI processing failed: {e}[/yellow]")
                            console.print("    [yellow]Saving without AI processing[/yellow]")

                    # Write to file
                    try:
                        filepath = write_notebook(notebook, output_dir, overwrite=overwrite)
                        console.print(f"    [green]Saved:[/green] {filepath}")
                    except FileExistsError:
                        console.print("    [yellow]Skipped (already exists, use -f to overwrite)[/yellow]")

                except KoboClientError as e:
                    console.print(f"    [red]Error:[/red] {e}")

            console.print("[green]Done![/green]")

    except KoboClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("process")
def process_file(
    file_path: Annotated[
        Path,
        typer.Argument(help="Markdown file to process."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file (default: overwrite input)."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", "-p", help="AI provider: 'anthropic', 'openai', or 'claude-code'."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show changes without writing."),
    ] = False,
) -> None:
    """Process an existing markdown file with AI.

    Adds wikilinks, cleans up text, and suggests tags.
    Requires ANTHROPIC_API_KEY, OPENAI_API_KEY, or Claude Code CLI installed.
    """
    if not file_path.exists():
        console.print(f"[red]File not found:[/red] {file_path}")
        raise typer.Exit(1)

    settings = get_settings()
    ai_provider = provider or settings.ai_provider

    try:
        from kobo_md.processor import NotebookProcessor

        console.print(f"[blue]Processing with {ai_provider}...[/blue]")
        console.print("[blue]Scanning vault for existing notes...[/blue]")

        processor = NotebookProcessor(
            vault_path=settings.vault_path,
            ai_enabled=True,
            ai_provider=ai_provider,
            ai_model=settings.ai_model,
        )

        if processor.vault_index:
            console.print(
                f"[dim]Found {len(processor.vault_index.note_titles)} notes, "
                f"{len(processor.vault_index.tags)} tags[/dim]"
            )

    except ImportError as e:
        console.print(f"[red]AI processing unavailable:[/red] {e}")
        console.print("[yellow]Install AI dependencies: pip install 'kobo-md[ai]'[/yellow]")
        raise typer.Exit(1) from e
    except ValueError as e:
        console.print(f"[red]AI configuration error:[/red] {e}")
        raise typer.Exit(1) from e

    # Read the file
    original_text = file_path.read_text(encoding="utf-8")

    console.print("[blue]Sending to AI for processing...[/blue]")

    try:
        result = processor.process_text(original_text)
    except Exception as e:
        console.print(f"[red]AI processing failed:[/red] {e}")
        raise typer.Exit(1) from e

    # Show results
    console.print()
    console.print(Panel(
        f"[green]Wikilinks added:[/green] {len(result.wikilinks)}\n"
        f"  Existing notes: {len(result.existing_wikilinks)}\n"
        f"  New links: {len(result.new_wikilinks)}\n"
        f"[green]Tags suggested:[/green] {len(result.tags)}",
        title="Processing Results",
    ))

    if result.wikilinks:
        console.print("\n[cyan]Wikilinks:[/cyan]")
        for link in result.wikilinks:
            status = "[green](exists)[/green]" if link in result.existing_wikilinks else "[yellow](new)[/yellow]"
            console.print(f"  [[{link}]] {status}")

    if result.tags:
        console.print("\n[cyan]Suggested tags:[/cyan]")
        console.print(f"  {', '.join('#' + t for t in result.tags)}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes written[/yellow]")
        console.print("\n[dim]Processed text preview:[/dim]")
        console.print(Panel(result.processed_text[:1000] + "..." if len(result.processed_text) > 1000 else result.processed_text))
    else:
        output_path = output or file_path
        output_path.write_text(result.processed_text, encoding="utf-8")
        console.print(f"\n[green]Saved:[/green] {output_path}")


@app.command("scan-vault")
def scan_vault_cmd(
    vault_path: Annotated[
        Path | None,
        typer.Option("--vault", "-v", help="Vault path (uses config default if not specified)."),
    ] = None,
) -> None:
    """Scan Obsidian vault and show statistics."""
    settings = get_settings()
    path = vault_path or settings.vault_path

    if not path.exists():
        console.print(f"[red]Vault not found:[/red] {path}")
        raise typer.Exit(1)

    console.print(f"[blue]Scanning vault:[/blue] {path}")

    from kobo_md.obsidian import scan_vault

    index = scan_vault(path)

    table = Table(title="Vault Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Notes", str(len(index.note_titles)))
    table.add_row("Tags", str(len(index.tags)))
    table.add_row("Notes with aliases", str(len(index.aliases)))

    console.print(table)

    if index.tags:
        console.print("\n[cyan]Top tags:[/cyan]")
        for tag in sorted(index.tags)[:20]:
            console.print(f"  #{tag}")
        if len(index.tags) > 20:
            console.print(f"  [dim]... and {len(index.tags) - 20} more[/dim]")


@app.command("config")
def show_config(
    show: Annotated[
        bool,
        typer.Option("--show", "-s", help="Show current configuration."),
    ] = False,
) -> None:
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Browser", settings.browser)
    table.add_row("Kobo Region", settings.kobo_region)
    table.add_row("Vault Path", str(settings.vault_path))
    table.add_row("Output Dir", settings.output_dir)
    table.add_row("Output Path", str(settings.output_path))
    table.add_row("Daily Notes Pattern", settings.daily_notes_pattern)
    table.add_row("AI Enabled", str(settings.ai_enabled))
    table.add_row("AI Provider", settings.ai_provider)
    table.add_row("AI Model", settings.ai_model)
    table.add_row("Suggest Wikilinks", str(settings.suggest_wikilinks))
    table.add_row("Cleanup Text", str(settings.cleanup_text))
    table.add_row("Skip Existing", str(settings.skip_existing))
    table.add_row("Config Dir", str(settings.config_dir))
    table.add_row("Cookies Path", str(settings.cookies_path))

    console.print(table)

    console.print("\n[dim]Configure via environment variables (KOBO_MD_* prefix) or .env file[/dim]")
    console.print("[dim]Example: export KOBO_MD_AI_ENABLED=true[/dim]")
    console.print("[dim]         export ANTHROPIC_API_KEY=sk-ant-...[/dim]")


if __name__ == "__main__":
    app()
