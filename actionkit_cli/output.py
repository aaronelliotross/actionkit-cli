"""Output formatting utilities."""

import json

import click
from rich.console import Console
from rich.table import Table

console = Console()


def print_json(data):
    """Print data as formatted JSON."""
    console.print_json(json.dumps(data, default=str))


def print_table(objects: list[dict], columns: list[str], title: str | None = None):
    """Print a list of dicts as a rich table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)

    for obj in objects:
        row = [str(obj.get(col, "")) for col in columns]
        table.add_row(*row)

    console.print(table)


def print_list_response(data: dict, columns: list[str], title: str | None = None):
    """Print a paginated list API response as a table with metadata."""
    meta = data.get("meta", {})
    objects = data.get("objects", [])

    if objects:
        print_table(objects, columns, title=title)
    else:
        click.echo("No results found.")

    total = meta.get("total_count", "?")
    offset = meta.get("offset", 0)
    limit = meta.get("limit", 20)
    click.echo(f"\nShowing {offset + 1}–{offset + len(objects)} of {total}")
