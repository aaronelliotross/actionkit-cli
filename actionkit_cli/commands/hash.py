"""Hash a value using the ActionKit secret key."""

import base64
import hashlib
import os

import click


@click.command()
@click.argument("value")
def hash(value):
    """Append an ActionKit-style short hash suffix to VALUE."""
    secret = os.getenv("ACTIONKIT_SECRET_KEY")
    if not secret:
        raise click.ClickException("ACTIONKIT_SECRET_KEY is not set")

    sha = hashlib.sha256(f"{secret}.{value}".encode("ascii"))
    urlsafe_hash = base64.urlsafe_b64encode(sha.digest()).decode("ascii")
    click.echo(f"{value}.{urlsafe_hash[:6]}")
