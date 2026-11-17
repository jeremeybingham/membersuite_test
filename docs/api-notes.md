# MemberSuite API notes

What we know about the API, from the Swagger specs saved in [`api-spec/`](api-spec/) on
2026-11-17. Items marked **unverified** need checking against the live system on the first run.

## Sources

| Link | What it is |
|---|---|
| https://rest.membersuite.com/platform/swagger/ui/index | Swagger UI for the `platform` module. Its spec is at `/platform/swagger/docs/v2` |
| `https://rest.membersuite.com/<module>/swagger/docs/v1` | The specs for the other 13 modules (found by probing; saved in `api-spec/`) |
| https://api.membersuite.com/ | Landing page only: "REST & GraphQL API". No GraphQL docs found |
| http://api.docs.membersuite.com/ | Help-site shell; reset connections or served an empty template on 2026-11-17. Not used |

## Shape of the API

- One web app per module: `platform` (v2), and `crm`, `membership`, `financial`, `orders`,
  `events`, `committees`, `certifications`, `awards`, `fundraising`, `exhibits`, `subscriptions`,
  `discussions`, `documents`, `careercenter` (all v1). `src/msuite/catalog.json` maps 299 objects
  to their module and MSQL type name.
- Each object has the same routes:
  `GET /{module}/v1/{objects}/{tenantId}?msql=&page=&pageSize=` (search, page is zero-based),
  `GET .../{objects}/{id}` (full record), `GET .../{objects}/description/{tenantId}` (field
  metadata, including custom fields), plus POST/PUT/DELETE which this harness never calls.
- General search across any object: `GET /platform/v2/search/{tenantId}` or
  `POST /platform/v2/search/executeSearch` with `{"msql", "page", "pageSize"}`.
- A search returns only the fields the statement selects. MSQL example from the spec:
  `SELECT ID, Name FROM Committee WHERE IsActive = true ORDER BY Name`.
- Custom fields are top-level properties named like `MeetingRoom__c`; they are not in the
  Swagger schemas, only in each object's `description` endpoint.

## Sign-in

- `POST /platform/v2/authtoken/{tenantId}` with `{"username", "password"}` returns the text
  `Bearer <token>` for the `Authorization` header. The harness uses this.
- `POST /platform/v2/loginUser/{tenantId}` with `{"email", "password"}` returns id, access and
  refresh tokens (described as the *portal* sign-in); `POST /platform/v2/refreshtoken` renews.
- **Unverified:** whether a staff (console) user signs in through `authtoken/{tenantId}`. The spec
  also lists `/platform/v1/consoleAuthData` and `msc_authdata/{tenantId}`. If `msuite ping` fails
  with a good password, try those next.

## Unverified until the first live run

- How a page of results is wrapped (the spec says only `Object`). `extract_rows` accepts a bare
  list or `data`/`results`/`items`-style wrappers; `msuite ping` prints the keys it saw.
- Whether MSQL field names are PascalCase in statements and camelCase in results; the code
  matches field names case-insensitively.
- Whether `ORDER BY CreatedDate DESC` works on every object (the inventory records an error per
  object if not).
- Page size limit and rate limits: none documented. Default page size is 500; lower it with
  `--page-size` if requests fail.
- No COUNT in the spec, so counts page through IDs (capped at 50,000 by default).

## Not available through the API (as far as the specs show)

API keys and API users, webhooks, audit/login logs, user accounts and security roles. These
come from staff and MemberSuite support (see the audit plan).
