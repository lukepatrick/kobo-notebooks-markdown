"""Command-line interface for kobo-md."""

from typing import Annotated

import typer
from rich.console import Console

from kobo_md import __version__

app = typer.Typer(
    name="kobo-md",
    help="Read Kobo Notebooks and Parse to Markdown.",
    no_args_is_help=True,
)

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


@app.command()
def sync(
    output_dir: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output directory for markdown files."),
    ] = None,
) -> None:
    """Sync annotations from Kobo cloud to local markdown files."""
    _ = output_dir  # Placeholder for future implementation
    console.print("[yellow]sync command not yet implemented[/yellow]")


@app.command()
def list_books() -> None:
    """List all books with annotations in your Kobo library."""
    console.print("[yellow]list-books command not yet implemented[/yellow]")


@app.command()
def export(
    book_id: Annotated[
        str | None,
        typer.Argument(help="Book ID to export (use list-books to find IDs)."),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path."),
    ] = None,
) -> None:
    """Export annotations for a specific book to markdown."""
    _ = book_id, output  # Placeholder for future implementation
    console.print("[yellow]export command not yet implemented[/yellow]")


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option("--show", "-s", help="Show current configuration."),
    ] = False,
    init: Annotated[
        bool,
        typer.Option("--init", "-i", help="Initialize configuration file."),
    ] = False,
) -> None:
    """Manage kobo-md configuration."""
    if show:
        console.print("[yellow]config --show not yet implemented[/yellow]")
    elif init:
        console.print("[yellow]config --init not yet implemented[/yellow]")
    else:
        console.print("Use --show to display config or --init to create one.")


if __name__ == "__main__":
    app()
