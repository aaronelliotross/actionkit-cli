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


@page.command("update")
@click.argument("page_id", type=int)
@click.option(
    "--field", "-f", multiple=True, help="Custom field as key=value (repeatable)."
)
@click.pass_obj
def update_page(client, page_id, field):
    """Update a page's custom fields."""
    fields = {}
    for f in field:
        key, _, value = f.partition("=")
        if not key or not _:
            raise click.BadParameter(f"Invalid field format: {f!r}. Use key=value.")
        fields[key] = value

    if not fields:
        click.echo("No fields to update. Use --help to see options.")
        return

    # The generic /page/ endpoint is read-only (405 on PATCH); custom fields must
    # be written via the type-specific resource (e.g. /signuppage/). Fetch the
    # page to discover its resource_uri, then merge into its existing fields so
    # we never clobber other custom fields.
    current = client.detail("page", page_id)
    resource_path = current.get("resource_uri", "").replace("/rest/v1/", "").strip("/")
    if not resource_path:
        raise click.ClickException(
            f"Could not resolve resource_uri for page {page_id}."
        )

    merged = {**(current.get("fields") or {}), **fields}
    data = client.patch(resource_path, {"fields": merged})
    click.echo(f"Page {page_id} updated.")
    print_json(data)
