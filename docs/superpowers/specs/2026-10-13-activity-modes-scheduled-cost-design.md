# CashflowPot Activity Modes and Scheduled Cost Design

## Purpose

Extend CashflowPot activities so project cost timing can be represented in three ways without changing downstream cash-flow semantics:

1. generated S-curve work;
2. generated linear work;
3. manually scheduled work; and
4. scheduled cost that affects project cost/outflow but is not physical work.

The design keeps project execution/cost modelling separate from financing. Facilities continue to fund the resulting project cashflow; a future LC-to-purchase link may use scheduled-cost activities as eligible costs, but facility linking is not part of this implementation.

## Current problem

The current `Activity.activity_type` has two responsibilities:

- it is a creation template/category such as General, Structure, MEP, Facade, etc.; and
- the exact value `"linear"` is also used by `Activity_cf` as the work-distribution switch.

This coupling makes it impossible to represent an MEP activity that is linear while preserving MEP as its category/template.

The current Activity model also contains legacy fields that no longer participate in calculation: `mobilization`, `profit`, `subcontractors_retention`, activity-level `interest_rate`, and `compounding_period`.

## Agreed model

Add three source fields to Activity:

```text
activity_mode
    work
    scheduled_cost

distribution_type
    s_curve
    linear
    manual

cost_schedule_json
    JSON list of marginal cost/work values
```

`activity_type` remains a template/category only. It must not control the calculation after the activity values have been saved.

### Defaults and legacy compatibility

New activities default to:

```text
activity_mode = work
distribution_type = s_curve
cost_schedule_json = null
```

Existing rows must continue to calculate without a destructive data migration:

- null/missing `activity_mode` is treated as `work`;
- null/missing `distribution_type` is inferred as `linear` only when legacy `activity_type` is exactly `linear` case-insensitively; otherwise it is treated as `s_curve`;
- null/missing `cost_schedule_json` is valid for generated S-curve/linear work.

The schema migration adds the new columns. It does not rewrite existing activity rows.

## Schedule semantics

`cost_schedule_json` is a dense list of marginal values, not a calculated cashflow object. Example:

```json
[200, 0, 500, 0, 200]
```

For `activity_mode = work` and `distribution_type = manual`, the list replaces the generated marginal work curve. The existing activity pipeline then remains unchanged: pre-work period, subcontracted share, no-billing period, WIEB, advance recovery, retention, payment delay and DLP are applied exactly as they are for generated work.

The activity `start` offset remains separate and is applied after the local schedule is calculated, exactly as it is for generated curves.

For any activity using `cost_schedule_json`, `cost` is derived from `sum(cost_schedule_json)` and is server-authoritative. `duration` is derived from the schedule length for manual work/scheduled-cost activities so stale cost/duration inputs cannot conflict with the schedule.

## Work activity behavior

For `activity_mode = work`:

### S-curve

```text
distribution_type = s_curve
marginal_work = generated S-curve using cost, duration, skew
```

### Linear

```text
distribution_type = linear
marginal_work = generated linear curve using cost and duration
```

### Manual

```text
distribution_type = manual
marginal_work = cost_schedule_json
cost = sum(cost_schedule_json)
duration = len(cost_schedule_json)
```

After the base marginal-work series is obtained, the existing Activity payment/outflow calculation is used unchanged.

## Scheduled-cost behavior

For `activity_mode = scheduled_cost`:

```text
marginal_work = zero series
marginal_out_flow = cost_schedule_json
cost = sum(cost_schedule_json)
duration = len(cost_schedule_json)
```

`start` shifts the scheduled outflow into project time.

Scheduled-cost activities do not use subcontract assumptions, advance, retention, WIEB, no-billing period, payment delay or DLP. They represent direct scheduled project cost/outflow.

A scheduled-cost activity therefore:

- increases project direct cost;
- increases project outflow according to its schedule;
- affects net cash and financing need;
- does not create physical work;
- does not create billed/client work;
- does not extend project work duration.

## Common calculated output

`cash_flow_json` remains calculated/server-owned output and keeps the same shape for every activity source:

```json
{
  "marginal_work": [...],
  "marginal_out_flow": [...]
}
```

Generated S-curve, generated linear, manual work and scheduled-cost activities all produce this same output contract.

`cost_schedule_json` is source input; `cash_flow_json` is calculated output/cache. Clients may send the former but not the latter as authoritative source data.

## Project calculation changes

The calculator must keep separate collections for work and outflow:

```text
work_cf     = work activities only
outflow_cf  = all activities
```

Project `workflow`, activity-linked contract work and work duration are calculated from `activity_mode = work` only.

Project outflow is calculated from every activity.

### Activity-linked inflow

When main-contract inflow follows activities, scheduled-cost activities are excluded entirely from the value-factor denominator and billed-work profile.

Let:

```text
C_work = sum(cost of work activities)
V      = contract value
value_factor = V / C_work
```

Then:

```text
contract_value_work_t = project_work_t * value_factor
```

Scheduled costs therefore remain project cost/outflow but do not create client PPC value.

### Independent inflow

Independent inflow remains independent of activity cost shape. Its duration is derived from work activities only. A scheduled purchase after the work ends must not extend the independent contract curve.

The overall financial horizon may still extend beyond work duration because outflows, facilities, payment delays and DLP can occur later.

## Validation

Backend validation is authoritative.

Valid activity modes:

```text
work
scheduled_cost
```

Valid work distributions:

```text
s_curve
linear
manual
```

Rules:

- `work + s_curve`: `cost > 0`, `duration > 0`, valid skew; schedule may be null/empty.
- `work + linear`: `cost > 0`, `duration > 0`; schedule may be null/empty.
- `work + manual`: non-empty valid `cost_schedule_json` required; schedule total must be finite and > 0.
- `scheduled_cost`: non-empty valid `cost_schedule_json` required; schedule total must be finite and > 0.
- schedule elements must be finite and non-negative.
- manual/scheduled-cost `cost` and `duration` are normalized from the schedule before final validation/calculation.

`distribution_type` is ignored for calculation when `activity_mode = scheduled_cost`; the persisted/default value may remain `manual` for consistency in the API/UI.

## Legacy field cleanup

Remove these fields from the active Activity ORM/API/Flutter model because they no longer participate in the calculation:

- `mobilization` percentage;
- `profit`;
- `subcontractors_retention` / Flutter `subcontractorRetention`;
- activity-level `interest_rate`;
- `compounding_period`.

Existing database installations may retain the old physical columns. The migration does not need a destructive table rebuild merely to drop them. New ORM/schema creation no longer defines them, and import/export/API clients stop exposing them.

Keep `mobilization_period` for this change because it is active calculation input representing the pre-work/no-work period. The UI may continue to call it `Pre-work period`.

Keep `duration_units` for compatibility in this implementation; moving period units to scenario level is separate cleanup.

## Activity type/template cleanup

`ActivityType.LINEAR` is not a real activity category and must no longer be used as the calculation switch.

The static activity-type catalogue remains a creation-time helper that supplies defaults such as skew/subcontract assumptions. Selecting a template populates fields; the saved calculation is determined by `activity_mode`, `distribution_type` and the persisted activity assumptions.

Legacy `activity_type = linear` rows remain accepted through the compatibility inference described above.

## Import/export

Portable `cashflowpot.cashflow` JSON must continue to accept existing version-1 files.

Activity export/import adds:

```text
activity_mode
distribution_type
cost_schedule_json
```

Older files without these keys import as legacy work activities using the compatibility rules.

Calculated `cash_flow_json` remains excluded from portable source JSON.

The removed legacy Activity fields remain excluded from portable JSON.

## Flutter behavior

The Flutter Activity model mirrors the new source fields and removes the dead legacy fields.

Activity form behavior:

- activity template/category remains available when creating an activity;
- mode selector: `Work` / `Scheduled cost`;
- Work mode exposes distribution: `S-curve` / `Linear` / `Manual`;
- S-curve keeps the work-timing/skew control;
- Linear hides skew control;
- Manual shows a schedule editor and treats cost/duration as calculated from the schedule;
- Scheduled cost shows the schedule editor, treats cost/duration as calculated, and hides work distribution and subcontract assumptions;
- start period remains available;
- pre-work period remains relevant only for Work mode.

The UI schedule editor uses user-facing period numbers, but serializes a dense local list so the backend has no ambiguous period-key numbering.

## Tests / acceptance criteria

Backend tests must prove:

1. existing S-curve activities are unchanged;
2. existing legacy `activity_type = linear` activities remain linear when new fields are absent;
3. new linear activities can keep a real category such as MEP;
4. manual work schedule exactly replaces generated marginal work before existing payment logic;
5. manual schedule total overrides submitted cost and schedule length overrides submitted duration;
6. empty manual schedule is rejected;
7. scheduled-cost activity uses the schedule directly as outflow and produces zero work;
8. empty scheduled-cost schedule is rejected;
9. scheduled-cost activity contributes to project direct cost/outflow but not workflow;
10. activity-linked inflow factors only work activities to the full contract value;
11. independent inflow duration ignores late scheduled-cost activities;
12. portable JSON round-trips new fields and still imports old version-1 files;
13. existing financing calculations continue to consume the resulting project inflow/outflow without special facility changes.

Flutter tests must cover model JSON round-trip and Activity form mode/distribution visibility/validation. The user will run the Flutter suite locally.

## Out of scope

This change does not implement:

- LC linking to scheduled-cost/purchase activities;
- financing-purpose restrictions;
- materials-on-site/off-site billable-value treatment;
- project-level period-unit refactor;
- residual facility maturity/balloon rules;
- the financing issues identified during facility testing.

Those remain follow-up work after the Activity model foundation is complete.
