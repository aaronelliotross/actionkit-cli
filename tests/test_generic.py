"""Tests for the generic per-resource commands."""

import json

import click
import httpx
from click.testing import CliRunner

from actionkit_cli.cli import cli


class StubClient:
    """Records calls and returns canned responses."""

    def __init__(self, post_result=None, list_result=None, detail_result=None):
        self.posted = []
        self.listed = []
        self.detailed = []
        self._post_result = post_result if post_result is not None else {"id": 1}
        self._list_result = (
            list_result
            if list_result is not None
            else {"meta": {"total_count": 0, "offset": 0, "limit": 20}, "objects": []}
        )
        self._detail_result = detail_result if detail_result is not None else {"id": 42}
        self.raise_on_post = None

    def post(self, path, data=None):
        self.posted.append((path, data))
        if self.raise_on_post is not None:
            raise self.raise_on_post
        return self._post_result

    def list(self, resource, **kwargs):
        self.listed.append((resource, kwargs))
        return self._list_result

    def detail(self, resource, resource_id):
        self.detailed.append((resource, resource_id))
        return self._detail_result

    def close(self):
        pass


def run(args, client=None, **kwargs):
    client = client or StubClient()
    result = CliRunner().invoke(cli, args, obj=client, **kwargs)
    return result, client


def http_error(status, url, body):
    request = httpx.Request("POST", url)
    response = httpx.Response(status, request=request, json=body)
    return httpx.HTTPStatusError("boom", request=request, response=response)


# --- create ----------------------------------------------------------------


def test_create_posts_parsed_assignments_to_the_resource():
    result, client = run(["field", "create", "field_name=first_name", "ordering:=1"])
    assert result.exit_code == 0, result.output
    assert client.posted == [("field", {"field_name": "first_name", "ordering": 1})]


def test_create_prints_the_created_object():
    result, _ = run(["field", "create", "a=b"], StubClient(post_result={"id": 99}))
    assert "99" in result.output


def test_create_accepts_a_pasted_resource_uri_as_the_resource_name():
    result, client = run(["/rest/v1/field/", "create", "a=b"])
    assert result.exit_code == 0, result.output
    assert client.posted[0][0] == "field"


def test_create_reads_a_base_body_from_a_json_file(tmp_path):
    payload = tmp_path / "fields.json"
    payload.write_text(json.dumps({"field_name": "first_name", "ordering": 1}))
    result, client = run(["field", "create", "--json", str(payload)])
    assert result.exit_code == 0, result.output
    assert client.posted[0][1] == {"field_name": "first_name", "ordering": 1}


def test_assignments_override_the_json_file(tmp_path):
    payload = tmp_path / "fields.json"
    payload.write_text(json.dumps({"field_name": "first_name", "ordering": 1}))
    result, client = run(
        [
            "field",
            "create",
            "--json",
            str(payload),
            "field_name=last_name",
            "ordering:=2",
        ]
    )
    assert result.exit_code == 0, result.output
    assert client.posted[0][1] == {"field_name": "last_name", "ordering": 2}


def test_create_reads_a_base_body_from_stdin():
    result, client = run(
        ["field", "create", "--json", "-"], input='{"field_name": "x"}'
    )
    assert result.exit_code == 0, result.output
    assert client.posted[0][1] == {"field_name": "x"}


def test_create_rejects_a_json_file_that_is_not_an_object(tmp_path):
    payload = tmp_path / "bad.json"
    payload.write_text("[1, 2]")
    result, client = run(["field", "create", "--json", str(payload)])
    assert result.exit_code != 0
    assert "object" in result.output
    assert client.posted == []


def test_create_rejects_malformed_json_input(tmp_path):
    payload = tmp_path / "bad.json"
    payload.write_text("{oops")
    result, client = run(["field", "create", "--json", str(payload)])
    assert result.exit_code != 0
    assert client.posted == []


def test_create_with_no_data_is_rejected():
    result, client = run(["field", "create"])
    assert result.exit_code != 0
    assert client.posted == []


def test_dry_run_prints_the_body_without_posting():
    result, client = run(["field", "create", "ordering:=1", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert client.posted == []
    assert "ordering" in result.output


def test_create_reports_an_unknown_resource_on_404():
    client = StubClient()
    client.raise_on_post = http_error(404, "https://ak.test/rest/v1/usr/", {})
    result, _ = run(["usr", "create", "a=b"], client)
    assert result.exit_code != 0
    assert "usr" in result.output
    assert "404" in result.output


def test_create_shows_the_response_body_on_a_validation_error():
    client = StubClient()
    client.raise_on_post = http_error(
        400, "https://ak.test/rest/v1/field/", {"field_name": ["required"]}
    )
    result, _ = run(["field", "create", "a=b"], client)
    assert result.exit_code != 0
    assert "400" in result.output
    assert "required" in result.output


# --- list ------------------------------------------------------------------


def test_list_passes_assignments_as_filters():
    result, client = run(["field", "list", "form_id=3708"])
    assert result.exit_code == 0, result.output
    resource, kwargs = client.listed[0]
    assert resource == "field"
    assert kwargs["form_id"] == "3708"


def test_list_passes_pagination_options():
    result, client = run(["field", "list", "-l", "5", "-o", "10", "--order-by", "id"])
    assert result.exit_code == 0, result.output
    _, kwargs = client.listed[0]
    assert kwargs["limit"] == 5
    assert kwargs["offset"] == 10
    assert kwargs["order_by"] == "id"


def test_list_derives_columns_from_the_returned_objects():
    client = StubClient(
        list_result={
            "meta": {"total_count": 1, "offset": 0, "limit": 20},
            "objects": [{"id": 1, "field_name": "first_name"}],
        }
    )
    result, _ = run(["field", "list"], client)
    assert result.exit_code == 0, result.output
    assert "field_name" in result.output


def test_list_caps_the_number_of_columns():
    wide = {f"col{i}": i for i in range(20)}
    client = StubClient(
        list_result={
            "meta": {"total_count": 1, "offset": 0, "limit": 20},
            "objects": [wide],
        }
    )
    result, _ = run(["field", "list"], client)
    assert result.exit_code == 0, result.output
    assert "col19" not in result.output


def test_list_json_prints_the_raw_response():
    client = StubClient(
        list_result={
            "meta": {"total_count": 1, "offset": 0, "limit": 20},
            "objects": [{"id": 1, "field_name": "first_name"}],
        }
    )
    result, _ = run(["field", "list", "--json"], client)
    assert result.exit_code == 0, result.output
    assert "meta" in result.output


# --- get -------------------------------------------------------------------


def test_get_fetches_the_detail_endpoint():
    result, client = run(["field", "get", "42"])
    assert result.exit_code == 0, result.output
    assert client.detailed == [("field", 42)]


# --- dispatch --------------------------------------------------------------


def test_registered_groups_are_not_shadowed_by_the_fallback():
    result, client = run(["user", "get", "123"])
    assert result.exit_code == 0, result.output
    assert client.detailed == [("user", 123)]


def test_registered_group_keeps_its_own_create():
    result, client = run(
        ["transaction", "create", "--order", "7", "--account", "acct", "--amount", "5"]
    )
    assert result.exit_code == 0, result.output
    assert client.posted[0][0] == "transaction"
    assert client.posted[0][1]["order"] == "/rest/v1/order/7/"


def test_only_registered_groups_are_listed_as_commands():
    ctx = click.Context(cli)
    assert "user" in cli.list_commands(ctx)
    assert "field" not in cli.list_commands(ctx)


def test_help_lists_the_registered_groups():
    result = CliRunner().invoke(cli, ["--help"], obj=StubClient())
    assert result.exit_code == 0
    assert "user" in result.output


def test_an_option_is_not_mistaken_for_a_resource():
    result = CliRunner().invoke(cli, ["--nope"], obj=StubClient())
    assert result.exit_code != 0
    assert "No such" in result.output or "no such" in result.output.lower()


# --- generic verbs on registered groups ------------------------------------


def test_registered_group_gains_a_generic_create():
    result, client = run(["user", "create", "email=a@b.eu"])
    assert result.exit_code == 0, result.output
    assert client.posted == [("user", {"email": "a@b.eu"})]


def test_page_gains_a_generic_create():
    result, client = run(["page", "create", "name=x", "type=Petition"])
    assert result.exit_code == 0, result.output
    assert client.posted == [("page", {"name": "x", "type": "Petition"})]


def test_generic_create_does_not_replace_a_groups_own_create():
    result, client = run(
        ["transaction", "create", "--order", "7", "--account", "a", "--amount", "5"]
    )
    assert result.exit_code == 0, result.output
    assert client.posted[0][1]["order"] == "/rest/v1/order/7/"


def test_generic_commands_do_not_replace_a_groups_own_list():
    result, client = run(["user", "list", "--country", "DE"])
    assert result.exit_code == 0, result.output
    assert client.listed[0][1]["country"] == "DE"


def test_utility_groups_do_not_gain_resource_commands():
    """report and translation do not map 1:1 onto a REST resource."""
    ctx = click.Context(cli)
    assert "create" not in cli.get_command(ctx, "report").commands
    assert "create" not in cli.get_command(ctx, "translation").commands


def test_hash_stays_a_plain_command():
    ctx = click.Context(cli)
    assert not isinstance(cli.get_command(ctx, "hash"), click.Group)
