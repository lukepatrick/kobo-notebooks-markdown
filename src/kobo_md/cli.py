"""Command-line interface for kobo-md."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
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
) -> None:
    """Fetch and export notebooks to markdown.

    You can specify a notebook ID (prefix match supported) or use --all.
    """
    if not notebook_id and not all_notebooks:
        console.print("[red]Error:[/red] Specify a notebook ID or use --all")
        raise typer.Exit(1)

    settings = get_settings()
    output_dir = output or settings.output_path

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
                        console.print(f"    [yellow]Skipping (not an Advanced notebook)[/yellow]")
                        continue

                    # Get all pages
                    pages = client.get_all_notebook_pages(nb_info.id, metadata)

                    # Create notebook object
                    notebook = Notebook(metadata=metadata, pages=pages)

                    # Write to file
                    try:
                        filepath = write_notebook(notebook, output_dir, overwrite=overwrite)
                        console.print(f"    [green]Saved:[/green] {filepath}")
                    except FileExistsError:
                        console.print(f"    [yellow]Skipped (already exists, use -f to overwrite)[/yellow]")

                except KoboClientError as e:
                    console.print(f"    [red]Error:[/red] {e}")

            console.print("[green]Done![/green]")

    except KoboClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


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


if __name__ == "__main__":
    app()
