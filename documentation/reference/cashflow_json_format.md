# CashflowPot portable cash-flow JSON

This document defines the current portable JSON format used to export and import a CashflowPot cash-flow scenario.

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
- Activity/subcontract `advance + retention <= 1.0`;
- Activity `skew` strictly inside `(-1, 1)`;
- non-null `inflow_curve_skew` strictly inside `(-1, 1)`;
- Activity cost > 0;
- Activity duration > 0;
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
  "financing_facilities": [
    {
      "id": "od-1",
      "name": "Project overdraft",
      "type": "Overdraft",
      "draw_method": "automatic_shortfall",
      "repayment_method": "cashflow_sweep",
      "start": 0,
      "end": 12,
      "limit": 200000,
      "fees": 500,
      "interest_rate": 0.01,
      "revolving": true,
      "sweep_priority": 0
    }
  ],
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

`financing_facilities` is optional for older version-1 files. Each facility is
an editable input model. Scheduled draws and repayments use period-to-amount
maps; PPC discounts use `advance_portion`; PPC repayments use
`repayment_percent`; equal installments use `installment_start`,
`installment_interval`, and `installment_count`. A scheduled facility draw is
capped at available capacity, with the undrawn amount reported in the
calculated snapshot.

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

The three Independent-inflow fields are optional for Version 1 compatibility.

If they are omitted when importing a **new** scenario, current backend scalar defaults are applied:

```text
use_independent_inflow_curve = true
inflow_curve_type            = s_curve
inflow_curve_skew            = 0.0
```

This differs from legacy database rows created before these columns existed: those stored rows may retain null values and therefore remain Activity-linked until explicitly changed.

## 5. Work in Excess of Billings (WIEB)

`wieb` is the project-level Work in Excess of Billings (WIEB) forecasting assumption.

It represents the estimated share of completed contract-value work that is not billed in the current period and is carried into the following billing period.

Actual WIEB is an amount/value; the portable file stores the percentage assumption used by CashflowPot.

WIEB changes timing, not lifetime project value.

## 6. Activity object

Example:

```json
{
  "name": "Concrete works",
  "activity_type": "concrete",
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

Current accepted Activity input fields are:

```text
name
activity_type
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

`name` must be non-empty text. `cost` and `duration` are required.

`work_in_excess` is the subcontract-side Work in Excess of Billings (WIEB) assumption and applies only to the subcontracted share. Self-performed/direct cost is paid as incurred.

`mobilization_period` is the legacy backend field currently used as the Activity **pre-work / no-work period**.

## 7. Deliberately excluded data

Portable files do not contain or trust server-owned identity or calculated output such as:

- Cashflow or Activity IDs;
- QAuth Unit/project ownership;
- creator/updater IDs or timestamps;
- deleted-state flags;
- calculated `workflow`, `inflow`, `outflow`, `netflow`, or cumulative financed-balance arrays;
- cached Activity `cash_flow_json`;
- deprecated/unused Activity fields such as `profit`, Activity financing/compounding fields, or legacy `subcontractors_retention`.

Those values are server-owned, compatibility-only, or recalculated.

The backend filters imported objects to the current allowed field set rather than trusting arbitrary extra keys.

## 8. Current Flutter export/import behavior

The Flutter client currently uses the same constants:

```text
format  = cashflowpot.cashflow
version = 1
```

On export it writes the current scenario inputs and Activities using the fields above.

The generated filename follows the pattern:

```text
<safe-scenario-name>.cashflowpot.json
```

On import, the Flutter client:

1. parses JSON;
2. verifies format/version;
3. validates the scenario fields;
4. validates every Activity;
5. creates an import preview containing the scenario name, Activity count, and contract value; and
6. only then submits the payload to the backend import endpoint.

Client validation improves UX but is not authoritative.

## 9. Backend import behavior

The backend import endpoint validates the payload again.

Current behavior is:

1. require the Version 1 format marker;
2. require a cash-flow object and Activity list;
3. filter scenario and Activity data to supported fields;
4. apply backend scalar defaults to omitted optional values;
5. validate the scenario;
6. validate every Activity;
7. calculate the imported scenario snapshot; and
8. commit the scenario and all Activities together only after the complete import is valid.

The import is transactional. Any validation or calculation failure rolls the new scenario back rather than leaving a partially imported Cashflow.

## 10. Compatibility expectations for Version 1

Version 1 is designed so older files that predate Independent inflow fields remain importable.

Do not silently change the meaning of an existing Version 1 field. If a future change cannot be made compatibly, introduce and document a new format version.

Do not serialize calculated arrays into the portable input model as a substitute for recalculation. The backend calculation engine remains authoritative.

## 11. Relationship to future AI-assisted setup

Future AI-assisted setup may generate this portable input structure as a proposal, but it must follow the same semantic and validation rules as manual input.

AI-generated values must still pass backend validation and be recalculated by the normal CashflowPot engine.

Last reviewed against current q_flow backend and Flutter JSON codec: 7 October 2026.
