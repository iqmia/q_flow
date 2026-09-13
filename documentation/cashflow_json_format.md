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

## Units and conventions

- Percentage-like values are stored as API fractions: `0.10` means 10%, `0.50` means 50%, and `1.0` means 100%.
- Timing values are integer model **periods**. The JSON format does not assume that a period is necessarily a calendar month.
- `advance + retention` must not exceed `1.0` at either client or subcontract level.
- `skew` must be strictly greater than `-1` and strictly less than `1`.
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
  "activities": []
}
```

`wieb` is the existing backend field name. In the user interface it is presented as **Billing deferral**: the share of completed work carried into the following billing period.

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

`work_in_excess` is the activity-level backend name for the same billing-deferral concept represented by project-level `wieb`.

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
