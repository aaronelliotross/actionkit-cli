"""ActionKit REST API client."""

import httpx


class ActionKitClient:
    """HTTP client for the ActionKit REST API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/rest/v1"
        self._client = httpx.Client(
            auth=(username, password),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
        )

    def _url(self, path: str) -> str:
        return f"{self.api_url}/{path.strip('/')}/"

    def get(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(self._url(path), params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict | None = None) -> dict:
        resp = self._client.post(self._url(path), json=data)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def put(self, path: str, data: dict) -> dict:
        resp = self._client.put(self._url(path), json=data)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def patch(self, path: str, data: dict) -> dict:
        resp = self._client.patch(self._url(path), json=data)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def delete(self, path: str) -> None:
        resp = self._client.delete(self._url(path))
        resp.raise_for_status()

    def list(
        self,
        resource: str,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        **filters,
    ) -> dict:
        params = {"_limit": limit, "_offset": offset}
        if order_by:
            params["order_by"] = order_by
        params.update(filters)
        return self.get(resource, params=params)

    def detail(self, resource: str, resource_id: int) -> dict:
        return self.get(f"{resource}/{resource_id}")

    def close(self):
        self._client.close()
