"""Tests for the ActionKit HTTP client."""

import httpx
import pytest

from actionkit_cli.client import ActionKitClient

BASE = "https://ak.test"
CREATED = f"{BASE}/rest/v1/user/2447618/"


def make_client(handler):
    client = ActionKitClient(BASE, "u", "p")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_post_returns_the_response_body_when_there_is_one():
    def handler(request):
        return httpx.Response(200, json={"id": 1})

    assert make_client(handler).post("user", {"email": "a@b.eu"}) == {"id": 1}


def test_post_follows_the_location_header_when_the_body_is_empty():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(201, headers={"Location": CREATED})
        assert str(request.url) == CREATED
        return httpx.Response(200, json={"id": 2447618, "email": "a@b.eu"})

    result = make_client(handler).post("user", {"email": "a@b.eu"})
    assert result == {"id": 2447618, "email": "a@b.eu"}


def test_post_reports_the_location_when_the_created_object_cannot_be_fetched():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(201, headers={"Location": CREATED})
        return httpx.Response(403)

    assert make_client(handler).post("user", {}) == {"resource_uri": CREATED}


def test_post_returns_empty_when_there_is_no_location():
    def handler(request):
        return httpx.Response(204)

    assert make_client(handler).post("user", {}) == {}


def test_post_still_raises_on_an_error_status():
    def handler(request):
        return httpx.Response(400, json={"email": ["required"]})

    with pytest.raises(httpx.HTTPStatusError):
        make_client(handler).post("user", {})
