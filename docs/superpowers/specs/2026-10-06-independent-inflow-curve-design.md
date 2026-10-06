# CashflowPot Independent Inflow Curve Design

Date: 2026-10-06

## Goal

Allow each CashflowPot scenario to choose how the main-contract value-of-work curve is generated before client billing/payment terms are applied.

The backend will support two calculation methods:

1. **Independent contract curve** — the default for new scenarios. Contract value follows its own linear or S-curve over the project execution horizon.
2. **Activity-linked curve** — the existing behavior. The combined activity cost-work curve is scaled to contract value.

The activity model continues to determine project outflow and project execution duration in both cases.

This backend phase does not change the Flutter UI or public website yet. Those follow after the backend model and API are stable.

## Core Principle

CashflowPot models inflow and outflow as related but distinct forecasts.

- **Outflow** comes from activity work, self-performed costs, subcontracted costs, and subcontract commercial/payment terms.
- **Inflow** starts from a contract-value work curve and is then converted to receipts through client WIEB, advance recovery, retention, payment delay, and DLP.

The new independent method does not require activity selling values, per-activity markup, or a Schedule of Values.

## Project Duration

There is no separate editable contract duration in this phase.

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
inflow_curve_type            : string
inflow_curve_skew            : float
```

### `use_independent_inflow_curve`

Meaning:

- `True` — generate the contract-value work curve independently from activity timing/profile.
- `False` — preserve the existing activity-linked contract-value calculation.

Application/model default for newly created scenarios: `True`.

Compatibility requirement: scenarios that already exist before this feature is introduced must remain on the current activity-linked method so their historical results do not silently change. Database migration/backfill therefore sets existing rows to `False`, while the model/default used for newly created rows is `True`.

### `inflow_curve_type`

Allowed values:

```text
s_curve
linear
```

Default: `s_curve`.

This controls only the independent contract curve. It is stored even when `use_independent_inflow_curve == False` so switching methods does not lose the user's independent-curve configuration.

### `inflow_curve_skew`

Controls front-loading/back-loading of the independent S-curve using the existing `Work` curve convention.

Validation:

```text
-1 < inflow_curve_skew < 1
```

Default: `0.0`.

Interpretation:

- negative — back-loaded;
- zero — balanced reference curve;
- positive — front-loaded.

For `linear`, the skew value is retained but does not affect the generated curve.

## Calculation Behavior

### Existing activity-linked method

When `use_independent_inflow_curve == False`, keep the current logic unchanged:

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

When `use_independent_inflow_curve == True`:

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

A clearer structure is:

```text
workflow()                 -> project cost-work series
factored_work()            -> existing activity-linked contract-value series
independent_contract_work()-> new independent contract-value series
contract_work()            -> selects one of the above based on the scenario flag
inflow()                   -> applies client commercial terms to contract_work()
```

The exact helper names may vary during implementation, but the separation between **contract-value work generation** and **cash timing transformation** should remain explicit.

## Validation and API Behavior

Backend validation is authoritative.

Validate:

- `use_independent_inflow_curve` is a boolean;
- `inflow_curve_type` is `s_curve` or `linear`;
- `inflow_curve_skew` is finite and strictly between `-1` and `1`.

The new fields must be returned by normal cashflow/scenario API serialization and accepted by scenario create/update routes.

Cashflow JSON import/export must preserve these fields. Existing version-1 imports that do not contain the fields remain valid and receive model defaults during import.

## Migration / Existing Data

Existing scenarios must not change calculation behavior merely because the backend was deployed.

Required migration semantics:

```text
existing rows:
    use_independent_inflow_curve = false
    inflow_curve_type = "s_curve"
    inflow_curve_skew = 0.0

new rows after deployment:
    use_independent_inflow_curve = true
    inflow_curve_type = "s_curve"
    inflow_curve_skew = 0.0
```

If the repository's deployment does not currently use an Alembic migration directory, implementation must still provide an explicit production-safe schema/backfill step rather than relying on SQLAlchemy model defaults to alter an existing table.

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

- new Cashflow model defaults select independent inflow;
- migration/backfill semantics preserve activity-linked behavior for pre-existing rows;
- independent linear curve distributes contract value across the derived duration and sums to contract value;
- independent S-curve uses skew and sums to contract value;
- positive and negative skew produce different timing shapes from the balanced curve;
- activity-linked mode reproduces the current `factored_work()` result unchanged;
- switching inflow method does not alter activity work/outflow calculations;
- client WIEB, advance, retention, payment delay and DLP still operate on whichever contract-work series is selected;
- no-active-activity scenarios still return an empty forecast;
- invalid flag/type/skew values are rejected;
- import/export preserves the new settings while older imports remain accepted;
- full existing backend test suite remains green.

## Out of Scope for This Backend Phase

- Flutter UI or scenario-form changes.
- Public-site wording changes.
- Editable contract duration independent from the activity-derived execution duration.
- Per-activity selling price, markup, Schedule of Values, or front-loading allocation.
- Manual period-by-period contract-value entry.
- Changes to activity outflow or subcontract calculations.
