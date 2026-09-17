"""Tests for the hand-written transaction commands."""

from click.testing import CliRunner

from actionkit_cli.cli import cli
from tests.test_generic import StubClient

BASE = ["transaction", "create", "--order", "7", "--account", "a", "--amount", "5"]


def run(args):
    client = StubClient()
    result = CliRunner().invoke(cli, args, obj=client)
    return result, client


def test_extra_field_supports_json_typing():
    result, client = run(BASE + ["-f", "ordering:=1"])
    assert result.exit_code == 0, result.output
    assert client.posted[0][1]["ordering"] == 1


def test_extra_field_still_supports_plain_strings():
    result, client = run(BASE + ["-f", "note=hello"])
    assert result.exit_code == 0, result.output
    assert client.posted[0][1]["note"] == "hello"


def test_extra_field_rejects_a_pair_without_equals():
    result, client = run(BASE + ["-f", "nope"])
    assert result.exit_code != 0
    assert client.posted == []
