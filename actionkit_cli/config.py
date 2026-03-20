"""Configuration loading from environment variables."""

import os
import sys

import click
from dotenv import load_dotenv


def load_config() -> dict:
    """Load ActionKit configuration from environment."""
    load_dotenv()

    base_url = os.environ.get("ACTIONKIT_BASE_URL")
    username = os.environ.get("ACTIONKIT_USERNAME")
    password = os.environ.get("ACTIONKIT_PASSWORD")

    missing = []
    if not base_url:
        missing.append("ACTIONKIT_BASE_URL")
    if not username:
        missing.append("ACTIONKIT_USERNAME")
    if not password:
        missing.append("ACTIONKIT_PASSWORD")

    if missing:
        click.echo(
            f"Error: Missing required environment variables: {', '.join(missing)}",
            err=True,
        )
        click.echo(
            "Set them in a .env file or export them in your shell.",
            err=True,
        )
        sys.exit(1)

    return {"base_url": base_url, "username": username, "password": password}
