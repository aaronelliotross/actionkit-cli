"""Parsing of KEY=VALUE assignments given on the command line."""

import json
from pathlib import Path

import click

JSON_SEP = ":="
PLAIN_SEP = "="


def _split(pair: str) -> tuple[str, str, bool]:
    """Split a pair into (key, raw_value, is_json) at its first separator."""
    json_at = pair.find(JSON_SEP)
    plain_at = pair.find(PLAIN_SEP)

    if json_at != -1 and (plain_at == -1 or json_at < plain_at):
        return pair[:json_at], pair[json_at + len(JSON_SEP) :], True
    if plain_at != -1:
        return pair[:plain_at], pair[plain_at + len(PLAIN_SEP) :], False
    raise click.BadParameter(
        f"{pair!r} is not an assignment. Use KEY=VALUE or KEY:=JSON."
    )


def _read_file(path: str, pair: str) -> str:
    try:
        return Path(path).read_text()
    except OSError as exc:
        raise click.BadParameter(f"Cannot read {path!r} in {pair!r}: {exc.strerror}")


def _decode(raw: str, pair: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON in {pair!r}: {exc.msg}")


def parse_assignments(pairs) -> dict:
    """Build a request body from KEY=VALUE arguments.

    KEY=VALUE     the value is always a string
    KEY:=JSON     the value is parsed as JSON (int, bool, null, array, object)
    KEY=@PATH     the value is the contents of PATH, as a string
    KEY:=@PATH    the value is the contents of PATH, parsed as JSON

    Later assignments override earlier ones.
    """
    data = {}
    for pair in pairs:
        key, raw, is_json = _split(pair)
        if not key:
            raise click.BadParameter(f"{pair!r} has an empty key.")
        if raw.startswith("@"):
            raw = _read_file(raw[1:], pair)
        data[key] = _decode(raw, pair) if is_json else raw
    return data
