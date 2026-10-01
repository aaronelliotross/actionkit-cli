"""GDPR commands."""

import json
import os
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit

import click

from actionkit_cli.commands.generic import api_errors

PAGE_SIZE = 100
API_PREFIX = "/rest/v1/"

# List links on the user record that are left out of the export.
SKIP_LINKS = {"usermailings"}

# Single-object links on the user record that hold personal data.
DETAIL_LINKS = ["location", "useroriginal"]


@click.group()
def gdpr():
    """GDPR data subject requests."""
    pass


def fetch_all(client, resource: str, **filters) -> list[dict]:
    """Fetch every page of a filtered list."""
    objects = []
    offset = 0
    while True:
        data = client.list(resource, limit=PAGE_SIZE, offset=offset, **filters)
        objects.extend(data.get("objects", []))
        if not data.get("meta", {}).get("next"):
            return objects
        offset += PAGE_SIZE


def list_links(user: dict) -> dict[str, tuple[str, dict]]:
    """Map each list link on a user record, e.g. `/rest/v1/order/?user=27`,
    to its resource name and filters."""
    links = {}
    for key, value in user.items():
        if key in SKIP_LINKS or not isinstance(value, str):
            continue
        parts = urlsplit(value)
        if parts.path.startswith(API_PREFIX) and parts.query:
            resource = parts.path.removeprefix(API_PREFIX).strip("/")
            links[key] = (resource, dict(parse_qsl(parts.query)))
    return links


@gdpr.command("export")
@click.argument("email")
@click.option(
    "--output", "-o", type=click.Path(dir_okay=False), help="Write JSON to this file."
)
@click.pass_obj
def export(client, email, output):
    """Export all personal data held for EMAIL (GDPR article 15)."""
    if output:
        directory = os.path.dirname(os.path.abspath(output))
        if not os.access(directory, os.W_OK):
            raise click.ClickException(f"Cannot write to directory: {directory}")
    with api_errors("user"):
        users = client.list("user", email=email).get("objects", [])
    if not users:
        raise click.ClickException(f"No user found with email: {email}")
    user = users[0]

    result = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "email": email,
        "user": user,
    }
    for key in DETAIL_LINKS:
        if user.get(key):
            with api_errors(key):
                result[key] = client.get(user[key].removeprefix(API_PREFIX))
    for key, (resource, filters) in list_links(user).items():
        click.echo(f"Fetching {key}...", err=True)
        with api_errors(resource):
            result[key] = fetch_all(client, resource, **filters)
    # Transactions are not linked from the user record, only from each order.
    click.echo("Fetching transactions...", err=True)
    with api_errors("transaction"):
        result["transactions"] = fetch_all(
            client, "transaction", order__user=user["id"]
        )

    text = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(text + "\n")
        click.echo(f"Wrote export for user {user['id']} to {output}", err=True)
    else:
        click.echo(text)
