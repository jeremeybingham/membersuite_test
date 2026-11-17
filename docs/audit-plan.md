# Light audit plan

**Goal.** Give the incoming CEO a clear picture of how staff use MemberSuite: what is used, what is
set up but abandoned, what has been customized or connected to other systems, and what needs to
change. Settle the open question of the real member count along the way.

**Approach.** Data first, then people. The API shows *what* is in the system and *when* it was
last touched; staff interviews explain *why*. About two weeks of part-time effort.

**Ground rules.** A dedicated read-only user ([`credentials.md`](credentials.md)). All extracts stay
in `local-data/`. Findings shared with the CEO are counts and patterns, never member rows.

## Phase 0: Access and context (day 1–2)

- [ ] Read-only API user and tenant id; `msuite ping` passes.
- [ ] From the organization: the MemberSuite contract and **which modules are licensed**, the
      vendor's account manager, the list of staff users and their roles, any implementation or
      consultant documents from the original rollout.
- [ ] From the board/finance: the member number currently reported (board deck, annual report,
      dues revenue). We will reconcile against it.

## Phase 1: Feature usage inventory (day 2–3)

```sh
uv run msuite inventory          # every object; record count and newest created/modified date
```

Read `local-data/audit/<date>/inventory.csv` and sort each object into one of:

| Class | Signal | Means |
|---|---|---|
| **Active** | records, and created in the last 3 months | part of daily work |
| **Seasonal** | records, newest within 12 months | annual cycles (renewals, conference, awards) |
| **Dormant** | records, nothing new in 12+ months | tried and dropped, or work moved elsewhere |
| **Set up, not used** | configuration objects exist, transactions do not (e.g. event types but no registrations) | an implementation that did not land |
| **Unused** | zero records, or 403 | not licensed, or never adopted |

Output: a one-page usage map by module (CRM, membership, finance, orders, events, committees,
certifications, awards, fundraising, exhibits, subscriptions, discussions, documents, career
center). Paying for modules in the last two rows is a quick win.

## Phase 2: Customizations (day 3–4)

```sh
uv run msuite config                 # custom fields/objects, forms, searches, templates, setup
uv run msuite describe individuals   # repeat for organizations, memberships, events, orders...
```

Questions to answer:

- **Custom fields:** how many per object, and are they filled? Export them
  (`msuite export individuals --fields "ID, <field>__c, ..."`) and run `msuite profile`.
  Fields under ~5% filled are clutter; fields at 100% may be doing work the standard fields
  should do.
- **Custom objects:** what business processes were built inside the AMS, and are their
  instances still being created?
- **Saved and scheduled searches:** how many, who built them, when last changed. A large pile of
  one-off searches means staff work around the standard reports; scheduled searches show which
  reports someone depends on every week.
- **Templates:** email and mail-merge templates in use vs. stale.
- **Membership structure:** membership organizations, types, statuses, chapters, sections,
  organizational layers. Complex structures are where member counts go wrong (Phase 4).

## Phase 3: Integrations (day 4–5)

From the API:

- **Payments:** which merchant accounts are configured (Authorize.Net, BluePay, PayPal,
  Payflow Pro, Priority Payments). More than one active gateway is worth a question.
- **Shipping:** FedEx, UPS and USPS carrier accounts (is there a store or fulfillment?).
- **Who writes the data.** For the high-volume objects, pull the audit fields and group by
  writer. Integration and import accounts show up as "users" that create thousands of records.

  ```sh
  uv run msuite query "SELECT ID, CreatedBy, CreatedDate, LastModifiedBy FROM Individual" \
      --entity individuals --out local-data/audit/individual_writers.csv
  duckdb -c "SELECT CreatedBy, count(*), max(CreatedDate)
             FROM 'local-data/audit/individual_writers.csv' GROUP BY 1 ORDER BY 2 DESC"
  ```

  Repeat for orders, payments, event registrations and memberships. This is also the best
  picture of **which staff do what**, and how much volume runs through each person.

From staff and the vendor (not visible in the API):

- Website and member portal: single sign-on (the API has JWT, OIDC and SSO routes), a community
  platform, an LMS, an email marketing tool, accounting export (GL, batches), Logi reporting.
- API users and keys issued, webhooks, scheduled imports and exports, middleware (Zapier and the
  like), and any spreadsheets that are the real system of record for something.

Output: an integration map: system, direction, how (API, file, manual), owner, and whether it
works.

## Phase 4: The member count (day 5–6)

```sh
uv run msuite members
```

This prints counts under several definitions side by side: membership records, records that
grant member benefits, unexpired and not terminated, both, distinct owners, and breakdowns by
status, type, membership organization and expiry year. The differences between those lines are
the findings. Questions to settle with staff:

- Is a member a **person or an organization**? For organizational memberships, are the
  individuals under them counted?
- Does renewal **extend one record or create a new one**? (Many records per owner means the
  latter; count distinct owners.)
- **Grace period:** are expired members in grace counted?
- Which statuses count (active, pending, complimentary, lifetime, honorary, staff, emeritus)?
- **Chapters and sections:** are those memberships separate products that inflate a raw count?
- Does the number match **dues revenue** for the year? A gap points at comps, discounts or
  records not tied to payment.

Output: one agreed definition, the number under it, and how it compares with the number
currently reported.

## Phase 5: Data quality (day 6–7, in parallel)

Export the core objects and `msuite profile` them: fill rates for email, address, phone,
member type; obvious duplicates (same email on several individuals, via DuckDB); individuals
with no organization; records with no activity in years. Summarize as counts.

## Phase 6: Staff interviews (week 2)

30–45 minutes each with membership, finance, events, communications and whoever administers
MemberSuite. Bring their slice of the usage map. Ask:

1. Walk me through your busiest week in the system.
2. What do you do outside MemberSuite (spreadsheets, other tools) and why?
3. Which reports do you trust? Which do you rebuild by hand?
4. What did the implementation promise that never worked?
5. Who do you call when something breaks, and how fast is the vendor?
6. If you could change one thing tomorrow, what would it be?

## Deliverable

A short memo to the CEO (markdown), with:

1. Usage map by module (active / seasonal / dormant / unused) and licensing implications.
2. Customization register: what was built, whether it is used, what to retire.
3. Integration map and the manual workarounds that sit between systems.
4. The member count: the definition, the number, the reconciliation.
5. Data quality headline numbers.
6. Staff pain points, and a ranked list of recommendations: quick fixes, process changes,
   training, and whether the platform itself is the problem.

## Open questions

| Question | How we answer it | Status |
|---|---|---|
| Accurate member count | Phase 4, plus the definition agreed with CEO and staff | open |
| Which modules are licensed and at what cost | Contract, vendor | open |
| Does a staff user sign in through `authtoken/{tenantId}`? | First `msuite ping` ([`api-notes.md`](api-notes.md)) | open |
| How search results are wrapped, field-name case | First `msuite ping` | open |
| API page size and rate limits | First inventory run; ask the vendor | open |
| Is the GraphQL API (mentioned on api.membersuite.com) worth using? | Ask the vendor for docs | open |
