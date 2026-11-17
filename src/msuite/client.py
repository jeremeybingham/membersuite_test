"""A small MemberSuite REST client: sign in, run MSQL searches page by page, describe objects.

Conventions (from the Swagger specs in docs/api-spec/):
- Sign-in: POST /platform/v2/authtoken/{tenantId} with {"username", "password"} returns the
  text "Bearer <token>", used as the Authorization header. Tokens are short-lived; on a 401 we
  sign in again.
- Search: GET /{module}/{version}/{entity}/{tenantId}?msql=...&page=N&pageSize=M (page is
  zero-based), or POST /platform/v2/search/executeSearch with {"msql", "page", "pageSize"} for
  any object type.
- The specs do not say how a page of results is wrapped, so `extract_rows` accepts a bare list
  or the common wrappers ({"data": ...}, {"results": [...]}). Check it against a real response.
"""

from collections.abc import Iterator
from typing import Any

import httpx

from .catalog import Entity, lookup
from .config import Settings

ROW_KEYS = ("results", "Results", "items", "records", "rows", "value", "data", "Data")


class ApiError(RuntimeError):
    pass


def extract_rows(payload: Any) -> list[dict]:
    """Pull the list of records out of a search response, whatever wrapper it comes in."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ROW_KEYS:
            if key in payload and payload[key] is not None:
                return extract_rows(payload[key])
        return []
    return []


class Client:
    def __init__(
        self,
        settings: Settings,
        page_size: int = 500,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.settings = settings
        self.tenant = settings.tenant_id
        self.page_size = page_size
        self._auth: str | None = None
        self.http = httpx.Client(
            base_url=settings.base_url,
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    # --- auth ---------------------------------------------------------------------------------

    def sign_in(self) -> None:
        r = self.http.post(
            f"/platform/v2/authtoken/{self.tenant}",
            json={"username": self.settings.username, "password": self.settings.password},
        )
        if r.status_code != 200:
            raise ApiError(f"sign-in failed: HTTP {r.status_code}")
        token = r.text.strip().strip('"')
        self._auth = token if token.lower().startswith("bearer ") else f"Bearer {token}"

    def request(self, method: str, path: str, **kw) -> httpx.Response:
        if self._auth is None:
            self.sign_in()
        for attempt in (1, 2):
            r = self.http.request(method, path, headers={"Authorization": self._auth}, **kw)
            if r.status_code == 401 and attempt == 1:
                self.sign_in()  # token expired: sign in once more
                continue
            break
        if r.status_code >= 400:
            raise ApiError(f"{method} {path}: HTTP {r.status_code} {r.text[:200]}")
        return r

    def get_json(self, path: str, **params) -> Any:
        return self.request("GET", path.format(tenant=self.tenant), params=params or None).json()

    # --- metadata -----------------------------------------------------------------------------

    def association_info(self) -> Any:
        """Public association settings (name, currency, time zone); needs no sign-in."""
        r = self.http.get(f"/platform/v2/association/information/{self.tenant}")
        r.raise_for_status()
        return r.json()

    def get(self, entity: str | Entity, record_id: str) -> Any:
        """One full record by id (searches return only the selected fields)."""
        e = entity if isinstance(entity, Entity) else lookup(entity)
        return self.get_json(f"/{e.module}/{e.version}/{e.entity}/{record_id}")

    def describe(self, entity: str | Entity) -> Any:
        """Field metadata for an object, including this association's custom fields."""
        e = entity if isinstance(entity, Entity) else lookup(entity)
        return self.get_json(e.describe_path)

    # --- search -------------------------------------------------------------------------------

    def search_page(self, msql: str, page: int, entity: str | Entity | None = None) -> list[dict]:
        if entity is None:
            payload = self.request(
                "POST",
                "/platform/v2/search/executeSearch",
                json={"msql": msql, "page": page, "pageSize": self.page_size},
            ).json()
        else:
            e = entity if isinstance(entity, Entity) else lookup(entity)
            payload = self.get_json(e.search_path, msql=msql, page=page, pageSize=self.page_size)
        return extract_rows(payload)

    def search(
        self, msql: str, entity: str | Entity | None = None, max_rows: int | None = None
    ) -> Iterator[dict]:
        """Yield every row of an MSQL query, following pages until a short page comes back.

        With `entity`, the module's own search endpoint is used; without it, the platform's
        general search (any object type the statement names).
        """
        page, sent = 0, 0
        while True:
            rows = self.search_page(msql, page, entity)
            for row in rows:
                yield row
                sent += 1
                if max_rows is not None and sent >= max_rows:
                    return
            if len(rows) < self.page_size:
                return
            page += 1

    def count(self, entity: str | Entity, where: str = "", cap: int | None = None) -> int:
        """Count records by paging through IDs (the specs show no COUNT endpoint)."""
        e = entity if isinstance(entity, Entity) else lookup(entity)
        msql = f"SELECT ID FROM {e.type}" + (f" WHERE {where}" if where else "")
        return sum(1 for _ in self.search(msql, e, max_rows=cap))

    def close(self) -> None:
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
