"""Tests for KEY=VALUE assignment parsing."""

import click
import pytest

from actionkit_cli.params import parse_assignments


def test_plain_assignment_yields_a_string():
    assert parse_assignments(["field_name=first_name"]) == {"field_name": "first_name"}


def test_multiple_assignments_are_collected():
    assert parse_assignments(["a=1", "b=2"]) == {"a": "1", "b": "2"}


def test_no_assignments_yields_empty_dict():
    assert parse_assignments([]) == {}


def test_empty_value_is_allowed():
    assert parse_assignments(["alternatives="]) == {"alternatives": ""}


def test_value_may_contain_equals_signs():
    assert parse_assignments(["q=a=b=c"]) == {"q": "a=b=c"}


def test_numeric_looking_string_keeps_leading_zero():
    assert parse_assignments(["zip=01234"]) == {"zip": "01234"}


def test_json_assignment_yields_an_int():
    assert parse_assignments(["ordering:=1"]) == {"ordering": 1}


def test_json_assignment_yields_a_bool():
    assert parse_assignments(["success:=true"]) == {"success": True}


def test_json_assignment_yields_null():
    assert parse_assignments(["failure_code:=null"]) == {"failure_code": None}


def test_json_assignment_yields_an_object():
    assert parse_assignments(['fields:={"a": "b"}']) == {"fields": {"a": "b"}}


def test_json_assignment_yields_an_array():
    assert parse_assignments(["tags:=[1, 2]"]) == {"tags": [1, 2]}


def test_json_assignment_yields_a_quoted_string():
    assert parse_assignments(['name:="1"']) == {"name": "1"}


def test_json_marker_wins_over_a_later_plain_equals():
    assert parse_assignments(["a:=1", "b=x:=y"]) == {"a": 1, "b": "x:=y"}


def test_file_assignment_reads_contents_as_a_string(tmp_path):
    body = tmp_path / "letter.html"
    body.write_text("<p>Dear friend</p>")
    assert parse_assignments([f"body=@{body}"]) == {"body": "<p>Dear friend</p>"}


def test_json_file_assignment_parses_contents(tmp_path):
    payload = tmp_path / "fields.json"
    payload.write_text('{"a": 1}')
    assert parse_assignments([f"fields:=@{payload}"]) == {"fields": {"a": 1}}


def test_literal_at_sign_is_not_treated_as_a_file():
    assert parse_assignments(["email=a@b.eu"]) == {"email": "a@b.eu"}


def test_later_assignment_overrides_an_earlier_one():
    assert parse_assignments(["a=1", "a=2"]) == {"a": "2"}


def test_missing_equals_is_rejected():
    with pytest.raises(click.BadParameter, match="first_name"):
        parse_assignments(["first_name"])


def test_empty_key_is_rejected():
    with pytest.raises(click.BadParameter):
        parse_assignments(["=value"])


def test_invalid_json_is_rejected():
    with pytest.raises(click.BadParameter, match="ordering"):
        parse_assignments(["ordering:=[1,"])


def test_missing_file_is_rejected():
    with pytest.raises(click.BadParameter, match="nope.html"):
        parse_assignments(["body=@nope.html"])
