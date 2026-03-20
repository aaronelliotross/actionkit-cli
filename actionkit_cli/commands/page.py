"""Page commands."""

import click

from actionkit_cli.output import print_json, print_list_response

PAGE_COLUMNS = ["id", "type", "name", "title", "status", "created_at"]


@click.group()
def page():
    """Manage ActionKit pages."""
    pass


@page.command("list")
@click.option("--limit", "-l", default=20, help="Number of results (max 100).")
@click.option("--offset", "-o", default=0, help="Result offset for pagination.")
@click.option("--order-by", default="-created_at", help="Field to sort by.")
@click.option(
    "--type", "page_type", help="Filter by page type (e.g. petition, donation, signup)."
)
@click.option("--status", help="Filter by status (e.g. active, inactive).")
@click.option("--name-contains", help="Filter by name (case-insensitive contains).")
@click.pass_obj
def list_pages(client, limit, offset, order_by, page_type, status, name_contains):
    """List pages."""
    filters = {}
    if page_type:
        filters["type"] = page_type
    if status:
        filters["status"] = status
    if name_contains:
        filters["name__icontains"] = name_contains

    data = client.list("page", limit=limit, offset=offset, order_by=order_by, **filters)
    print_list_response(data, PAGE_COLUMNS, title="Pages")


@page.command("get")
@click.argument("page_id", type=int)
@click.pass_obj
def get_page(client, page_id):
    """Get a single page by ID."""
    data = client.detail("page", page_id)
    print_json(data)
