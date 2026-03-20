"""Translation commands."""

import json

import click

from actionkit_cli.output import print_json


@click.group()
def translation():
    """Manage ActionKit translation strings."""
    pass


def _find_language(client, iso_code):
    """Find a language resource by ISO code."""
    data = client.list("language", iso_code=iso_code, _limit=1)
    objects = data.get("objects", [])
    if not objects:
        click.echo(f"Language '{iso_code}' not found.", err=True)
        raise SystemExit(1)
    return objects[0]


def _parse_translations(language):
    """Parse the translations JSON string from a language resource."""
    raw = language.get("translations", "{}")
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


@translation.command("set")
@click.argument("iso_code")
@click.argument("key")
@click.argument("value", required=False)
@click.pass_obj
def set_translation(client, iso_code, key, value):
    """Add or update translation strings.

    Set a single key:

        actionkit translation set nl donate_button "Doneer nu"

    Set multiple keys from a JSON file (prefix path with @):

        actionkit translation set nl @translations.json
    """
    if key.startswith("@"):
        if value:
            raise click.UsageError("VALUE is not allowed when using @file input.")
        file_path = key[1:]
        try:
            with open(file_path) as f:
                updates = json.load(f)
        except FileNotFoundError:
            raise click.UsageError(f"File not found: {file_path}")
        if not isinstance(updates, dict):
            raise click.UsageError("JSON file must contain an object of key-value pairs.")
    else:
        if not value:
            raise click.UsageError("VALUE is required when setting a single key.")
        updates = {key: value}

    language = _find_language(client, iso_code)
    translations = _parse_translations(language)

    added = 0
    updated = 0
    for k, v in updates.items():
        if k in translations:
            updated += 1
        else:
            added += 1
        translations[k] = v

    client.patch(
        f"language/{language['id']}",
        {"translations": json.dumps(translations, ensure_ascii=False)},
    )

    parts = []
    if added:
        parts.append(f"{added} added")
    if updated:
        parts.append(f"{updated} updated")
    click.echo(f"Language {iso_code}: {', '.join(parts)}.")


@translation.command("get")
@click.argument("iso_code")
@click.argument("key", required=False)
@click.pass_obj
def get_translation(client, iso_code, key):
    """Get translation strings for a language.

    If KEY is provided, prints only that value.
    Otherwise prints all translation strings.
    """
    language = _find_language(client, iso_code)
    translations = _parse_translations(language)

    if key:
        if key in translations:
            click.echo(translations[key])
        else:
            click.echo(f"Key '{key}' not found in {iso_code}.", err=True)
            raise SystemExit(1)
    else:
        print_json(translations)


@translation.command("list")
@click.pass_obj
def list_languages(client):
    """List available languages."""
    data = client.list("language", _limit=100, order_by="name")
    objects = data.get("objects", [])

    if not objects:
        click.echo("No languages found.")
        return

    for lang in objects:
        translations = _parse_translations(lang)
        count = len(translations)
        click.echo(f"  {lang['iso_code']:5s}  {lang['name']:<20s}  ({count} keys)")


@translation.command("delete")
@click.argument("iso_code")
@click.argument("key")
@click.confirmation_option(prompt="Are you sure you want to delete this translation key?")
@click.pass_obj
def delete_translation(client, iso_code, key):
    """Delete a translation key from a language."""
    language = _find_language(client, iso_code)
    translations = _parse_translations(language)

    if key not in translations:
        click.echo(f"Key '{key}' not found in {iso_code}.", err=True)
        raise SystemExit(1)

    del translations[key]
    client.patch(
        f"language/{language['id']}",
        {"translations": json.dumps(translations, ensure_ascii=False)},
    )
    click.echo(f"Deleted '{key}' from language {iso_code}.")
