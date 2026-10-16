# CashflowPot technical architecture

## 1. Repository roles

CashflowPot currently spans three relevant repositories:

- `iqmia/q_flow` — Flask backend, authoritative calculation engine, QAuth Unit integration, portable JSON import/export, financing-facility engine and atomic facility APIs, backend Excel report generation, tests, and the source/build system for the public CashflowPot website.
- `iqmia/cashflowpot` — Flutter client deployed under `/app/`; owns user input/presentation, charts, portable JSON UX, and the existing client-side Excel/report UX.
- `iqmia/quollnet-mcp` — MCP gateway. Its dedicated `/cashflowpot` resource translates AI-facing tools into normal QAuth token exchange plus q_flow API calls. It does not duplicate CashflowPot persistence or financial calculations.

The public website source lives in `q_flow/site/` and is rendered to static HTML. It is not a Flask-rendered website at request time.

The backend/package name remains `q_flow` even though the product name is CashflowPot.

## 2. Production surfaces

The CashflowPot domain exposes:

```text
cashflowpot.com/      static public website
cashflowpot.com/app/  Flutter application
cashflowpot.com/api/  Flask API through Apache + Gunicorn
```

The MCP gateway is deployed separately at:

```text
mcp.quollnet.com/mcp          existing Quollnet MCP
mcp.quollnet.com/cashflowpot  dedicated CashflowPot MCP
```

Apache exposes CashflowPot `/api/` and reverse-proxies to Gunicorn on `127.0.0.1:5002`. The Flask application itself defines routes without an `/api` prefix.

The q_flow Gunicorn process is managed by the CashflowPot systemd service with `/home/cashflowpot/q_flow` as the working directory and `wsgi:app` as the application entrypoint.

See [`deployment.md`](deployment.md) for the exact server layout and commands.

## 3. Flask application and persistence

`q_flow.create_app()` initializes the core extensions and registers the current blueprints:

- `projects` — project / QAuth Unit operations;
- `cashflows` — cash-flow scenario operations, portable scenario import/export, and atomic financing-facility operations;
- `activities` — Activity CRUD and Activity cash-flow updates;
- `exports` — signed Excel export-link creation and stateless workbook streaming;
- `users` — QAuth-facing user flows;
- `system` — system/health routes.

The application uses SQLAlchemy. Production uses PostgreSQL from the configured `DATABASE_URL` and psycopg driver. The current production storage directory is:

```text
/home/cashflowpot/q_flow/main_storage
```

When `DATABASE_URL` is absent, the application can fall back to SQLite at `<STORAGE_PATH>/q_flow.db`, which remains useful for local/test-compatible operation. Tests use their own test configuration and storage.

Generated Excel reports are not persisted in `main_storage` or elsewhere. They are built in memory and streamed directly.

## 4. Project identity and QAuth

A CashflowPot **project** is represented externally by a QAuth Unit.

QAuth owns the project/unit identity and access context such as:

- Unit id;
- name;
- description;
- image/color;
- roles; and
- unit permissions.

The local q_flow database owns cash-flow scenarios and Activities. Each scenario stores the QAuth `unit_id` that it belongs to.

Current permissions used by q_flow are:

```text
view:cashflow
edit:cashflow
```

Creating a new project creates a QAuth Unit and then creates a local `Base Cashflow` scenario for that Unit. A QAuth Unit can own multiple local cash-flow scenarios.

For MCP access, the connected OAuth token belongs to the QAuth MCP resource. The MCP server exchanges it through QAuth for the same normal CashflowPot app or Unit token that q_flow already understands. q_flow therefore keeps the same authorization boundary for Flutter and MCP callers.

## 5. Main local models

### `Cashflow`

`q_flow.models.cashflow.Cashflow` represents one independent financial scenario.

For compatibility, its physical database table remains named `project`.

Important groups of fields include:

- identity: `id`, `unit_id`, `name`, `description`;
- client terms: `advance`, `retention`, `release_retention_eop`, `dlp`, `duration_for_payment`;
- finance/value: `interest_rate`, `contract_value`, `wieb`;
- inflow method: `use_independent_inflow_curve`, `inflow_curve_type`, `inflow_curve_skew`;
- financing facilities: `financing_facilities` JSON definitions;
- relationship: `activities`.

Financing facilities deliberately remain embedded in the Cashflow aggregate. That is what allows one portable JSON scenario to contain its commercial assumptions, Activities, inflow model, and financing setup in a single shareable document.

New scenarios use Independent inflow defaults; legacy rows can retain null values in the independent-inflow columns and therefore remain activity-linked.

### `Activity`

An Activity belongs to one Cashflow. Its foreign-key column remains physically named `project_id`; the current model exposes `cashflow_id` and retains a `project_id` synonym for compatibility.

Current source/calculation fields include:

- category/template: `activity_type`;
- calculation mode: `activity_mode` (`work`, `scheduled_cost`);
- Work distribution: `distribution_type` (`s_curve`, `linear`, `manual`);
- dense manual/scheduled source: `cost_schedule_json`;
- cost/timing: `cost`, `duration`, `duration_units`, `start`, `mobilization_period`;
- Work subcontract assumptions: `subcontracted`, `advance`, `retention`, `release_retention_eop`, `dlp`, `duration_for_payment`, `work_in_excess`, `no_billing_period`;
- generated S-curve input: `skew`;
- calculated/cache compatibility output: `cash_flow_json`.

`activity_type` no longer controls calculation after save. It is a category/template only.

Legacy rows can keep null `activity_mode`/`distribution_type`; helper functions provide runtime compatibility:

```text
missing activity_mode -> work
missing distribution_type + legacy activity_type == "linear" -> linear
otherwise missing distribution_type -> s_curve
scheduled_cost -> effective manual distribution
```

Manual Work and Scheduled Cost derive their authoritative `cost` and `duration` from `cost_schedule_json`.

### Removed/legacy Activity fields

Several historical fields can remain physically in upgraded databases but are not active source inputs in the current ORM/client model:

- mobilization percentage;
- profit;
- subcontractors_retention;
- Activity-level interest rate;
- compounding period.

`mobilization_period` remains active but semantically means **pre-work/no-work period**.

## 6. Calculation engine

`q_flow/cashflow.py` contains the project/Activity calculation engine.

Important classes/functions are:

- `Work` — generates Linear or S-curve marginal work and corrects the curve so total value returns to the specified cost/value;
- `Activity_cf` — calculates Activity work and Activity outflow according to Work vs Scheduled Cost semantics;
- `CashflowCalculator` — combines active Activities, selects the contract-value inflow method, calculates project inflow/outflow/net cash, and applies legacy or explicit financing;
- `calculate_financing` in `q_flow/financing.py` — applies optional facility definitions period-by-period and returns facility draw, repayment, interest, fees, outstanding, funded balance, capacity, and shortfall series.

`Project_cf` remains as a compatibility alias for `CashflowCalculator`.

The backend is authoritative for calculation logic. Neither Flutter reporting nor MCP tools are second financial engines. The canonical formula reference is [`reference/cashflow_model.md`](reference/cashflow_model.md).

## 7. Work vs Scheduled Cost calculation

### Work

Work Activities contribute to:

- `workflow` / cost-loaded execution;
- project Work duration;
- project outflow; and
- the denominator/profile used by Activity-linked client inflow.

Generated Work uses `cost` + `duration` + distribution settings. Manual Work uses `cost_schedule_json` as its base marginal work schedule, after which the normal pre-work and subcontract-payment pipeline applies.

### Scheduled Cost

Scheduled Cost calculates:

```text
marginal_work     = zeros(schedule length)
marginal_out_flow = cost_schedule_json
```

It contributes to project cost/outflow, net cash, financing need, and financial horizon, but is excluded from:

- project `workflow` aggregation;
- Work duration;
- Independent inflow duration; and
- Activity-linked contract-value allocation.

Work subcontract terms are ignored for Scheduled Cost.

## 8. Duration model

CashflowPot deliberately separates **Work duration** from **financial horizon**.

### Work duration

`CashflowCalculator.duration` is the maximum Work Activity calculated work-series length. Scheduled Cost does not extend this value.

### Financial horizon

The returned snapshot can extend past Work duration because of:

- Scheduled Cost;
- client/subcontract payment delays;
- WIEB carry;
- retention and DLP releases;
- facility availability/draw schedules;
- facility repayment schedules;
- interest/fees; and
- other financing flows.

The summary exposes:

```text
work_duration
financial_horizon
```

as separate values.

## 9. Client inflow and PPC series

`CashflowCalculator.contract_work()` first chooses Independent or Activity-linked contract-value work.

`inflow()` then applies client advance, WIEB, payment delay, retention, and DLP to produce **cash receipts**.

Two supporting PPC series are used by financing:

- `ppc_issued()` — net certificate values in certificate periods, before client payment delay;
- `ppc_base()` — client PPC receipts excluding advance and retention releases.

PPC Discount draw logic uses `ppc_issued`; PPC-linked repayment uses `ppc_base`.

## 10. Financing engine and atomic facility API

Facility definitions are plain dictionaries validated by `validate_financing_facilities()` and calculated by `calculate_financing()`.

Current draw methods:

```text
automatic_shortfall
scheduled
ppc_base
```

Current repayment methods:

```text
cashflow_sweep
percent_of_ppc
equal_installments
scheduled
```

Capacity semantics:

```text
revolving     -> limit - current outstanding
non-revolving -> limit - cumulative actual draws
blank limit   -> unlimited
```

Scheduled draw schedules represent requested financing inflows. Actual draw is capped by available capacity; the unavailable portion is not a project cost and is not carried forward.

Facility interest uses opening principal. One-time fees are charged at the configured availability start period. Automatic repayment of a scheduled draw through `% PPC` or cashflow sweep is capped to opening-period principal so a new scheduled draw cannot be automatically repaid in the same period.

Facilities are stored inside `cashflow.financing_facilities`, but q_flow exposes atomic list/get/add/update/delete/order operations. These routes normalize stable facility IDs and validate/recalculate the complete scenario transactionally. An MCP or other client therefore does not need to fetch and rewrite the full array for a one-facility edit.

Detailed facility behavior is documented in [`reference/financing_facilities.md`](reference/financing_facilities.md).

## 11. Snapshot keys

Core calculated snapshot keys include:

```text
workflow
inflow
outflow
netflow
outflow_with_interest
duration
```

When financing facilities are configured, the snapshot also includes facility draw/repayment/interest/fee rows, pre-financing balance, funded cash position, and unfunded shortfall arrays.

Important semantic notes:

- `workflow` is the combined **Work Activity** cost-loaded execution series;
- `inflow` is client/project cash receipts;
- `outflow` is project cost/payments from all Activities;
- `netflow` is project inflow minus project outflow before explicit facilities;
- facility draws are actual financing inflows;
- facility repayment is principal only;
- `outflow_with_interest` is the funded closing cash balance despite the legacy name;
- `duration` is Work duration, not financial horizon.

Clients should prefer semantic labels in the UI instead of exposing these backend key names.

## 12. Facility row shape

Each entry in `facility_rows` currently includes:

```text
id
name
type
draw_method
repayment_method
draw[]
repayment[]
interest[]
fees[]
outstanding[]
available_limit[]
```

The report presentation combines `interest[] + fees[]` into one **Interest & fees** row while keeping the source arrays separate for calculation/KPI detail.

## 13. Summary / KPI fields

`Cashflow.as_dict_with_activities()` computes canonical scenario summary fields from authoritative model values.

Current summary fields include:

```text
total_inflow
work_cost
scheduled_cost
subcontracted_cost
self_performed_cost
direct_cost
financing_cost
total_cost
total_facility_interest
total_facility_fees
minimum_pre_financing_balance
minimum_pre_financing_period
peak_pre_financing_need
peak_pre_financing_period
peak_facility_outstanding
final_facility_outstanding
final_cash_balance
cash_after_debt_settlement
work_duration
dlp
financial_horizon
```

When facilities are present, the summary can also include:

```text
contractor_contribution
peak_unfunded_shortfall
```

Definitions used by the UI:

```text
Project cost = direct_cost = Work cost + Scheduled Cost
Financing cost = total facility interest + total facility fees
Total cost = direct_cost + financing_cost
Cash after debt settlement = final cash balance - final facility outstanding
```

Peak Funding Requirement is derived from the most negative pre-financing balance and displayed as zero if the pre-financing balance never becomes negative.

The UI displays summary periods as 1-based even though backend period indexes are zero-based.

## 14. Calculation precision vs presentation precision

The backend source model and summary values are authoritative.

Period arrays are rounded for serialized/display compatibility. A client/report must not derive canonical totals by summing rounded period labels when a source total is available.

Examples:

- Activity row total should use Activity `cost` rather than summing displayed period values;
- Project cost should use canonical Activity/summary totals;
- Project inflow total should use the backend summary rather than summing visibly rounded receipt cells where that would introduce drift.

Excel keeps actual numeric cells/formulas; display formatting is separate from the underlying value.

## 15. Validation and transactions

Cashflow, Activity, and facility mutation routes validate model inputs before committing.

The backend enforces rules including:

- finite numeric values;
- valid percentage/fraction ranges;
- valid non-negative integer timing values;
- generated Work cost and duration > 0;
- non-empty finite non-negative schedules with total > 0 for Manual Work/Scheduled Cost;
- `advance + retention <= 1`;
- valid Activity mode/distribution;
- valid inflow curve type;
- skew strictly inside `(-1, 1)`;
- valid facility definitions and method-specific inputs.

Mutations that recalculate snapshots are committed transactionally. If validation or calculation fails, the mutation is rolled back.

The Flutter client mirrors key validation rules to give immediate feedback, but backend validation remains authoritative.

## 16. Portable scenario JSON

CashflowPot exports/imports a versioned portable input model using:

```text
format = cashflowpot.cashflow
version = 1
```

The file contains scenario source inputs, embedded facilities, and Activity source inputs. It deliberately excludes server identity, ownership, calculated arrays, and Activity calculation caches.

The backend is now the canonical serializer as well as the canonical importer. MCP export returns the q_flow-generated document rather than reconstructing it from a calculated snapshot.

Version 1 remains backward compatible with old Activity files that do not include `activity_mode`, `distribution_type`, or `cost_schedule_json`. Legacy facilities that lack an ID are normalized with stable IDs when they are addressed through the facility API; no bulk data migration is required.

The Flutter client can validate a file before import confirmation. The backend validates the scenario and every Activity again, normalizes mode/distribution semantics, derives schedule-based cost/duration, calculates the resulting snapshot, and commits the imported scenario transactionally.

The exact format is defined in [`reference/cashflow_json_format.md`](reference/cashflow_json_format.md).

## 17. Excel/report architecture

The approved CashflowPot workbook design originated in the Flutter exporter and remains the report-layout reference, including sheet structure, styles, chart/KPI structure, column geometry, formulas, and A4/A3 print/PDF setup.

q_flow now also generates that report in Python with `XlsxWriter`, using authoritative backend scenario values. Targeted OOXML post-processing can be used only where XlsxWriter cannot reproduce an approved workbook detail directly.

The report is still a presentation layer, not a second financial engine. The lower structure is:

```text
PROJECT CASHFLOW
FACILITIES
CASH POSITION
RECONCILIATION & NOTES
```

The exporter uses backend-calculated facility series for Draw, Repayment, Interest & fees, and Outstanding balance. Workbook formulas are used for reporting reconciliation/aggregation where appropriate, but the exporter does not reimplement facility banking rules.

The workbook retains numeric cells, one-decimal cashflow display formatting, approved A4-landscape/A3 print geometry, existing column widths, and the current chart/KPI structure.

### Stateless Excel delivery

The authenticated creation route is:

```text
POST /cashflow/<cashflow_id>/excel-export
```

It requires normal CashflowPot authentication and `VIEW_CASHFLOW`, then returns:

```text
filename
download_url
expires_at
```

The public download route is:

```text
GET /exports/cashflow/<signed-token>.xlsx
```

The signed token binds the download to the cashflow, exact project/unit, project name, export purpose, and expiry. The route verifies the token, loads the **current** authoritative scenario, generates the workbook in memory, and streams it. No Excel file is retained on disk and no cleanup job is needed.

`PUBLIC_API_BASE_URL` supplies the externally visible `/api` base because Apache strips that prefix before Flask sees requests. `EXCEL_EXPORT_TOKEN_TTL_SECONDS` defaults to 600 seconds.

## 18. MCP integration

The dedicated CashflowPot MCP is an adapter, not part of the financial engine:

```text
AI client
  -> OAuth/PKCE with QAuth
  -> MCP access token aud=https://mcp.quollnet.com/cashflowpot
  -> quollnet-mcp /cashflowpot
  -> QAuth exchange to normal CashflowPot app/Unit token
  -> cashflowpot.com/api (q_flow)
```

The dedicated MCP exposes projects, cashflows/results, activities, facility convenience operations, portable JSON import/export, and Excel export. q_flow remains authoritative for every operation underneath.

Excel is returned to MCP as signed URL metadata only. The MCP server does not fetch, proxy, base64-encode, or store the workbook.

## 19. Authentication and authorization

Protected q_flow routes expect:

```http
Authorization: Bearer <QAuth user or Unit token>
```

q_flow verifies the user JWT locally using the configured QAuth public key/algorithm and application audience. Calls from q_flow to QAuth carry a short-lived application JWT in the `client-app-id` header.

Project access is then enforced using QAuth Unit context and Unit permissions.

The stateless Excel GET route is the intentional exception: possession of the unexpired signed URL authorizes that specific export download. Its claims are validated before any cashflow is loaded or report generated.

Token refresh and the exact current security flow are documented in [`reference/security.md`](reference/security.md).

## 20. Public website and discovery metadata

The public website source is under:

```text
site/templates/
site/static/
site/build_site.py
```

`build_site.py` renders the reviewed page set into `site/dist/` and, in normal production mode, publishes only the site-owned entries into `/home/cashflowpot/public_html`.

The builder maintains an authoritative `PublicPage` registry containing each page's output destination, canonical path, indexing status, title/description metadata, and schema type. That registry drives sitemap membership and supplies the shared Jinja shell with canonical/search/social metadata.

The shared public head provides canonical/robots metadata, Open Graph and Twitter metadata, JSON-LD, breadcrumbs, and the shared social image.

`build_site.py` also generates root `robots.txt`, `sitemap.xml`, and `llms.txt`. The public website is the authoritative indexable discovery surface. The Flutter `/app/` shell remains crawlable but non-indexable, while `/api/` is disallowed through the public robots policy. The application shell and API are not a discovery surface for indexable public product content.

## 21. Tests

Backend tests live under `tests/` and cover calculations, Activity modes, Scheduled Cost, financing facilities, validation, QAuth integration boundaries, project/cash-flow routes, portable import/export, backend Excel generation, signed download tokens/no-storage behavior, public-site builder, and documentation structure.

For a backend change, the final local verification command is normally:

```bash
pytest
```

Flutter tests are maintained in `iqmia/cashflowpot` and cover input/presentation/export contracts. Run them when a change affects client behavior or shared input/output contracts.

The dedicated MCP tests live in `iqmia/quollnet-mcp` and verify audience isolation, `/mcp` compatibility, full `/cashflowpot` tool registration, token exchange, route mapping, source-field forwarding, atomic facility operations, and signed Excel metadata forwarding.

## 22. Compatibility debt to recognize

Some current names exist for historical compatibility and should not be treated as ideal semantic names:

- database table `project` stores `Cashflow` scenarios;
- Activity DB foreign key `project_id` maps to `cashflow_id`;
- API `workflow` is Work-only cost-loaded execution;
- API `outflow_with_interest` is cumulative financed cash balance;
- `Activity.mobilization_period` acts as a pre-work/no-work period;
- legacy Activity columns can remain physically present after schema upgrades;
- backend Activity `start` is a zero-based offset while user-facing periods are 1-based.

Do not rename these casually without a migration/compatibility plan. User-facing language should remain clear even while legacy backend names exist.

Last reviewed: 17 October 2026.
