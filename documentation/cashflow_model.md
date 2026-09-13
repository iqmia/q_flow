# CashFlowPot calculation model

This document is the canonical reference for the CashFlowPot financial model in `q_flow`.

It defines what the model is intended to do, the meaning of its inputs, the calculation sequence, and the assumptions that must remain consistent across the backend, clients, exports, tests, and any future AI-assisted project setup.

## 1. Purpose and scope

CashFlowPot is a lightweight project cash-flow forecasting model for contractors. It approximates future cash inflows and outflows from a relatively small set of project, activity, subcontracting, billing, payment, and financing assumptions.

A useful summary of the question it answers is:

> Given what we currently expect to execute, how much cash is likely to go out, how much is likely to come in, when, and what funding gap could result?

CashFlowPot is **not** a replacement for Primavera P6, MS Project, a detailed resource-loaded programme, quantity-based cost loading, a full cost-control system, or a detailed Excel cash-flow model. It does not model individual labour, plant, material, productivity, or quantity resources.

Detailed resource- and quantity-loaded forecasts can require significant effort to keep current on large and fast-changing construction projects. CashFlowPot is intended to remain useful when a detailed model does not yet exist, when it is not economical to update it for every financial question, or when the detailed baseline has become stale and a rapid forecast-to-completion is needed.

The output is an approximation based on the assumptions supplied to the model. It is decision-support information, not a guarantee of future project performance.

### Typical uses

CashFlowPot is particularly useful for:

- tender cash-flow forecasting and bid assessment;
- feasibility studies and early-stage project planning;
- estimating working-capital and peak funding requirements;
- overdraft, revolving-credit, and banking-facility planning;
- contract-condition and payment-term negotiation;
- mobilization and early-project liquidity planning;
- subcontracting and procurement strategy comparisons;
- rapid what-if financial modelling;
- monthly management cash-flow forecasting without rebuilding a detailed programme;
- early warning of a worsening liquidity position;
- mid-project re-baselining and forecast-to-completion on distressed projects;
- stale-baseline recovery when a detailed programme has not been resource/cost updated recently;
- estimating the cash consequence of an expected delay, without performing delay or entitlement analysis;
- estimating the cash consequence of major variations or recovery strategies;
- retention and close-out cash forecasting; and
- communicating financial scenarios to project management, commercial teams, management, lenders, and partners.

## 2. Time convention

The engine works in integer **periods**. The current activity model defaults `duration_units` to `Months`, and the application is normally used as a monthly cash-flow model, but the calculation engine itself operates on periods rather than calendar dates.

All timing inputs must therefore use the same period unit within one cash-flow scenario.

Examples:

- `duration = 6` means six model periods;
- `duration_for_payment = 2` means payment is received or made two model periods after billing;
- `dlp = 12` means the second retention release occurs twelve model periods after the first retention-release point.

The interest rate is also a **rate per model period**. A monthly model therefore requires a monthly financing rate, not an annual rate entered unchanged.

## 3. Direction of the model

The same commercial concepts appear at two different levels and must not be confused.

### Cash-flow/project level

Project-level terms describe money between the **client and the contractor**. They primarily determine project **inflow**.

Examples: client advance, client retention, client payment delay, and client WIEB.

### Activity level

Activity-level commercial terms describe the subcontracted share of an activity between the **contractor and its subcontractor/supplier**. They primarily determine project **outflow**.

Examples: subcontract advance, subcontract retention, subcontract payment delay, and subcontract WIEB.

Future UI text and AI schemas should use the contextual names above even though some backend columns retain shorter legacy names such as `advance`, `retention`, and `duration_for_payment`.

## 4. Core terminology

### Contract value

The total client contract value represented by one cash-flow scenario.

Backend field: `Cashflow.contract_value`.

### Estimated activity cost

The contractor's estimated cost of an activity. Activity work curves are cost-loaded from this amount.

Backend field: `Activity.cost`.

The current model does **not** store a separate selling value for each activity. Contract value is allocated across activities proportionally to their estimated cost as described in section 7.

### Advance payment

A percentage paid at the beginning of the relevant relationship.

At project level this is a client advance received by the contractor. At activity level it is an advance paid by the contractor on the subcontracted share.

The model also recovers the advance proportionally from later progress payments.

### Retention

A percentage withheld from progress payments and released later.

`release_retention_eop` is the fraction of total retention released at the first/end-of-project release point. The balance is released after the DLP.

Example: retention = 10% and release at EOP = 50% means 5% of the relevant value is released at the first release point and the other 5% after the DLP.

### DLP — Defects Liability Period

The number of model periods between the first retention release and the remaining retention release.

CashFlowPot uses the following timing convention:

- `dlp = 0`: both retention portions are released in the same end period;
- `dlp = 1`: the remaining portion is released one period later;
- `dlp = N`: the remaining portion is released exactly N periods later.

### Payment delay

Backend field: `duration_for_payment`.

The number of model periods between billing and payment.

A value of `N` shifts a progress receipt/payment exactly N periods. This meaning is independent of whether an advance payment exists.

### WIEB — Work in Excess of Billing

Project backend field: `Cashflow.wieb`.

Activity backend field: `Activity.work_in_excess`.

In CashFlowPot, WIEB is the **share of completed work that is not billed in the current billing period and is carried into the next billing period**.

This is a simplified forecasting assumption. It should not be confused with every accounting use of underbilling/work-in-excess terminology.

If WIEB is 20%, then 80% of the current period's otherwise billable work is billed in that period and 20% is carried into the following billing period.

WIEB affects **timing**, not the lifetime value of the work. Increasing WIEB generally delays cash receipts/payments and can increase the contractor's temporary funding requirement.

### Subcontracted share

Backend field: `Activity.subcontracted`.

The fraction of an activity cost assumed to be procured through subcontractors/suppliers and therefore subject to the activity's subcontract billing/payment assumptions.

The remaining share is treated as self-performed/direct cost and paid in the same period as the activity cost is incurred.

### No-billing period

Backend field: `Activity.no_billing_period`.

An initial period during which the subcontractor does not issue progress bills. Work performed during this period accumulates into the first bill after the no-billing period.

### Pre-work period

Current backend field: `Activity.mobilization_period`.

Despite the legacy name, the current calculation engine uses this as an initial **no-work/pre-work period**. It prepends periods with no activity cost-loaded work before the main work curve begins.

The separate `mobilization` percentage field is not currently used by the calculation engine.

### Activity start

Backend field: `Activity.start`.

The number of project periods before the activity/subcontract relationship begins. It shifts both the activity work curve and the activity outflow by that number of periods.

### Skew

Backend field: `Activity.skew`.

Controls the timing shape of a non-linear activity cost curve. Valid values are greater than -1 and less than 1.

Within the current curve implementation:

- negative skew tends to back-load the activity;
- zero gives the balanced reference curve; and
- positive skew tends to front-load the activity.

`activity_type == "linear"` uses a linear distribution. Other activity types currently use the sigmoid/S-curve calculation.

## 5. Activity work curve

For an activity with:

- duration `d`;
- skew `s`;
- estimated cost `c`; and
- model time `t`;

the linear cumulative work curve is:

```text
C_linear(t) = c / d * t
```

For a non-linear activity, the raw cumulative curve is:

```text
C_raw(t) = c * (s + 1) / ((s + 1) + exp(-(t / (0.1*d) + s^2 - 5)))
```

Marginal activity cost in each period is calculated from the difference between consecutive cumulative values.

The raw sigmoid does not necessarily end at exactly `c`. The engine calculates the residual error:

```text
error = c - sum(raw marginal work)
```

and applies a cubic cumulative correction over the activity duration:

```text
error_distribution(t)
    = -2 * error * t^3 / d^3
      + 3 * error * t^2 / d^2
```

The corrected cumulative curve is then differenced again to produce the final marginal activity work/cost flow.

### Invariant

Subject to normal floating-point precision:

```text
sum(activity marginal work) = activity estimated cost
```

The pre-work period and activity start add zero periods but do not change total activity cost.

## 6. Activity outflow

Each activity is divided into a self-performed share and a subcontracted share.

For activity marginal work `W_t` and subcontracted fraction `q`:

```text
self_performed_cost_t = W_t * (1 - q)
subcontracted_work_t  = W_t * q
```

### Subcontract billing

After applying any no-billing period, WIEB is applied to the subcontracted billable work.

For billable subcontract work `S_t` and WIEB `w`:

```text
B_0 = S_0 * (1 - w)

B_t = S_t * (1 - w) + S_(t-1) * w

final_carry = S_last * w
```

The progress-payment portion after advance recovery and retention is:

```text
subcontract_progress_payment_t
    = B_t * (1 - subcontract_advance - subcontract_retention)
```

The payment series is shifted by the subcontract payment delay.

The subcontract advance is added at the beginning of the activity/subcontract timeline:

```text
subcontract_advance_payment
    = activity_cost * subcontracted_share * subcontract_advance
```

Total subcontract retention is:

```text
subcontract_retention_value
    = activity_cost * subcontracted_share * subcontract_retention
```

The first retention portion is released at the end of the subcontract progress-payment sequence. The remaining portion is released according to the DLP convention in section 4.

Total activity outflow by period is:

```text
activity_outflow_t
    = self_performed_cost_t + subcontractor_payment_t
```

### Invariant

For valid parameters and ignoring the project-level financing calculation:

```text
sum(activity outflow) = activity estimated cost
```

Advance, retention, WIEB, no-billing period, payment delay, and DLP change **when** the subcontracted portion is paid. They do not change the activity's total estimated cost.

## 7. Project cost-loaded work and contract-value allocation

The project's raw workflow is the sum of all active activity marginal cost flows:

```text
project_cost_work_t = sum(activity_work_i,t)
```

The total estimated project cost currently represented by the entered activities is:

```text
C = sum(project_cost_work_t)
```

The API currently returns this cost-loaded series under the legacy key `workflow`.

### Contract-value allocation

CashFlowPot currently assumes the same contract-value-to-cost factor across all entered activities.

For project contract value `V` and total entered activity cost `C`:

```text
value_factor = V / C
```

and:

```text
contract_value_work_t = project_cost_work_t * value_factor
```

Therefore:

```text
sum(contract_value_work) = contract_value
```

when `C > 0`.

This is a deliberate simplification. The model does not currently know the individual selling value or markup of each activity.

Example:

```text
Contract value             = 100
Total entered activity cost = 80
Value factor               = 100 / 80 = 1.25
```

An activity cost flow of 10 is therefore treated as 12.5 of contract-value work for client billing purposes.

Until all expected activities/costs have been entered, `contract_value - total_entered_activity_cost` should not automatically be interpreted as final project profit. It is only the difference between the contract value and the costs currently represented in the model.

## 8. Project inflow

Let:

- `E_t` = contract-value work in period t;
- `a` = client advance fraction;
- `r` = client retention fraction;
- `w` = client WIEB fraction;
- `p` = payment delay in periods; and
- `V` = contract value.

The client advance received at the beginning of the model is:

```text
advance_receipt = a * V
```

### WIEB / billed work

WIEB applies from the **first** work period:

```text
B_0 = E_0 * (1 - w)

B_t = E_t * (1 - w) + E_(t-1) * w

final_carry = E_last * w
```

### Progress receipts

Advance recovery and retention are deducted from progress receipts:

```text
progress_receipt_t = B_t * (1 - a - r)
```

The progress receipt is then shifted by exactly `p` periods.

The calculation requires:

```text
0 <= a <= 1
0 <= r <= 1
a + r <= 1
```

The final condition prevents negative progress receipts.

### Retention releases

Total client retention is:

```text
retention_value = r * V
```

If `e` is `release_retention_eop`:

```text
first_retention_release  = retention_value * e
second_retention_release = retention_value * (1 - e)
```

The first portion is added at the end of the progress-payment sequence, including any final WIEB carry period. The second portion is released according to the DLP convention:

- DLP 0: same period as the first portion;
- DLP 1: one period later;
- DLP N: exactly N periods later.

### Invariant

For valid parameters and normal floating-point precision:

```text
sum(project inflow) = contract value
```

Advance, retention, WIEB, payment delay, and DLP redistribute the timing of contract receipts; they do not create additional contract value.

## 9. Project outflow

Project outflow is the sum of the current calculated activity outflows in each period:

```text
project_outflow_t = sum(activity_outflow_i,t)
```

Deleted activities are excluded. The calculator recomputes active activity cash flows rather than trusting old cached activity cash-flow JSON.

## 10. Net cash flow and financing

For each period:

```text
net_cash_flow_t = inflow_t - outflow_t
```

The engine then maintains a cumulative cash balance.

Let `balance_(t-1)` be the previous period's financed balance and `i` the financing interest rate per model period:

```text
pre_finance_balance_t = balance_(t-1) + net_cash_flow_t
```

If the balance is negative:

```text
balance_t = pre_finance_balance_t * (1 + i)
```

Otherwise:

```text
balance_t = pre_finance_balance_t
```

The current engine therefore applies financing cost only when the cumulative balance is negative. It does not earn interest on a positive cash balance.

The API currently exposes this cumulative financed balance under the legacy key `outflow_with_interest`. That key should be understood as **cumulative cash balance after financing**, not as a marginal outflow series.

## 11. Validation rules that affect calculations

The backend is authoritative for model validity.

Project/cash-flow inputs require:

- contract value: finite and non-negative;
- advance, retention, retention-release fraction, and WIEB: each between 0 and 1;
- advance + retention: not greater than 1;
- interest rate: finite and non-negative;
- DLP and payment delay: non-negative integers.

Activity inputs require:

- cost: finite and greater than zero;
- duration: integer greater than zero;
- skew: greater than -1 and less than 1;
- start, DLP, payment delay, pre-work period, and no-billing period: non-negative integers;
- fraction fields: each between 0 and 1; and
- advance + retention: not greater than 1.

Client applications should mirror these validations so users see errors before submitting data, but backend validation remains authoritative.

## 12. Current backend defaults

Defaults are starting assumptions, not universal construction rules.

### Cash-flow scenario defaults

| Parameter | Backend default |
| --- | ---: |
| Client advance | 10% |
| Client retention | 10% |
| Retention released at first/EOP release | 50% |
| DLP | 12 periods |
| Client payment delay | 1 period |
| Financing rate | 0.5% per period |
| Client WIEB | 20% |
| Contract value | 0 |

Activity-type presets may supply different activity assumptions in the client. Those presets are heuristics intended to speed up modelling, not statements that all projects or trades use those conditions.

## 13. Legacy and currently unused activity fields

Several activity fields remain in the data model for compatibility but are not part of the current activity cash-flow calculation:

- `mobilization` — percentage amount; the engine currently uses `mobilization_period` only as a pre-work/no-work period;
- `profit` — not used by the current engine;
- `subcontractors_retention` — deprecated; use `retention`;
- activity `interest_rate` — deprecated; financing is calculated at project/cash-flow level; and
- `compounding_period` — deprecated.

These fields must not be treated as active calculation drivers by future clients or AI generators unless the model is deliberately changed and documented.

## 14. Naming guidance for clients and future AI schemas

User-facing and AI-facing names should describe both the meaning and the direction of a variable.

Preferred terms include:

| Legacy/backend name | Preferred semantic name |
| --- | --- |
| `Cashflow.advance` | Client advance payment |
| `Cashflow.retention` | Client retention |
| `Cashflow.duration_for_payment` | Client payment delay |
| `Cashflow.wieb` | Client billing deferral / WIEB |
| `Activity.cost` | Estimated activity cost |
| `Activity.subcontracted` | Subcontracted share |
| `Activity.advance` | Subcontract advance |
| `Activity.retention` | Subcontract retention |
| `Activity.duration_for_payment` | Subcontract payment delay |
| `Activity.work_in_excess` | Subcontract billing deferral / WIEB |
| `Activity.mobilization_period` | Pre-work / no-work period |
| API `workflow` | Cost-loaded work / planned cost flow |
| API `netflow` | Net cash flow |
| API `outflow_with_interest` | Cumulative cash balance after financing |

Abbreviations such as WIEB and DLP should be expanded in the UI at first use and in any AI schema description.

### Activity type warning

The current backend uses the `activity_type` field for activity/trade categorization, while the calculation engine also treats the exact value `"linear"` as the switch for a linear work curve and treats other values as non-linear/S-curve work.

Before an AI generator becomes authoritative, activity/trade category and work-distribution type should be represented as separate semantic concepts, even if compatibility requires the current database field to remain temporarily.

## 15. What the model intentionally does not calculate

CashFlowPot does not currently calculate:

- critical path or schedule logic;
- delay entitlement or extension-of-time entitlement;
- resource availability or productivity;
- labour, plant, material, or equipment quantities;
- detailed BOQ measurement or earned-value measurement;
- tax, currency, escalation, bonds, or other commercial mechanisms unless represented indirectly in the entered cost/value assumptions;
- individual activity selling values or activity-specific markup; or
- accounting statements.

Those may influence the assumptions entered into CashFlowPot, but they are outside this calculation model.

## 16. Calculation invariants for tests

Changes to the calculation engine should preserve or deliberately revise the following invariants with explicit regression tests:

1. Corrected marginal work sums to the activity estimated cost.
2. Total activity outflow sums to the activity estimated cost.
3. Total project inflow sums to the contract value for valid terms.
4. WIEB shifts timing only and applies from the first billing period.
5. A payment delay of N shifts progress cash exactly N periods, independent of advance payment.
6. DLP 0 releases remaining retention in the same end period; DLP N releases it exactly N periods later.
7. Advance + retention cannot exceed 100% at either project or activity/subcontract level.
8. Deleted activities do not contribute to project work or outflow.
9. Positive skew front-loads the current sigmoid work curve relative to the balanced curve; negative skew back-loads it.

If a future model intentionally changes one of these rules, update the tests and this document together.
