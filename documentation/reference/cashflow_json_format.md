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

Backend period indexes/start offsets use the model's existing zero-based convention. User-facing Flutter period labels are 1-based, so the client converts between UI representation and portable/backend values where required.

Important validation rules include:

- project/client `advance + retention <= 1.0`;
- Work Activity/subcontract `advance + retention <= 1.0`;
- Activity `skew` strictly inside `(-1, 1)`;
- non-null `inflow_curve_skew` strictly inside `(-1, 1)`;
- generated Work Activity cost > 0 and duration > 0;
- Manual Work and Scheduled Cost require a non-empty `cost_schedule_json` with finite non-negative values and a total > 0;
- payment period, DLP, start, pre-work, and no-billing period are non-negative integers;
- financing facilities must use supported draw/repayment methods and valid method-specific values.

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

`name` must be non-empty text. `description`, when present, must be text.

`interest_rate` is the legacy scenario financing rate used when explicit facilities are not configured. Explicit facility definitions carry their own financing terms.

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

## 6. Financing facilities

`financing_facilities` is an optional Version-1 field. Older files without it remain valid.

Each facility is a source/input definition. Calculated facility arrays such as Draw, Repayment, Interest, Fees, Outstanding, Available Limit, funded cash balance, and shortfall are **not** portable source data.

Current facility concepts include:

```text
name
type
start
end
limit
fees
interest_rate
revolving
draw_method
repayment_method
sweep_priority
advance_portion
repayment_percent
draw_schedule
repayment_schedule
installment_start
installment_interval
installment_count
```

Method-specific fields are used only when relevant to the selected draw/repayment method.

Supported draw methods:

```text
automatic_shortfall
scheduled
ppc_base
```

Supported repayment methods:

```text
cashflow_sweep
percent_of_ppc
equal_installments
scheduled
```

Scheduled draw/repayment schedules use period-to-amount maps. They are financing schedules, not Activity project-cost schedules.

A blank/null facility limit means unlimited. For finite limits, revolving capacity is based on current outstanding principal while non-revolving capacity is based on cumulative actual draws.

The exact calculation semantics are defined in [`financing_facilities.md`](financing_facilities.md).

## 7. Activity object

Activities separate **category/template**, **calculation mode**, and **Work distribution**.

### 7.1 Generated Work Activity

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

### 7.2 Manual Work Activity

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

`cost_schedule_json` is a **dense Activity-local marginal list**. The example above means four local periods with values 200, 0, 500 and 300. `start` shifts the resulting series into project time.

For Manual Work:

```text
cost     = sum(cost_schedule_json)
duration = len(cost_schedule_json)
```

The backend derives those values from the schedule. The manual schedule replaces only the generated base Work curve; the existing pre-work, subcontract share, no-billing, WIEB, advance, retention, payment-period and DLP logic then operates unchanged.

### 7.3 Scheduled Cost Activity

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

Scheduled Cost affects project direct cost, outflow, net cash and financing need. It does **not** create physical Work, client billed work/PPC, or project Work duration. Subcontract terms are not applied to the schedule.

The backend still stores the schedule as a dense **Activity-local** list plus `start`.

The Flutter Scheduled Cost editor may let the user enter absolute project-period pairs such as:

```text
4:25000, 7:75000
```

The client converts that to `start = firstPeriod - 1` plus a dense local schedule before sending/exporting the portable model. The portable JSON itself does not store the human-entered pair string.

### 7.4 Current accepted Activity source fields

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

## 8. Version-1 compatibility

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

Older Version-1 files without `financing_facilities` also remain valid.

Do not silently change the meaning of an existing Version 1 field. If a future change cannot be made compatibly, introduce and document a new format version.

## 9. Deliberately excluded data

Portable files do not contain or trust server-owned identity or calculated output such as:

- Cashflow or Activity IDs;
- QAuth Unit/project ownership;
- creator/updater IDs or timestamps;
- deleted-state flags;
- calculated `workflow`, `inflow`, `outflow`, `netflow`, funded-net, or cumulative balance arrays;
- calculated facility rows/series;
- backend summary/KPI values;
- cached Activity `cash_flow_json`.

The following removed legacy Activity inputs are also not portable source fields:

- `mobilization` percentage;
- `profit`;
- `subcontractors_retention`;
- Activity-level `interest_rate`;
- `compounding_period`.

Existing upgraded database tables may physically retain old nullable columns, but the active ORM/API/client model does not use them.

## 10. Flutter export/import behavior

The Flutter client uses the same Version 1 marker. On export it writes current scenario, facility, and Activity source inputs.

A Manual Work schedule editor may display a dense schedule as user-facing local pairs such as:

```text
1:500, 4:900
```

but the stored/exported value remains:

```json
[500, 0, 0, 900]
```

A Scheduled Cost editor uses absolute project-period pairs for the user but exports the converted `start` + dense local schedule.

This keeps UI representation independent from the backend schema.

On import, Flutter parses and validates the scenario and every Activity before submitting the payload. Backend validation remains authoritative.

## 11. Backend import behavior

The backend import endpoint:

1. requires the Version 1 format marker;
2. requires a cash-flow object and Activity list;
3. filters scenario and Activity data to supported fields;
4. validates/normalizes financing facility definitions;
5. normalizes legacy/new Activity mode and distribution semantics;
6. derives `cost` and `duration` from Manual Work/Scheduled Cost schedules;
7. validates the scenario and every Activity;
8. calculates the imported scenario snapshot; and
9. commits the scenario and all Activities together only after the complete import is valid.

The import is transactional. Any validation or calculation failure rolls the new scenario back rather than leaving a partially imported Cashflow.

## 12. Relationship to calculated totals and reports

Portable JSON stores **inputs**, not the report result.

The backend recalculates canonical totals/KPIs after import. Flutter/Excel should use those authoritative values instead of trusting or reconstructing totals from visibly rounded period arrays where that could create drift.

The portable format therefore remains suitable even when UI/Excel formatting conventions change.

## 13. Relationship to future AI-assisted setup

Future AI-assisted setup may generate this portable input structure as a proposal, but it must follow the same semantic and validation rules as manual input.

AI-generated values must still pass backend validation and be recalculated by the normal CashflowPot engine.

Last reviewed against current q_flow backend and Flutter JSON codec: 14 October 2026.
