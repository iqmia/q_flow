# CashflowPot Independent Inflow Curve Design

Date: 2026-10-06

## Goal

Allow each CashflowPot scenario to choose how the main-contract value-of-work curve is generated before client billing/payment terms are applied.

The backend supports two calculation methods:

1. **Independent contract curve** — the default for newly created scenarios. Contract value follows its own linear or S-curve over the derived project execution horizon.
2. **Activity-linked curve** — the existing behavior. The combined activity cost-work curve is scaled to contract value.

The activity model continues to determine project outflow and project execution duration in both cases.

This backend phase does not change the Flutter UI or public website yet. Those follow after the backend model and API are stable.

## Core Principle

CashflowPot models inflow and outflow as related but distinct forecasts.

- **Outflow** comes from activity work, self-performed costs, subcontracted costs, and subcontract commercial/payment terms.
- **Inflow** starts from a contract-value work curve and is then converted to receipts through client WIEB, advance recovery, retention, payment delay, and DLP.

The independent method does not require activity selling values, per-activity markup, or a Schedule of Values.

## Project Duration

There is no separate editable contract duration.

The project execution horizon remains derived from the active activity work series:

```text
execution_duration = max(length of active activity work series)
```

The independent contract curve uses that same derived duration. This keeps the inflow and outflow base execution horizons aligned while allowing their shapes to differ.

The financial horizon may extend beyond execution because of WIEB carry, payment delay, retention release, subcontract payment timing, and DLP. That is expected and is not treated as a duration discrepancy.

If there are no active activities, the calculator continues to return an empty forecast because there is no derived execution duration and no meaningful outflow.

## Cashflow Model Fields

Add these fields to `Cashflow`:

```text
use_independent_inflow_curve : bool
inflow_curve_type            : string | null
inflow_curve_skew            : float | null
```

Application/model defaults for newly created scenarios:

```text
use_independent_inflow_curve = true
inflow_curve_type            = "s_curve"
inflow_curve_skew            = 0.0
```

### Calculation-method rule

Use the independent contract curve only when both conditions are true:

```text
use_independent_inflow_curve is True
AND
inflow_curve_type is not NULL
```

Otherwise, use the existing activity-linked calculation.

This rule provides backward compatibility without a data backfill. Existing database rows may have `NULL` for the newly added fields and therefore continue using the activity-linked model automatically.

### `inflow_curve_type`

Allowed non-null values:

```text
s_curve
linear
```

For newly created scenarios the default is `s_curve`.

A `NULL` value means the independent method is not active, even if the boolean is true. This is the compatibility fallback for scenarios created before these fields existed.

### `inflow_curve_skew`

Controls front-loading/back-loading of the independent S-curve using the existing `Work` curve convention.

For an active independent curve, validation is:

```text
-1 < inflow_curve_skew < 1
```

New-scenario default: `0.0`.

Interpretation:

- negative — back-loaded;
- zero — balanced reference curve;
- positive — front-loaded.

For `linear`, the stored skew value does not affect the generated curve.

## Calculation Behavior

### Activity-linked method

Use this method whenever the independent-method rule is false.

Keep the current logic unchanged:

```text
activity work curves
    -> combined project cost-work curve
    -> multiply by contract_value / total_entered_activity_cost
    -> contract-value work curve
    -> client commercial terms
    -> inflow
```

The current `factored_work()` behavior remains the compatibility reference.

### Independent contract curve

When:

```text
use_independent_inflow_curve is True
AND
inflow_curve_type is not NULL
```

then:

1. derive `execution_duration` from the active activity work series;
2. generate a `Work` curve using:
   - `d = execution_duration`
   - `c = contract_value`
   - `s = inflow_curve_skew`
   - linear or S-curve according to `inflow_curve_type`;
3. use the resulting marginal contract-value work series as the input to the existing client inflow transformation;
4. apply the existing client advance, WIEB, retention, payment-delay and DLP rules without changing their semantics.

Conceptually:

```text
contract value + derived duration + curve type + skew
    -> contract-value work per period
    -> WIEB / advance recovery / retention / payment delay / DLP
    -> inflow
```

The independent contract-value work series must sum to `contract_value` within normal floating-point precision.

## Calculator Structure

Refactor the calculator so client inflow does not directly assume `factored_work()`.

A clear structure is:

```text
workflow()                  -> project cost-work series
factored_work()             -> existing activity-linked contract-value series
independent_contract_work() -> independent contract-value series
contract_work()             -> selects the applicable method
inflow()                    -> applies client commercial terms to contract_work()
```

The exact helper names may vary during implementation, but the separation between **contract-value work generation** and **cash timing transformation** should remain explicit.

## Validation and API Behavior

Backend validation is authoritative.

Rules:

- `use_independent_inflow_curve`, when supplied, must be a boolean;
- `inflow_curve_type`, when non-null, must be `s_curve` or `linear`;
- when the independent method is active, `inflow_curve_skew` must be finite and strictly between `-1` and `1`;
- a null curve type always falls back to the activity-linked calculation.

The new fields must be returned by normal cashflow/scenario API serialization and accepted by scenario create/update routes.

Cashflow JSON import/export must preserve the new settings. Older imports that do not contain the fields remain valid; because an import creates a new scenario, normal model defaults may be applied to missing fields.

## Database Compatibility

No existing scenario rows need to be updated or backfilled.

A database **schema change is still required** to add the nullable columns. The columns should be introduced without a data-update step so existing rows can remain `NULL`.

Compatibility then follows naturally:

```text
existing row with no curve settings
    -> inflow_curve_type is NULL
    -> activity-linked calculation

new scenario created by the application
    -> use_independent_inflow_curve = true
    -> inflow_curve_type = "s_curve"
    -> inflow_curve_skew = 0.0
    -> independent calculation
```

This avoids a data migration while preserving previous forecast behavior.

## Invariants

The existing invariants remain:

```text
sum(activity marginal work) = activity estimated cost
sum(activity outflow)       = activity estimated cost
sum(project inflow)         = contract value
```

For independent inflow, add:

```text
sum(independent contract work) = contract value
length(independent contract work) = derived execution duration
```

Commercial variables alter timing, not lifetime contract value.

## Tests

Backend tests should cover at least:

- newly created Cashflow scenarios default to independent inflow with `s_curve` and zero skew;
- a null `inflow_curve_type` always uses the activity-linked method;
- `use_independent_inflow_curve = false` uses the activity-linked method even when curve settings exist;
- independent linear curve distributes contract value across the derived duration and sums to contract value;
- independent S-curve uses skew and sums to contract value;
- positive and negative skew produce different timing shapes from the balanced curve;
- activity-linked mode reproduces the current `factored_work()` result unchanged;
- switching inflow method does not alter activity work/outflow calculations;
- client WIEB, advance, retention, payment delay and DLP operate on whichever contract-work series is selected;
- no-active-activity scenarios still return an empty forecast;
- invalid flag/type/skew values are rejected;
- import/export preserves the new settings and older imports remain accepted;
- full existing backend test suite remains green.

## Out of Scope for This Backend Phase

- Flutter UI or scenario-form changes.
- Public-site wording changes.
- Editable contract duration independent from the activity-derived execution duration.
- Per-activity selling price, markup, Schedule of Values, or front-loading allocation.
- Manual period-by-period contract-value entry.
- Changes to activity outflow or subcontract calculations.
