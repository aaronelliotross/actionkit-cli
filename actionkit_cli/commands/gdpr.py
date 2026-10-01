"""GDPR commands."""

import json
import os
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit

import click
import httpx

from actionkit_cli.commands.generic import api_errors
from actionkit_cli.gdpr_html import ref_key, render_html

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


def fetch_ref(client, uri: str) -> dict | None:
    """Fetch the object a URI points at, or None if it has been deleted."""
    try:
        return client.get(uri.removeprefix(API_PREFIX))
    except httpx.HTTPStatusError as exc:
        # Deleted pages still appear on old actions, and some user links
        # point at records that were never created.
        if exc.response.status_code != 404:
            with api_errors(uri):
                raise
        return None


def is_letter(action: dict) -> bool:
    return (action.get("resource_uri") or "").startswith(API_PREFIX + "letteraction/")


def resolve_references(client, export: dict) -> tuple[dict, dict]:
    """Look up what the readable export needs beyond the raw data.

    Returns `labels`, mapping `ref_key()`s of pages, lists and letter
    recipients to display names, and `letters`, mapping letter pages to
    their letter template. Each distinct object is fetched once. Actions
    get their page's title too, so orders and transactions show the
    campaign.
    """
    actions = export.get("actions", [])
    uris = {a.get("page") for a in actions}
    uris |= {t for a in actions for t in a.get("targeted", [])}
    for key in ("subscriptions", "subscriptionhistory"):
        uris |= {r.get("list") for r in export.get(key, [])}
    labels, letters = {}, {}
    for uri in sorted(u for u in uris if ref_key(u)):
        key = ref_key(uri)
        obj = fetch_ref(client, uri)
        if obj is None:
            labels[key] = f"{key[0].capitalize()} no longer available"
            continue
        labels[key] = (
            obj.get("title")
            or obj.get("title_full")
            or obj.get("full_name")
            or obj.get("name")
        )
        form_uri = obj.get("cms_form") or ""
        if form_uri.startswith(API_PREFIX + "letterform/"):
            form = fetch_ref(client, form_uri) or {}
            text = [form.get(k) for k in ("statement_leadin", "letter_text")]
            letters[key] = "\n\n".join(t for t in text if t)
    # Orders point at an action and transactions at an order, so chain the
    # campaign title along.
    for key, via in (("actions", "page"), ("orders", "action")):
        for obj in export.get(key, []):
            title = labels.get(ref_key(obj.get(via)))
            if title and ref_key(obj.get("resource_uri")):
                labels[ref_key(obj["resource_uri"])] = title
    return labels, letters


@gdpr.command("export")
@click.argument("email")
@click.option(
    "--output", "-o", type=click.Path(dir_okay=False), help="Write to this file."
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "html"]),
    default="json",
    show_default=True,
    help="json is the complete record; html is a readable document to send.",
)
@click.pass_obj
def export(client, email, output, fmt):
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
            # Not every user has e.g. a useroriginal record; the link is
            # present regardless.
            result[key] = fetch_ref(client, user[key]) or {}
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

    # The generic action listing leaves out who a letter was sent to.
    if any(is_letter(a) for a in result.get("actions", [])):
        click.echo("Fetching letter recipients...", err=True)
        with api_errors("letteraction"):
            letters = fetch_all(client, "letteraction", user=user["id"])
        targeted = {la["id"]: la.get("targeted", []) for la in letters}
        for action in result["actions"]:
            if is_letter(action) and action.get("id") in targeted:
                action["targeted"] = targeted[action["id"]]

    if fmt == "html":
        click.echo("Looking up campaign, list and recipient names...", err=True)
        labels, letters = resolve_references(client, result)
        text = render_html(result, labels, letters).rstrip("\n")
    else:
        text = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(text + "\n")
        click.echo(f"Wrote export for user {user['id']} to {output}", err=True)
    else:
        click.echo(text)
