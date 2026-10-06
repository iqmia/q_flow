# CashflowPot calculation model

This document is the canonical technical reference for the current CashflowPot financial model implemented in `q_flow`.

It defines the model direction, formulas, timing conventions, defaults, validation rules, legacy fields, and invariants that should remain consistent across the backend, Flutter client, exports, tests, public explanations, and future AI-assisted setup.

For the shorter product explanation, see [`../product.md`](../product.md).

## 1. Purpose

CashflowPot turns project execution, contract terms, and forecasting assumptions into a time-phased construction cash-flow forecast.

The model answers questions such as:

> Given the execution we currently expect, the contract/commercial terms we know, and the assumptions we are using, how much cash is expected to go out, how much is expected to come in, when, and what funding gap could result?

The result is a **forecast, not a guarantee**.

Planning data may inform activity timing, but CashflowPot calculates the commercial cash layer separately: billings, receipts, payments, net cash, cumulative cash balance, and financing exposure.

## 2. Model hierarchy

A QAuth Unit represents one CashflowPot Project.

A Project can contain multiple independent `Cashflow` scenarios. Each scenario contains Activities.

```text
QAuth Unit / Project
  └── Cashflow scenario
        └── Activities
```

A scenario owns its contract value, client terms, financing assumption, inflow method, and activities.

Activities own execution cost/timing and subcontract-side assumptions.

## 3. Time convention

The engine works in integer **model periods**.

The app is normally used monthly and `Activity.duration_units` defaults to `Months`, but the calculation engine itself works on periods rather than calendar dates.

Within one scenario, timing inputs must use a consistent period convention.

Examples:

```text
duration = 6               six execution periods
duration_for_payment = 2   payment occurs two periods after billing
dlp = 12                   second retention release is twelve periods after first release
```

The financing rate is also a **rate per model period**.

The scenario execution duration comes from the active Activity work series. The financial horizon can extend beyond execution because of WIEB carry, payment delay, retention releases, subcontract payment timing, and DLP.

## 4. Direction of the model

CashflowPot separates:

1. **project execution / outflow**; and
2. **main-contract value / inflow**.

Activities always determine execution cost, activity outflow, and project execution duration.

The main-contract value profile can be generated independently from activities or linked to the combined activity cost profile.

Client-side contract terms and assumptions are applied only after the contract-value work profile has been generated.

## 5. Core terminology

### Contract value

`Cashflow.contract_value`

The total client contract value represented by the scenario.

### Estimated activity cost

`Activity.cost`

The contractor's estimated cost for an Activity. Activity work curves are cost-loaded from this amount.

The current model does not require or infer individual Activity selling values or Activity-specific markup.

### Advance

At scenario level, `Cashflow.advance` is the client advance received by the contractor.

At Activity level, `Activity.advance` is the advance paid on the subcontracted share.

Advance is recovered proportionally from later progress cash.

### Retention

At both client and subcontract level, retention is withheld from progress cash and released later.

`release_retention_eop` is the fraction of the total retention released at the first/end-of-progress release point. The remainder is released after the DLP.

### Defects Liability Period (DLP)

The number of model periods between the first retention release and the remaining retention release.

Current timing convention:

```text
dlp = 0   both retention portions released in the same end period
dlp = 1   remaining portion one period later
dlp = N   remaining portion exactly N periods later
```

### Payment period

Backend field: `duration_for_payment`.

A value of `N` shifts progress receipts/payments exactly `N` model periods after billing.

### Work in Excess of Billings (WIEB)

Scenario field: `Cashflow.wieb`.

Activity field: `Activity.work_in_excess`.

Actual Work in Excess of Billings is a value/amount. CashflowPot stores a **percentage forecasting assumption**: the estimated share of completed work that is not billed in the current period and is carried into the following billing period.

WIEB changes **timing**, not lifetime value.

At scenario level it applies to client-side contract-value work.

At Activity level it applies only to the subcontracted share. Self-performed/direct cost is paid as incurred and is not adjusted by WIEB.

### Subcontracted share

`Activity.subcontracted`

The fraction of Activity cost treated as subcontracted/supplied and therefore subject to Activity subcontract terms.

The remainder is self-performed/direct cost.

### Pre-work period

Current backend field: `Activity.mobilization_period`.

Despite its legacy name, the current calculation uses this field as an initial no-work/pre-work period by prepending zero-cost work periods before the Activity work curve.

The separate `Activity.mobilization` percentage is currently not used by the calculation engine.

### No-billing period

`Activity.no_billing_period`

An initial subcontract billing window during which work accumulates before the first subcontract bill.

### Activity start

`Activity.start`

The number of project periods before the Activity/subcontract timeline begins. It shifts both Activity work and Activity outflow.

### Skew

`Activity.skew` and, for the independent S-curve, `Cashflow.inflow_curve_skew`.

Valid skew is strictly inside `(-1, 1)`.

With the current curve implementation:

- negative values back-load the curve;
- zero is the balanced reference; and
- positive values front-load the curve.

## 6. Activity work curve

For Activity duration `d`, skew `s`, estimated cost `c`, and time `t`, the current raw cumulative S-curve is:

```text
C_raw(t) = c * (s + 1) / ((s + 1) + exp(-(t / (0.1*d) + s^2 - 5)))
```

For a linear curve:

```text
C_linear(t) = c / d * t
```

Marginal work is obtained from differences between consecutive cumulative values.

The raw sigmoid does not necessarily end exactly at `c`. The engine calculates:

```text
error = c - sum(raw marginal work)
```

and applies this cubic cumulative correction over the duration:

```text
error_distribution(t)
    = -2 * error * t^3 / d^3
      + 3 * error * t^2 / d^2
```

The corrected cumulative curve is differenced again to produce final marginal work.

Invariant, subject to normal floating-point precision:

```text
sum(activity marginal work) = activity estimated cost
```

The current calculation switch uses the exact Activity type string `"linear"` for a linear curve. Other values use the S-curve calculation. This is legacy coupling between Activity category and distribution type and should not be copied into future semantic schemas.

## 7. Activity outflow

For Activity marginal work `W_t` and subcontracted fraction `q`:

```text
self_performed_cost_t = W_t * (1 - q)
subcontracted_work_t  = W_t * q
```

Self-performed/direct cost is paid in the same period as Activity work.

The subcontracted share follows subcontract terms.

### Subcontract billing and WIEB

The no-billing period is applied first. Work within that initial window accumulates into the first subcontract bill.

For billable subcontract work `S_t` and subcontract WIEB assumption `w`, the timing rule is conceptually:

```text
B_0 = S_0 * (1 - w)
B_t = S_t * (1 - w) + S_(t-1) * w
final_carry = S_last * w
```

After WIEB, subcontract advance recovery and retention reduce progress payments:

```text
subcontract_progress_payment_t
    = B_t * (1 - subcontract_advance - subcontract_retention)
```

The progress-payment series is then shifted by `Activity.duration_for_payment` periods.

The subcontract advance paid at the start of the Activity/subcontract timeline is:

```text
subcontract_advance_payment
    = activity_cost * subcontracted_share * subcontract_advance
```

Total subcontract retention is:

```text
subcontract_retention_value
    = activity_cost * subcontracted_share * subcontract_retention
```

The first retention portion is released at the end of the subcontract progress-payment sequence. The remaining portion is released according to the DLP rule.

Total Activity outflow is:

```text
activity_outflow_t
    = self_performed_cost_t + subcontractor_payment_t
```

Invariant for valid inputs:

```text
sum(activity outflow) = activity estimated cost
```

Advance, retention, WIEB, no-billing period, payment period, and DLP change **when** subcontracted cost is paid; they do not change the Activity's total estimated cost.

## 8. Project execution work and duration

The combined project cost-loaded workflow is the sum of all current non-deleted Activity work:

```text
project_cost_work_t = sum(activity_work_i,t)
```

Total entered Activity cost is:

```text
C = sum(project_cost_work_t)
```

The API currently returns this series under the legacy key:

```text
workflow
```

Execution duration is:

```text
execution_duration = max(length of active activity work series)
```

Activity start and pre-work periods therefore contribute to derived execution duration.

If no active Activities exist, the engine has no execution duration and returns an empty forecast.

## 9. Main-contract inflow method selection

Backend fields:

```text
Cashflow.use_independent_inflow_curve
Cashflow.inflow_curve_type
Cashflow.inflow_curve_skew
```

The Independent contract curve is selected only when:

```text
use_independent_inflow_curve is True
and
inflow_curve_type is not NULL
```

Otherwise the engine uses Activity-linked inflow.

A null `inflow_curve_skew` is treated as balanced `0.0` and does **not** disable Independent mode.

Valid non-null `inflow_curve_type` values are:

```text
s_curve
linear
```

## 10. Independent contract curve

This is the default for new scenarios.

The contract-value curve uses:

```text
duration = execution_duration
value    = contract_value
curve    = inflow_curve_type
skew     = inflow_curve_skew, with NULL interpreted as 0.0
```

For a Linear curve, contract value is distributed evenly over execution duration.

For an S-curve, the same `Work` mathematics and error correction are used so the total contract-value work returns to the contract value.

Activities determine execution duration and project outflow, but do not allocate main-contract value.

The Independent contract curve does not infer Activity selling prices, Activity markup allocation, or a Schedule of Values.

## 11. Activity-linked inflow

This is the alternative / compatibility method.

For contract value `V` and total entered Activity cost `C`:

```text
value_factor = V / C
contract_value_work_t = project_cost_work_t * value_factor
```

Therefore, when `C > 0`:

```text
sum(contract_value_work) = contract value
```

This method assumes the main-contract value profile follows the combined Activity cost-work profile using one project-level value factor.

It still does not assign an individual selling value or markup to each Activity.

## 12. Project inflow

The chosen method first produces contract-value work `E_t`.

Let:

- `a` = client advance fraction;
- `r` = client retention fraction;
- `w` = client WIEB assumption;
- `p` = client payment period; and
- `V` = contract value.

Client advance at the start is:

```text
advance_receipt = a * V
```

### Client WIEB

WIEB applies from the first work period:

```text
B_0 = E_0 * (1 - w)
B_t = E_t * (1 - w) + E_(t-1) * w
final_carry = E_last * w
```

### Progress receipts

Advance recovery and retention reduce the billable progress amount:

```text
progress_receipt_t = B_t * (1 - a - r)
```

The progress receipt is shifted by exactly `p` periods.

The engine always establishes a period-zero position, so payment period has the same meaning whether or not client advance is zero.

### Client retention

Total client retention:

```text
retention_value = r * V
```

With `e = release_retention_eop`:

```text
first_retention_release  = retention_value * e
second_retention_release = retention_value * (1 - e)
```

The first portion is released at the end of the progress-payment sequence, after any final WIEB carry.

The remaining portion is released exactly according to the DLP convention.

Project inflow invariant for valid inputs:

```text
sum(project inflow) = contract value
```

For Independent inflow:

```text
sum(independent contract work) = contract value
length(independent contract work) = execution_duration
```

Client advance, retention, WIEB, payment period, and DLP redistribute receipt timing; they do not create or remove contract value.

## 13. Project outflow

Project outflow is the period-by-period sum of current Activity outflows:

```text
project_outflow_t = sum(activity_outflow_i,t)
```

Deleted Activities are excluded.

Changing Independent/Activity-linked inflow settings does not change Activity work or project outflow.

## 14. Net cash and financing

For each model period:

```text
net_cash_flow_t = inflow_t - outflow_t
```

Let `balance_(t-1)` be the previous financed cumulative balance and `i` the financing rate per model period:

```text
pre_finance_balance_t = balance_(t-1) + net_cash_flow_t
```

If negative:

```text
balance_t = pre_finance_balance_t * (1 + i)
```

Otherwise:

```text
balance_t = pre_finance_balance_t
```

The current engine applies financing cost only when cumulative cash is negative. It does not earn interest on positive cash.

The API currently exposes the cumulative financed balance under the legacy key:

```text
outflow_with_interest
```

That key is **not** a marginal outflow series.

## 15. Current snapshot fields

`Cashflow.as_dict_with_activities()` returns the current scenario data, active Activities, calculated snapshot, and summary.

Calculated snapshot keys include:

```text
workflow
inflow
outflow
netflow
outflow_with_interest
duration
```

The summary currently includes:

```text
total_inflow
subcontracted_cost
self_performed_cost
direct_cost
financing_cost
total_cost
final_cash_balance
work_duration
dlp
financial_horizon
```

## 16. Backend validation

Backend validation is authoritative.

### Cashflow/scenario inputs

- `contract_value`: finite and non-negative.
- `advance`, `retention`, `release_retention_eop`, `wieb`: each in `[0, 1]`.
- `advance + retention <= 1`.
- `interest_rate`: finite and non-negative.
- `dlp`, `duration_for_payment`: non-negative integers.
- `use_independent_inflow_curve`: boolean or null.
- `inflow_curve_type`: `s_curve`, `linear`, or null.
- non-null `inflow_curve_skew`: finite and strictly inside `(-1, 1)`.

### Activity inputs

- `cost`: finite and greater than zero.
- `duration`: integer greater than zero.
- `skew`: finite and strictly inside `(-1, 1)`.
- `start`, `dlp`, `duration_for_payment`, `mobilization_period`, `no_billing_period`: non-negative integers.
- `advance`, `retention`, `release_retention_eop`, `work_in_excess`, `mobilization`, `profit`, `subcontracted`: each in `[0, 1]`.
- `advance + retention <= 1`.

Clients should mirror useful validation for UX, but backend rules remain authoritative.

## 17. Current backend defaults

Defaults are starting values, not universal construction rules.

### Cashflow scenario defaults

| Parameter | Backend default |
| --- | ---: |
| Client advance | 10% |
| Client retention | 10% |
| Retention released at first release | 50% |
| DLP | 12 periods |
| Client payment period | 1 period |
| Financing rate | 0.5% per period |
| Client WIEB assumption | 20% |
| Contract value | 0 |
| Use Independent inflow curve | `true` |
| Inflow curve type | `s_curve` |
| Inflow curve skew | `0.0` |

Existing database rows created before Independent-inflow columns were added can contain null in those three fields. They remain Activity-linked without backfill until changed.

### Activity model defaults

| Parameter | Backend model default |
| --- | ---: |
| Activity type | `General` |
| Cost | `0.0` (creation validation still requires `> 0`) |
| Duration unit | `Months` |
| Duration | 4 periods |
| Start | 0 |
| Subcontract advance | 10% |
| Subcontract retention | 10% |
| Retention released at first release | 50% |
| DLP | 0 |
| Subcontract payment period | 1 period |
| Subcontract WIEB assumption | 10% |
| Pre-work period (`mobilization_period`) | 1 period |
| Subcontracted share | 70% |
| Skew | `0.0` |
| No-billing period | 0 |

Some client Activity presets can provide different starting values. Presets are heuristics, not contractual rules.

## 18. Legacy and unused Activity fields

The schema currently retains compatibility fields that are not active calculation drivers:

- `mobilization` — percentage field; current calculation uses `mobilization_period` as pre-work/no-work time instead;
- `profit` — validated/stored but not used by the cash-flow engine;
- `subcontractors_retention` — deprecated; use `retention`;
- Activity `interest_rate` — deprecated; financing is scenario-level;
- `compounding_period` — deprecated.

Future clients and AI schemas must not treat these as active calculation inputs unless the model is deliberately changed and documented.

## 19. Semantic naming guidance

| Backend/API name | Preferred semantic meaning |
| --- | --- |
| `Cashflow.advance` | Client advance payment |
| `Cashflow.retention` | Client retention |
| `Cashflow.duration_for_payment` | Client payment period |
| `Cashflow.wieb` | Client WIEB assumption (%) |
| `Cashflow.use_independent_inflow_curve` | Inflow forecast method |
| `Cashflow.inflow_curve_type` | Contract value curve type |
| `Cashflow.inflow_curve_skew` | Contract value curve timing/skew |
| `Activity.cost` | Estimated activity cost |
| `Activity.subcontracted` | Subcontracted share |
| `Activity.advance` | Subcontract advance |
| `Activity.retention` | Subcontract retention |
| `Activity.duration_for_payment` | Subcontract payment period |
| `Activity.work_in_excess` | Subcontract WIEB assumption (%) |
| `Activity.mobilization_period` | Pre-work period |
| API `workflow` | Cost-loaded work / execution cost profile |
| API `netflow` | Net cash flow |
| API `outflow_with_interest` | Cumulative cash balance after financing |

User-facing text should expand WIEB and DLP at first use.

## 20. Current calculation boundaries

The engine does not currently calculate:

- critical path or schedule logic;
- delay/EOT entitlement;
- labour/plant/material productivity or resource availability;
- detailed BOQ measurement or earned-value measurement;
- tax, currency, escalation, bonds, and similar mechanisms unless represented indirectly in entered values/costs;
- individual Activity selling values or Activity-specific markup;
- detailed Schedule of Values; or
- accounting statements.

Those may influence scenario inputs, but are outside the current calculation engine.

## 21. Regression invariants

Calculation changes should preserve or deliberately revise these invariants with tests and documentation together:

1. Corrected marginal Activity work sums to Activity estimated cost.
2. Total Activity outflow sums to Activity estimated cost for valid inputs.
3. Project inflow sums to contract value for valid terms when active Activities provide an execution duration.
4. Independent contract work sums to contract value and uses the Activity-derived execution duration.
5. Independent inflow is selected only when `use_independent_inflow_curve is True` and `inflow_curve_type is not NULL`.
6. Null Independent skew means balanced `0.0`; it does not disable Independent mode.
7. Changing the inflow method does not change Activity work or project outflow.
8. WIEB applies from the first billing period and shifts timing only.
9. Payment period `N` shifts progress cash exactly `N` periods.
10. DLP `0` releases remaining retention in the same end period; DLP `N` releases it exactly `N` periods later.
11. Advance plus retention cannot exceed 100% at client or subcontract level.
12. Deleted Activities do not contribute to current project work/outflow.
13. Positive current skew front-loads the S-curve relative to balanced; negative skew back-loads it.
14. With no active Activities, the current engine returns an empty forecast because there is no derived execution duration.

If a future change intentionally revises one of these rules, update implementation, tests, this reference, and affected overview/UI documentation in the same change.

Last reviewed against current `q_flow` implementation: 7 October 2026.
