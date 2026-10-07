# CashflowPot technical architecture

## 1. Repository roles

CashflowPot is split across two main application repositories:

- `iqmia/q_flow` — Flask backend, authoritative calculation engine, QAuth integration, portable JSON import endpoint, tests, and the source/build system for the public CashflowPot website.
- `iqmia/cashflowpot` — Flutter client deployed under `/app/`.

The public website source lives in `q_flow/site/` and is rendered to static HTML. It is not a Flask-rendered website at request time.

The backend/package name remains `q_flow` even though the product name is CashflowPot.

## 2. Production surfaces

The same domain exposes three independent surfaces:

```text
cashflowpot.com/      static public website
cashflowpot.com/app/  Flutter application
cashflowpot.com/api/  Flask API mounted by Passenger
```

The Flask application itself defines routes without an `/api` prefix. Passenger supplies that public prefix in production.

See [`deployment.md`](deployment.md) for the exact server layout and commands.

## 3. Flask application

`q_flow.create_app()` initializes the core extensions and registers the current blueprints:

- `projects` — project / QAuth Unit operations;
- `cashflows` — cash-flow scenario operations and portable scenario import;
- `activities` — activity CRUD and activity cash-flow updates;
- `users` — QAuth-facing user flows;
- `system` — system/health routes.

The application uses SQLAlchemy. The current file-system service configures the database as SQLite at:

```text
<STORAGE_PATH>/q_flow.db
```

Production `STORAGE_PATH` is currently configured under the q_flow server directory. Tests use a test storage location/configuration.

## 4. Project identity and QAuth

A CashflowPot **project** is represented externally by a QAuth Unit.

QAuth owns the project/unit identity and access context such as:

- Unit id;
- name;
- description;
- image/color;
- roles; and
- unit permissions.

The local q_flow database owns cash-flow scenarios and activities. Each scenario stores the QAuth `unit_id` that it belongs to.

Current permissions used by q_flow are:

```text
view:cashflow
edit:cashflow
```

Creating a new project creates a QAuth Unit and then creates a local `Base Cashflow` scenario for that Unit.

A QAuth Unit can own multiple local cash-flow scenarios.

## 5. Main local models

### `Cashflow`

`q_flow.models.cashflow.Cashflow` represents one independent financial scenario.

For compatibility, its physical database table remains named `project`.

Important groups of fields include:

- identity: `id`, `unit_id`, `name`, `description`;
- client terms: `advance`, `retention`, `release_retention_eop`, `dlp`, `duration_for_payment`;
- finance/value: `interest_rate`, `contract_value`, `wieb`;
- inflow method: `use_independent_inflow_curve`, `inflow_curve_type`, `inflow_curve_skew`;
- relationship: `activities`.

New scenarios use Independent inflow defaults; legacy rows can retain null values in the independent-inflow columns and therefore remain activity-linked.

### `Activity`

An Activity belongs to one Cashflow. Its foreign-key column remains physically named `project_id`; the current model exposes `cashflow_id` and retains a `project_id` synonym for compatibility.

Important groups of fields include:

- execution: cost, duration, start, activity type/skew, pre-work period;
- subcontract share;
- subcontract advance/retention/payment/DLP/WIEB/no-billing assumptions;
- cached `cash_flow_json` for activity work/outflow compatibility.

Project snapshots are recalculated from current non-deleted activities rather than trusting old cached project results.

## 6. Calculation engine

`q_flow/cashflow.py` contains the current calculation engine.

Important classes are:

- `Work` — generates linear or S-curve marginal work and corrects the curve to preserve total value;
- `Activity_cf` — calculates activity work and activity outflow;
- `CashflowCalculator` — combines active activities, selects the contract-value inflow method, calculates project inflow/outflow/net cash, and applies financing to negative cumulative balances.

`Project_cf` remains as a compatibility alias for `CashflowCalculator`.

The backend is authoritative for calculation logic. The canonical formula reference is [`reference/cashflow_model.md`](reference/cashflow_model.md).

### Current snapshot keys

The API snapshot currently exposes legacy/current keys including:

```text
workflow
inflow
outflow
netflow
outflow_with_interest
duration
summary
```

Important semantic notes:

- `workflow` is the combined cost-loaded activity work series;
- `outflow_with_interest` is the cumulative cash balance after financing, despite the legacy name;
- `duration` is the active activity-derived execution duration;
- the `summary` object includes totals such as direct cost, subcontracted/self-performed cost, financing cost, final cash balance, work duration, and financial horizon.

Clients should prefer semantic labels in the UI instead of exposing these backend key names.

## 7. Validation and transactions

Cashflow and Activity mutation routes validate model inputs before committing.

The backend enforces rules including:

- finite numeric values;
- valid percentage/fraction ranges;
- non-negative integer timing values;
- positive activity cost and duration;
- `advance + retention <= 1`;
- valid inflow curve type;
- skew strictly inside `(-1, 1)`.

Mutations that recalculate snapshots are committed transactionally. If validation or calculation fails, the mutation is rolled back.

The Flutter client mirrors key validation rules to give immediate feedback, but backend validation remains authoritative.

## 8. Portable scenario JSON

CashflowPot can export/import a versioned portable input model using:

```text
format = cashflowpot.cashflow
version = 1
```

The file contains scenario inputs and activities, not server identity or calculated arrays.

The Flutter client validates the file before import confirmation. The backend validates the scenario and every activity again, calculates the resulting snapshot, and commits the imported scenario transactionally.

The exact format is defined in [`reference/cashflow_json_format.md`](reference/cashflow_json_format.md).

## 9. Authentication and authorization

Protected q_flow routes expect:

```http
Authorization: Bearer <QAuth user token>
```

q_flow verifies the user JWT locally using the configured QAuth public key/algorithm and application audience. Calls from q_flow to QAuth carry a short-lived application JWT in the `client-app-id` header.

Project access is then enforced using QAuth Unit context and Unit permissions.

Token refresh and the exact current security flow are documented in [`reference/security.md`](reference/security.md).

## 10. Public website and discovery metadata

The public website source is under:

```text
site/templates/
site/static/
site/build_site.py
```

`build_site.py` renders the reviewed page set into `site/dist/` and, in normal production mode, publishes only the site-owned entries into the production web root.

The builder maintains an authoritative public-page registry containing each page's output destination, canonical path, indexing status, title/description metadata, and schema type. That registry drives sitemap membership and supplies the shared Jinja shell with canonical/search/social metadata.

The shared public head provides:

- canonical URLs and robots directives;
- Open Graph and Twitter metadata;
- the shared social image `https://cashflowpot.com/assets/images/cashflowpot-og.webp`;
- homepage JSON-LD for the Quollnet Organization, CashflowPot WebSite, and current SoftwareApplication;
- lightweight page-level JSON-LD plus breadcrumb data on internal public pages.

`build_site.py` also generates root `robots.txt`, `sitemap.xml`, and `llms.txt`. The public website is the authoritative indexable discovery surface. The Flutter `/app/` shell remains crawlable but non-indexable so its `noindex, follow` directive can be read, while `/api/` is not a discovery surface and is disallowed through the public robots policy.

The site and Flutter app intentionally share some `/app/icons/...` assets on the production domain. A simple local `site/dist` preview therefore cannot display those app-owned icons unless the Flutter app is also served at `/app/`.

## 11. Tests

Backend tests live under `tests/` and cover calculations, validation, QAuth integration boundaries, project/cash-flow routes, portable import, the public-site builder, and documentation structure.

For a backend change, the final local verification command is normally:

```bash
pytest
```

Flutter tests are maintained in the `iqmia/cashflowpot` repository and should also be run when a change affects client behavior or shared input/output contracts.

## 12. Compatibility debt to recognize

Some current names exist for historical compatibility and should not be treated as ideal semantic names:

- database table `project` stores `Cashflow` scenarios;
- Activity DB foreign key `project_id` maps to `cashflow_id`;
- API `workflow` is cost-loaded activity work;
- API `outflow_with_interest` is cumulative financed cash balance;
- `Activity.mobilization_period` currently acts as a pre-work/no-work period;
- several deprecated/unused Activity fields remain in the schema.

Do not rename these casually without a migration/compatibility plan. User-facing language should remain clear even while legacy backend names exist.

Last reviewed: 7 October 2026.
