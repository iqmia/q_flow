# CashflowPot portable cash-flow JSON

This document defines the portable JSON format used to export and import a CashflowPot cash-flow scenario.

The portable file is an **input model**, not a serialized API response. It is intended for backup/transfer and is also the natural structured target for future AI-assisted scenario generation.

## 1. Version marker

```json
{
  "format": "cashflowpot.cashflow",
  "version": 1,
  "cashflow": {}
}
```

Current format:

```text
format  = cashflowpot.cashflow
version = 1
```

Importers reject an unknown format or unsupported version rather than guessing semantics.

## 2. Percentage and timing conventions

Percentage-like values are stored as API fractions:

```text
0.10 = 10%
0.50 = 50%
1.00 = 100%
```

Timing values are integer model **periods**. The portable format does not assume that a period must be a calendar month.

Important validation rules include:

- project/client `advance + retention <= 1.0`;
- Work Activity/subcontract `advance + retention <= 1.0`;
- Activity `skew` strictly inside `(-1, 1)`;
- non-null `inflow_curve_skew` strictly inside `(-1, 1)`;
- generated Work Activity cost > 0 and duration > 0;
- Manual Work and Scheduled Cost require a non-empty `cost_schedule_json` with finite non-negative values and a total > 0;
- payment period, DLP, start, pre-work, and no-billing period are non-negative integers.

## 3. Cash-flow object

Example:

```json
{
  "name": "Tender scenario",
  "description": "Baseline tender cash-flow forecast",
  "contract_value": 1250000,
  "advance": 0.10,
  "retention": 0.10,
  "release_retention_eop": 0.50,
  "dlp": 12,
  "duration_for_payment": 1,
  "interest_rate": 0.005,
  "wieb": 0.20,
  "use_independent_inflow_curve": true,
  "inflow_curve_type": "s_curve",
  "inflow_curve_skew": 0.0,
  "financing_facilities": [],
  "activities": []
}
```

Current accepted scenario input fields are:

```text
name
description
advance
retention
release_retention_eop
dlp
duration_for_payment
interest_rate
contract_value
wieb
use_independent_inflow_curve
inflow_curve_type
inflow_curve_skew
financing_facilities
activities
```

`financing_facilities` is optional for older version-1 files. Scheduled facility draws and repayments continue to use the facility period-to-amount map representation. Activity schedules use the separate dense-list representation documented below.

`name` must be non-empty text. `description`, when present, must be text.

## 4. Inflow forecast settings

The Independent contract curve is selected only when:

```text
use_independent_inflow_curve is true
and
inflow_curve_type is not null
```

Otherwise the backend uses Activity-linked inflow.

`inflow_curve_type` accepts:

```text
s_curve
linear
```

A null `inflow_curve_skew` is interpreted as balanced `0.0`. It does not disable Independent inflow. Skew is retained but has no calculation effect for a Linear curve.

The three Independent-inflow fields are optional for Version 1 compatibility. When omitted for a newly imported scenario, current scalar defaults are applied.

## 5. Work in Excess of Billings (WIEB)

`wieb` is the project-level Work in Excess of Billings forecasting assumption. It represents the estimated share of completed contract-value work that is not billed in the current period and is carried into the following billing period.

Activity `work_in_excess` is the equivalent subcontract-side timing assumption for Work Activities. Scheduled Cost does not use WIEB.

WIEB changes timing, not lifetime value.

## 6. Activity object

Activities separate **category/template**, **calculation mode**, and **work distribution**.

### 6.1 Generated Work Activity

```json
{
  "name": "Concrete works",
  "activity_type": "concrete",
  "activity_mode": "work",
  "distribution_type": "s_curve",
  "cost_schedule_json": null,
  "cost": 400000,
  "duration": 4,
  "duration_units": "Periods",
  "start": 0,
  "advance": 0.10,
  "retention": 0.10,
  "release_retention_eop": 0.50,
  "dlp": 6,
  "duration_for_payment": 1,
  "work_in_excess": 0.10,
  "mobilization_period": 0,
  "subcontracted": 0.50,
  "skew": -0.50,
  "no_billing_period": 0
}
```

`activity_type` is a template/category only. It no longer selects the calculation method.

`activity_mode` accepts:

```text
work
scheduled_cost
```

For `activity_mode = work`, `distribution_type` accepts:

```text
s_curve
linear
manual
```

Generated `s_curve` and `linear` Work Activities use `cost` and `duration` and do not require a schedule.

### 6.2 Manual Work Activity

```json
{
  "name": "Manual MEP work",
  "activity_type": "mep",
  "activity_mode": "work",
  "distribution_type": "manual",
  "cost_schedule_json": [200, 0, 500, 300],
  "start": 1,
  "advance": 0.10,
  "retention": 0.10,
  "release_retention_eop": 0.50,
  "dlp": 6,
  "duration_for_payment": 1,
  "work_in_excess": 0.10,
  "mobilization_period": 0,
  "subcontracted": 0.50,
  "skew": 0,
  "no_billing_period": 0
}
```

`cost_schedule_json` is a **dense activity-local marginal list**. The example above means four local periods with values 200, 0, 500 and 300. `start` shifts the resulting series into project time.

For Manual Work:

```text
cost     = sum(cost_schedule_json)
duration = len(cost_schedule_json)
```

The backend derives those values from the schedule. The manual schedule replaces only the generated base work curve; the existing pre-work, subcontract share, no-billing, WIEB, advance, retention, payment-period and DLP logic then operates unchanged.

### 6.3 Scheduled Cost Activity

```json
{
  "name": "Elevator purchase",
  "activity_type": "other",
  "activity_mode": "scheduled_cost",
  "distribution_type": "manual",
  "cost_schedule_json": [0, 200000, 0, 500000],
  "start": 0
}
```

For Scheduled Cost:

```text
cost              = sum(cost_schedule_json)
duration          = len(cost_schedule_json)
marginal_work     = zero series
marginal_out_flow = cost_schedule_json
```

Scheduled Cost affects project direct cost, outflow, net cash and financing need. It does **not** create physical work, client billed work/PPC, or project work duration. Subcontract terms are not applied to the schedule.

### 6.4 Current accepted Activity source fields

```text
name
activity_type
activity_mode
distribution_type
cost_schedule_json
cost
duration
duration_units
start
advance
retention
release_retention_eop
dlp
duration_for_payment
work_in_excess
mobilization_period
subcontracted
skew
no_billing_period
```

`name` must be non-empty text.

`mobilization_period` is the legacy backend field currently used as the Activity **pre-work / no-work period** and remains active for Work Activities.

## 7. Version-1 compatibility

The new Activity fields are optional for older Version 1 files.

When they are absent:

```text
activity_mode = work
```

and distribution is inferred as:

```text
activity_type == "linear"  -> linear
otherwise                  -> s_curve
```

This preserves old files that used `activity_type = "linear"` as the calculation switch while allowing new files to keep type/category and distribution independent.

Do not silently change the meaning of an existing Version 1 field. If a future change cannot be made compatibly, introduce and document a new format version.

## 8. Deliberately excluded data

Portable files do not contain or trust server-owned identity or calculated output such as:

- Cashflow or Activity IDs;
- QAuth Unit/project ownership;
- creator/updater IDs or timestamps;
- deleted-state flags;
- calculated `workflow`, `inflow`, `outflow`, `netflow`, or cumulative financed-balance arrays;
- cached Activity `cash_flow_json`.

The following removed legacy Activity inputs are also not portable source fields:

- `mobilization` percentage;
- `profit`;
- `subcontractors_retention`;
- Activity-level `interest_rate`;
- `compounding_period`.

Existing upgraded database tables may physically retain old nullable columns, but the active ORM/API/client model does not use them.

## 9. Flutter export/import behavior

The Flutter client uses the same Version 1 marker. On export it writes current scenario and Activity source inputs. A simple Activity schedule editor may display a dense schedule as user-facing pairs such as:

```text
1: 500, 4: 900
```

but the stored/exported value remains:

```json
[500, 0, 0, 900]
```

This keeps UI representation independent from the backend schema.

On import, Flutter parses and validates the scenario and every Activity before submitting the payload. Backend validation remains authoritative.

## 10. Backend import behavior

The backend import endpoint:

1. requires the Version 1 format marker;
2. requires a cash-flow object and Activity list;
3. filters scenario and Activity data to supported fields;
4. normalizes legacy/new Activity mode and distribution semantics;
5. derives `cost` and `duration` from manual/scheduled schedules;
6. validates the scenario and every Activity;
7. calculates the imported scenario snapshot; and
8. commits the scenario and all Activities together only after the complete import is valid.

The import is transactional. Any validation or calculation failure rolls the new scenario back rather than leaving a partially imported Cashflow.

## 11. Relationship to future AI-assisted setup

Future AI-assisted setup may generate this portable input structure as a proposal, but it must follow the same semantic and validation rules as manual input.

AI-generated values must still pass backend validation and be recalculated by the normal CashflowPot engine.

Last reviewed against current q_flow backend and Flutter JSON codec: 13 October 2026.
