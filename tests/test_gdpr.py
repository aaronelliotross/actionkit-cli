"""Tests for the GDPR article 15 export command."""

import json

import httpx
from click.testing import CliRunner

from actionkit_cli.cli import cli

USER = {
    "id": 7,
    "email": "a@b.eu",
    "fields": {"preferred_currency": "EUR"},
    "phones": [],
    "actions": "/rest/v1/action/?user=7",
    "events": "/rest/v1/event/?creator=7",
    "orders": "/rest/v1/order/?user=7",
    "usermailings": "/rest/v1/usermailing/?user=7",
    "location": "/rest/v1/location/7/",
    "useroriginal": "/rest/v1/useroriginal/7/",
    "lang": "/rest/v1/language/106/",
    "resource_uri": "/rest/v1/user/7/",
}


def page(objects, next_url=None):
    return {"meta": {"next": next_url, "total_count": len(objects)}, "objects": objects}


class PagedClient:
    """Serves canned pages per resource, keyed by offset."""

    def __init__(self, pages=None, users=None):
        self.users = users if users is not None else [USER]
        self.pages = pages or {}
        self.listed = []
        self.fetched = []
        self.raise_for = None

    def list(self, resource, **kwargs):
        self.listed.append((resource, kwargs))
        if resource == self.raise_for:
            request = httpx.Request("GET", f"https://ak/rest/v1/{resource}/")
            response = httpx.Response(500, request=request, json={"error": "boom"})
            raise httpx.HTTPStatusError("boom", request=request, response=response)
        if resource == "user":
            return page(self.users)
        return self.pages.get((resource, kwargs.get("offset", 0)), page([]))

    def get(self, path, params=None):
        self.fetched.append(path)
        return {"resource_uri": f"/rest/v1/{path}"}

    def close(self):
        pass


def run(args, client=None):
    client = client or PagedClient()
    result = CliRunner().invoke(cli, ["gdpr", "export", *args], obj=client)
    return result, client


def test_looks_up_the_user_by_email():
    _, client = run(["a@b.eu"])
    assert client.listed[0] == ("user", {"email": "a@b.eu"})


def test_unknown_email_fails_without_fetching_anything_else():
    result, client = run(["nobody@b.eu"], PagedClient(users=[]))
    assert result.exit_code != 0
    assert "nobody@b.eu" in result.output
    assert [r for r, _ in client.listed] == ["user"]
    assert client.fetched == []


def test_follows_every_list_link_on_the_user_record():
    _, client = run(["a@b.eu"])
    listed = client.listed[1:]
    assert ("action", {"limit": 100, "offset": 0, "user": "7"}) in listed
    assert ("event", {"limit": 100, "offset": 0, "creator": "7"}) in listed
    assert ("order", {"limit": 100, "offset": 0, "user": "7"}) in listed


def test_skips_mailings():
    _, client = run(["a@b.eu"])
    assert "usermailing" not in [r for r, _ in client.listed]


def test_fetches_transactions_through_the_users_orders():
    _, client = run(["a@b.eu"])
    assert ("transaction", {"limit": 100, "offset": 0, "order__user": 7}) in (
        client.listed
    )


def test_fetches_location_and_original_record_but_not_other_detail_links():
    _, client = run(["a@b.eu"])
    assert client.fetched == ["location/7/", "useroriginal/7/"]


def test_follows_pagination_until_there_is_no_next_page():
    pages = {
        ("action", 0): page([{"id": 1}], next_url="/rest/v1/action/?_offset=100"),
        ("action", 100): page([{"id": 2}]),
    }
    result, _ = run(["a@b.eu"], PagedClient(pages=pages))
    assert result.exit_code == 0, result.output
    assert [a["id"] for a in json.loads(result.stdout)["actions"]] == [1, 2]


def test_output_contains_user_and_every_section():
    result, _ = run(["a@b.eu"])
    data = json.loads(result.stdout)
    assert data["email"] == "a@b.eu"
    assert data["user"] == USER
    assert "exported_at" in data
    for key in ["actions", "events", "orders", "transactions"]:
        assert data[key] == []
    assert data["location"] == {"resource_uri": "/rest/v1/location/7/"}
    assert "usermailings" not in data


def test_writes_to_output_file(tmp_path):
    out = tmp_path / "export.json"
    result, _ = run(["a@b.eu", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text())["user"]["id"] == 7


def test_api_error_aborts_the_whole_export(tmp_path):
    client = PagedClient()
    client.raise_for = "order"
    out = tmp_path / "export.json"
    result, _ = run(["a@b.eu", "--output", str(out)], client)
    assert result.exit_code != 0
    assert not out.exists()


def test_unwritable_output_path_fails_before_fetching_anything(tmp_path):
    out = tmp_path / "missing" / "export.json"
    result, client = run(["a@b.eu", "--output", str(out)])
    assert result.exit_code != 0
    assert "Cannot write" in result.output
    assert client.listed == []
