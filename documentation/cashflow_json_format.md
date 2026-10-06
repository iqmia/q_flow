# CashFlowPot Portable Cash-Flow JSON

This document defines the portable JSON format used to export and import a CashFlowPot cash-flow scenario.

The format is intentionally an **input model**, not a serialized API response. It is suitable for backup/transfer and is the format future AI-assisted project generation should target.

## Version marker

```json
{
  "format": "cashflowpot.cashflow",
  "version": 1,
  "cashflow": {}
}
```

Importers must reject an unknown `format` or unsupported `version` rather than guessing semantics.

The independent-inflow settings were added as optional V1 fields. A V1 file created before these fields existed remains valid; when imported as a new scenario, normal backend defaults are applied to omitted fields.

## Units and conventions

- Percentage-like values are stored as API fractions: `0.10` means 10%, `0.50` means 50%, and `1.0` means 100%.
- Timing values are integer model **periods**. The JSON format does not assume that a period is necessarily a calendar month.
- `advance + retention` must not exceed `1.0` at either client or subcontract level.
- Activity `skew`, and non-null independent `inflow_curve_skew`, must be strictly greater than `-1` and strictly less than `1`.
- A null `inflow_curve_skew` is interpreted as the balanced value `0.0`; it does not disable independent inflow.
- Activity cost and duration must be greater than zero.
- Payment delay, DLP, start, pre-work, and no-billing periods must be non-negative integers.

## Cash-flow object

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
  "activities": []
}
```

### Inflow forecast settings

The independent contract-value curve is used only when:

```text
use_independent_inflow_curve is true
and
inflow_curve_type is not null
```

Otherwise the calculator uses the activity-linked contract-value method.

`inflow_curve_type` accepts:

- `"s_curve"`; or
- `"linear"`.

`inflow_curve_skew` controls front-loading/back-loading of the S-curve using the normal CashFlowPot skew convention. A null value is treated as `0.0`. The value is retained but has no calculation effect for a linear curve.

### WIEB

`wieb` is the project-level **Work in Excess of Billing (WIEB) forecasting assumption**. It is the estimated share of completed contract-value work that is not billed in the current period and is carried into the following billing period.

Actual WIEB is an amount/value; CashFlowPot stores the percentage assumption used to simulate it.

## Activity object

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

`work_in_excess` is the activity-level WIEB forecasting assumption applied to the **subcontracted share only**. The self-performed/direct share is paid as incurred and does not use WIEB.

## Deliberately excluded data

Portable files do not contain or trust:

- cash-flow or activity IDs;
- QAuth Unit/project ownership;
- creator/updater IDs or timestamps;
- deleted-state flags;
- calculated `workflow`, `inflow`, `outflow`, `netflow`, or financing-balance arrays;
- cached activity `cash_flow_json`;
- deprecated or currently unused activity fields such as `profit`, activity interest/compounding, or legacy subcontractor retention.

Those values are owned or recalculated by the server.

## Import behavior

A V1 import is validated twice:

1. the Flutter client validates the file before showing the confirmation dialog;
2. the backend validates the cash-flow and every activity again using the normal model rules.

The backend import is transactional. The new scenario and all activities are committed together only after the complete payload is valid and its calculated cash-flow snapshot can be generated. Any failure rolls the import back.

Older V1 files that omit the three independent-inflow fields remain valid. Because an import creates a **new** scenario, omitted values receive the current new-scenario defaults (`true`, `"s_curve"`, `0.0`). Existing database rows are different: schema upgrade adds nullable columns without backfilling them, so legacy stored scenarios naturally remain activity-linked until explicitly changed.
