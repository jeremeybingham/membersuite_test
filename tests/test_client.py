import json
from datetime import date

import httpx
import pytest

from msuite import audit
from msuite.catalog import lookup
from msuite.client import ApiError, Client, extract_rows
from msuite.config import ConfigError, Settings, load_settings
from msuite.export import flatten, profile, shape, write_csv

SETTINGS = Settings(tenant_id=123, username="user", password="secret")


def fake_api(rows_total=7, expire_first=False):
    """An in-memory API: sign-in, and a search that serves `rows_total` rows in pages."""
    state = {"signins": 0, "expired": expire_first}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/platform/v2/authtoken/123":
            state["signins"] += 1
            return httpx.Response(200, text=f'"Bearer tok{state["signins"]}"')
        if request.headers.get("Authorization", "").startswith("Bearer ") is False:
            return httpx.Response(401)
        if state["expired"]:
            state["expired"] = False
            return httpx.Response(401)
        if request.url.path == "/crm/v1/individuals/123":
            page = int(request.url.params["page"])
            size = int(request.url.params["pageSize"])
            ids = range(page * size, min(rows_total, (page + 1) * size))
            return httpx.Response(200, json={"data": [{"id": i} for i in ids]})
        if request.url.path == "/platform/v2/search/executeSearch":
            body = json.loads(request.content)
            assert set(body) == {"msql", "page", "pageSize"}
            return httpx.Response(200, json=[{"ID": "x"}] if body["page"] == 0 else [])
        return httpx.Response(404)

    return Client(SETTINGS, page_size=3, transport=httpx.MockTransport(handler)), state


def test_search_follows_pages_until_short_page():
    c, _ = fake_api(rows_total=7)
    assert [r["id"] for r in c.search("SELECT ID FROM Individual", "individuals")] == list(range(7))


def test_search_exact_multiple_of_page_size_stops():
    c, _ = fake_api(rows_total=6)
    assert c.count("individuals") == 6


def test_count_cap():
    c, _ = fake_api(rows_total=100)
    assert c.count("individuals", cap=5) == 5


def test_reauth_on_401():
    c, state = fake_api(expire_first=True)
    assert len(c.search_page("SELECT ID FROM Individual", 0, "individuals")) == 3
    assert state["signins"] == 2


def test_platform_search_posts_body():
    c, _ = fake_api()
    assert list(c.search("SELECT ID FROM Committee")) == [{"ID": "x"}]


def test_http_error_raises():
    c, _ = fake_api()
    with pytest.raises(ApiError):
        c.get_json("/nope/{tenant}")


@pytest.mark.parametrize(
    "payload,n",
    [([{"a": 1}], 1), ({"data": [{"a": 1}]}, 1), ({"data": {"results": [{}, {}]}}, 2), ({}, 0)],
)
def test_extract_rows(payload, n):
    assert len(extract_rows(payload)) == n


def test_lookup_by_segment_or_type():
    assert lookup("memberships").type == "Membership"
    assert lookup("Membership").module == "membership"
    with pytest.raises(KeyError):
        lookup("nothing")


def test_settings_repr_hides_password():
    assert "secret" not in repr(SETTINGS)


def test_load_settings_requires_values(monkeypatch, tmp_path):
    for k in ("MS_TENANT_ID", "MS_USERNAME", "MS_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ConfigError):
        load_settings(tmp_path / "missing.env", prompt=False)
    env = tmp_path / ".env"
    env.write_text("MS_TENANT_ID=42\nMS_USERNAME=a\nMS_PASSWORD=b\n")
    s = load_settings(env, prompt=False)
    assert (s.tenant_id, s.base_url) == (42, "https://rest.membersuite.com")


def test_flatten_and_csv(tmp_path):
    assert flatten({"a": {"b": 1}, "c": [1, 2]}) == {"a.b": 1, "c": "[1, 2]"}
    p = tmp_path / "x.csv"
    assert write_csv([{"a": 1}, {"b": "Zz9"}], p) == 2
    prof = {r["column"]: r for r in profile(p)}
    assert prof["a"]["filled"] == 1 and prof["b"]["top_shape"] == "aa9"
    assert shape("AB-12") == "aa-99"


def test_member_summary_definitions():
    rows = [
        {"owner": "o1", "status": "Active", "receivesMemberBenefits": True,
         "expirationDate": "2027-01-01T00:00:00"},
        {"owner": "o1", "status": "Active", "receivesMemberBenefits": True,
         "expirationDate": "2027-06-01"},  # second record, same owner
        {"Owner": "o2", "Status": "Lapsed", "ReceivesMemberBenefits": False,
         "ExpirationDate": "2025-01-01"},
        {"owner": {"name": "o3"}, "status": "Active", "receivesMemberBenefits": True,
         "expirationDate": None, "terminationDate": "2026-01-01"},
    ]  # fmt: skip
    s = audit.member_summary(rows, today=date(2026, 11, 17))
    assert s["membership_records"] == 4
    assert s["receives_member_benefits"] == 3
    assert s["benefits_and_unexpired"] == 2
    assert s["distinct_owners_benefits_and_unexpired"] == 1
    assert s["by_status"] == {"Active": 3, "Lapsed": 1}
