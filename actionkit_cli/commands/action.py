"""Action commands."""

import json

import click

from actionkit_cli.output import print_json, print_list_response

ACTION_COLUMNS = ["id", "user", "page", "source", "status", "created_at"]


@click.group()
def action():
    """Manage ActionKit actions."""
    pass


@action.command("list")
@click.option("--limit", "-l", default=20, help="Number of results (max 100).")
@click.option("--offset", "-o", default=0, help="Result offset for pagination.")
@click.option("--order-by", default="-created_at", help="Field to sort by.")
@click.option("--page", "page_id", type=int, help="Filter by page ID.")
@click.option("--user", "user_id", type=int, help="Filter by user ID.")
@click.pass_obj
def list_actions(client, limit, offset, order_by, page_id, user_id):
    """List actions."""
    filters = {}
    if page_id:
        filters["page"] = page_id
    if user_id:
        filters["user"] = user_id

    data = client.list(
        "action", limit=limit, offset=offset, order_by=order_by, **filters
    )
    print_list_response(data, ACTION_COLUMNS, title="Actions")


@action.command("get")
@click.argument("action_id", type=int)
@click.pass_obj
def get_action(client, action_id):
    """Get a single action by ID."""
    data = client.detail("action", action_id)
    print_json(data)


@action.command("create")
@click.option("--page", "page_name", required=True, help="Page short name.")
@click.option("--email", required=True, help="User email address.")
@click.option("--first-name", help="User first name.")
@click.option("--last-name", help="User last name.")
@click.option("--source", help="Action source.")
@click.option(
    "--field", "-f", multiple=True, help="Custom field as key=value (repeatable)."
)
@click.pass_obj
def create_action(client, page_name, email, first_name, last_name, source, field):
    """Create an action (process a user through a page)."""
    data = {"page": page_name, "email": email}
    if first_name:
        data["first_name"] = first_name
    if last_name:
        data["last_name"] = last_name
    if source:
        data["source"] = source

    for f in field:
        key, _, value = f.partition("=")
        if not key or not _:
            raise click.BadParameter(f"Invalid field format: {f!r}. Use key=value.")
        data[key] = value

    result = client.post("action", data)
    click.echo("Action created.")
    print_json(result)
