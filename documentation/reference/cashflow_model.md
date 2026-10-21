# CashflowPot calculation model

This document is the canonical technical reference for the current CashflowPot financial model implemented in `q_flow`.

It defines model direction, formulas, timing conventions, defaults, validation rules, compatibility behavior, financing semantics, summary metrics, and invariants that should remain consistent across the backend, Flutter client, exports, tests, public explanations, and future AI-assisted setup.

For the shorter product explanation, see [`../product.md`](../product.md).

## 1. Purpose

CashflowPot turns project execution, project costs, contract/commercial terms, financing facilities, and forecasting assumptions into a time-phased construction cash-flow forecast.

The model answers:

> Given the execution and project costs we currently expect, the contract/commercial terms we know, and the financing/forecast assumptions we are using, how much cash is expected to go out, how much is expected to come in, when, and what funding gap could result?

The result is a **forecast, not a guarantee**.

## 2. Model hierarchy

A QAuth Unit represents one CashflowPot Project. A Project can contain multiple independent `Cashflow` scenarios, and each scenario contains Activities.

```text
QAuth Unit / Project
  └── Cashflow scenario
        └── Activities
              ├── Work
              └── Scheduled Cost
```

A scenario owns its contract value, client terms, financing assumptions/facilities, inflow method, and Activities.

Activities own execution/project-cost timing. Work Activities can also own subcontract-side assumptions.

## 3. Time convention

The engine works in integer **model periods**.

The app is normally used monthly and `Activity.duration_units` defaults to `Months`, but the calculation engine itself works on periods rather than calendar dates. Within one scenario, timing inputs must use one consistent period convention.

Backend timing/index examples:

```text
duration = 6               six local Activity periods
duration_for_payment = 2   payment occurs two periods after billing
dlp = 12                   second retention release is twelve periods after first release
start = 3                   Activity local period 1 begins after three project periods
```

Backend offsets/indexes are zero-based where required by the data model. **User-facing periods are 1-based** (`P1`, `P2`, ...).

The scenario **work duration** is derived only from Work Activity work series. The financial horizon can extend beyond work duration because Scheduled Cost, WIEB carry, payment delay, retention releases, subcontract payment timing, DLP, and financing facilities may occur later.

## 4. Direction of the model

CashflowPot separates:

1. **project execution / project cost / outflow**;
2. **main-contract value / client inflow**; and
3. **financing facilities / funded cash position**.

Work Activities create physical/cost-loaded work and project outflow. Scheduled Cost Activities create project cost/outflow but no physical or billable work.

The main-contract value profile can be generated independently from Work Activity shape or linked to the combined Work Activity profile.

Client-side contract terms are applied only after the contract-value work profile has been generated.

Financing facilities are applied after project inflow/outflow is known; facility draws do not create project value or project cost.

## 5. Activity source model

Activity category and calculation behavior are separate concepts.

### Activity type

`Activity.activity_type`

A creation-time template/category such as General, Structure, MEP or Facade. A template may suggest assumptions, skew, and a distribution, but `activity_type` does not control calculation after the Activity has been saved.

### Activity mode

`Activity.activity_mode`

Valid values:

```text
work
scheduled_cost
```

Null/missing mode on a legacy row is interpreted as `work`.

### Distribution type

`Activity.distribution_type`

Valid values for Work Activities:

```text
s_curve
linear
manual
```

Null/missing distribution on a legacy row is interpreted as `linear` only when legacy `activity_type` equals `linear` case-insensitively; otherwise it is `s_curve`.

Scheduled Cost is always treated as manual scheduled cost regardless of an older stored distribution value.

### Cost schedule

`Activity.cost_schedule_json`

A dense Activity-local list of marginal amounts. Example:

```json
[200, 0, 500, 300]
```

`start` remains a separate project offset.

For Manual Work and Scheduled Cost:

```text
cost     = sum(cost_schedule_json)
duration = len(cost_schedule_json)
```

Those two values are server-authoritative and are normalized from the schedule.

The Flutter Scheduled Cost editor may accept **absolute project-period pairs** and convert them into the backend `start` offset plus dense local schedule. That UI representation does not change the backend source format.

## 6. Core commercial terminology

### Contract value

`Cashflow.contract_value`

The total client contract value represented by the scenario.

### Estimated Activity cost

`Activity.cost`

For generated Work Activities this is the entered estimated contractor cost used to cost-load the generated curve.

For Manual Work and Scheduled Cost it is derived from the dense schedule total.

The model does not require or infer individual Activity selling values or Activity-specific markup.

### Advance

At scenario level, `Cashflow.advance` is the client advance received by the contractor.

At Work Activity level, `Activity.advance` is the advance paid on the subcontracted share. Advance is recovered proportionally from later progress cash.

Scheduled Cost does not apply Activity advance logic.

### Retention

At both client and Work Activity subcontract level, retention is withheld from progress cash and released later.

`release_retention_eop` is the fraction of total retention released at the first/end-of-progress release point. The remainder is released after the DLP.

Scheduled Cost does not apply Activity retention logic.

### Defects Liability Period (DLP)

The number of model periods between the first retention release and the remaining retention release.

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

Work Activity field: `Activity.work_in_excess`.

CashflowPot stores a percentage forecasting assumption: the estimated share of completed work that is not billed in the current period and is carried into the following billing period.

WIEB changes **timing**, not lifetime value.

At scenario level it applies to client-side contract-value work. At Work Activity level it applies only to the subcontracted share. Self-performed/direct cost is paid as incurred. Scheduled Cost does not use WIEB.

### Subcontracted share

`Activity.subcontracted`

For Work Activities this is the fraction of Activity cost treated as subcontracted/supplied and therefore subject to Activity subcontract terms. The remainder is self-performed/direct cost.

Scheduled Cost is direct scheduled project cost and is not classified as subcontracted work by the canonical summary.

### Pre-work period

Backend field: `Activity.mobilization_period`.

Despite its legacy name, this field is an initial no-work/pre-work period. For Work Activities the engine prepends zero-cost work periods before the base work series.

There is no longer a separate active `Activity.mobilization` percentage input.

### No-billing period

`Activity.no_billing_period`

An initial Work Activity subcontract billing window during which work accumulates before the first subcontract bill.

### Activity start

`Activity.start`

The number of project periods before the Activity-local series begins. It shifts Work Activity work/outflow and Scheduled Cost outflow into project time.

### Skew

`Activity.skew` and, for the independent S-curve, `Cashflow.inflow_curve_skew`.

Valid skew is strictly inside `(-1, 1)`.

With the current curve implementation:

- negative values back-load the curve;
- zero is the balanced reference; and
- positive values front-load the curve.

Skew has no calculation effect for Linear or Manual Work distributions.

## 7. Work Activity base distribution

A Work Activity obtains one base marginal work series by exactly one of three methods.

### Generated S-curve

For duration `d`, skew `s`, estimated cost `c`, and time `t`, the raw cumulative curve is:

```text
C_raw(t) = c * (s + 1) / ((s + 1) + exp(-(t / (0.1*d) + s^2 - 5)))
```

Marginal work is obtained from differences between consecutive cumulative values.

The raw sigmoid does not necessarily end exactly at `c`. The engine calculates:

```text
error = c - sum(raw marginal work)
```

and applies the cubic cumulative correction:

```text
error_distribution(t)
    = -2 * error * t^3 / d^3
      + 3 * error * t^2 / d^2
```

The corrected cumulative curve is differenced again to produce final marginal work.

### Generated Linear

```text
C_linear(t) = c / d * t
```

The same marginal/error-correction mechanism returns the series to the Activity cost.

### Manual Work

```text
base_marginal_work = cost_schedule_json
```

The dense schedule replaces only the generated curve. From that point onward, the existing Work Activity pipeline remains unchanged.

### Pre-work and start

After the base Work series is obtained, `mobilization_period` prepends zero-work periods. `start` is applied later when the Activity-local calculated result is shifted into project time.

For valid Work Activities:

```text
sum(activity marginal work) = activity estimated cost
```

## 8. Work Activity outflow

For Work Activity marginal work `W_t` and subcontracted fraction `q`:

```text
self_performed_cost_t = W_t * (1 - q)
subcontracted_work_t  = W_t * q
```

Self-performed/direct cost is paid in the same period as Activity work.

The subcontracted share follows subcontract terms.

### Subcontract billing and WIEB

The no-billing period is applied first. Work within that initial window accumulates into the first subcontract bill.

For billable subcontract work `S_t` and subcontract WIEB assumption `w`:

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

The progress-payment series is shifted by `Activity.duration_for_payment` periods.

The subcontract advance at the start of the Activity/subcontract timeline is:

```text
subcontract_advance_payment
    = activity_cost * subcontracted_share * subcontract_advance
```

Total subcontract retention is:

```text
subcontract_retention_value
    = activity_cost * subcontracted_share * subcontract_retention
```

Total Work Activity outflow is:

```text
activity_outflow_t
    = self_performed_cost_t + subcontractor_payment_t
```

For valid Work Activities:

```text
sum(activity outflow) = activity estimated cost
```

Advance, retention, WIEB, no-billing period, payment period, and DLP change **when** subcontracted cost is paid; they do not change total estimated cost.

## 9. Scheduled Cost Activity

A Scheduled Cost Activity represents project cost/outflow that is not physical/billable work.

Its local calculated series are:

```text
marginal_work     = zeros(len(cost_schedule_json))
marginal_out_flow = cost_schedule_json
```

`start` shifts both calculated arrays into project time. The zero work array exists only to keep the common Activity calculated-output shape; Scheduled Cost is excluded from project work aggregation.

Activity subcontract assumptions, pre-work, WIEB, advance, retention, payment delay and DLP do not transform Scheduled Cost outflow.

For valid Scheduled Cost:

```text
sum(activity outflow) = activity estimated cost
sum(activity work)    = 0
```

## 10. Common Activity calculated output

`cash_flow_json` is calculated/server-owned compatibility/cache output. Every Activity mode exposes:

```json
{
  "marginal_work": [],
  "marginal_out_flow": []
}
```

`cost_schedule_json` is source input; `cash_flow_json` is calculated output. Portable input must not use cached `cash_flow_json` as authoritative source data.

## 11. Project execution work and duration

Project cost-loaded workflow is the period-by-period sum of **Work Activities only**:

```text
project_cost_work_t = sum(work_activity_work_i,t)
```

Let:

```text
C_work = sum(project_cost_work_t)
```

Scheduled Cost is not included in `project_cost_work_t` or `C_work`.

The API returns the Work Activity series under the legacy key:

```text
workflow
```

Execution/work duration is:

```text
execution_duration = max(length of active Work Activity work series)
```

A Scheduled Cost after the final Work Activity may extend project outflow and financial horizon but does not extend work duration.

A scenario may therefore have project outflow while `workflow = []` and `duration = 0`.

## 12. Main-contract inflow method selection

Backend fields:

```text
Cashflow.use_independent_inflow_curve
Cashflow.inflow_curve_type
Cashflow.inflow_curve_skew
```

Independent contract curve is selected only when:

```text
use_independent_inflow_curve is True
and
inflow_curve_type is not NULL
```

Otherwise the engine uses Activity-linked inflow.

A null `inflow_curve_skew` is treated as balanced `0.0` and does not disable Independent mode.

Valid non-null `inflow_curve_type` values are:

```text
s_curve
linear
```

## 13. Independent contract curve

This is the default for new scenarios.

The contract-value curve uses:

```text
duration = Work Activity execution_duration
value    = contract_value
curve    = inflow_curve_type
skew     = inflow_curve_skew, with NULL interpreted as 0.0
```

For a Linear curve, contract value is distributed evenly over Work duration. For an S-curve, the same `Work` mathematics and error correction are used so total contract-value work returns to contract value.

Scheduled Cost does not allocate main-contract value and does not extend this independent curve.

## 14. Activity-linked inflow

This is the alternative/compatibility method.

For contract value `V` and total Work Activity cost `C_work`:

```text
value_factor = V / C_work
contract_value_work_t = project_cost_work_t * value_factor
```

Therefore, when `C_work > 0`:

```text
sum(contract_value_work) = contract value
```

Scheduled Cost is excluded from both `C_work` and `project_cost_work_t`. It affects project cost/outflow but does not create client PPC/billed work.

The method still does not assign individual selling values or markup to Activities.

## 15. Project inflow

The selected method first produces contract-value work `E_t`.

Let:

- `a` = client advance fraction;
- `r` = client retention fraction;
- `w` = client WIEB assumption;
- `p` = client payment period; and
- `V` = contract value.

Client advance at period zero is:

```text
advance_receipt = a * V
```

### Client WIEB

```text
B_0 = E_0 * (1 - w)
B_t = E_t * (1 - w) + E_(t-1) * w
final_carry = E_last * w
```

### Progress receipts

```text
progress_receipt_t = B_t * (1 - a - r)
```

Progress receipt is shifted by exactly `p` periods.

### Client retention

```text
retention_value = r * V
first_retention_release  = retention_value * release_retention_eop
second_retention_release = retention_value * (1 - release_retention_eop)
```

The remaining portion is released exactly according to the DLP convention.

For a valid scenario with Work Activity execution:

```text
sum(project inflow) = contract value
```

Client advance, retention, WIEB, payment period and DLP redistribute timing; they do not create or remove contract value.

### PPC supporting series

The financing engine also uses two derived client-progress series:

```text
ppc_issued
```

Net PPC certificate values in issue periods, before project payment delay.

```text
ppc_base
```

Client PPC cash receipts after payment timing, excluding client advance and retention releases.

PPC Discount draw requests use `ppc_issued`; percent-of-PPC repayment uses `ppc_base`.

## 16. Project outflow

Project outflow is the period-by-period sum of **all** current Activity outflows:

```text
project_outflow_t = sum(activity_outflow_i,t)
```

This includes Work Activity outflow and Scheduled Cost outflow. Deleted Activities are excluded.

Changing Independent/Activity-linked inflow settings does not change Activity outflow.

## 17. Net cash before explicit facilities

For each model period:

```text
project_net_cash_flow_t = inflow_t - outflow_t
```

Without explicit financing facilities, the legacy scenario financing assumption applies financing cost only when cumulative cash is negative:

```text
pre_finance_balance_t = balance_(t-1) + project_net_cash_flow_t

if pre_finance_balance_t < 0:
    balance_t = pre_finance_balance_t * (1 + interest_rate)
else:
    balance_t = pre_finance_balance_t
```

The API exposes this cumulative financed balance under the legacy key `outflow_with_interest`.

When explicit facilities are configured, the facility engine becomes the financing layer instead.

## 18. Financing facilities

Detailed rules are canonical in [`financing_facilities.md`](financing_facilities.md). The key calculation semantics are summarized here.

### Draw methods

```text
automatic_shortfall
scheduled
ppc_base
```

### Repayment methods

```text
cashflow_sweep
percent_of_ppc
equal_installments
scheduled
```

### Capacity

For a finite limit `L`:

```text
revolving available capacity
= L - current outstanding principal

non-revolving available capacity
= L - cumulative actual draws
```

Blank limit means unlimited.

### Scheduled draw

```text
actual_draw_t = min(requested_draw_t, available_capacity_t)
```

Unavailable requested draw has no cashflow effect and is not carried forward.

### Opening-principal interest

```text
interest_t = opening_outstanding_t * facility_interest_rate
```

A new draw begins accruing interest in the following period.

### Scheduled-draw automatic repayment cap

For a scheduled-draw facility using `% PPC` or cashflow sweep:

```text
automatic_repayment_t <= opening_outstanding_t
```

so same-period scheduled principal is not automatically repaid immediately.

### Period order

The engine applies, in order:

1. project inflow/outflow;
2. interest on opening principal and applicable fees;
3. scheduled/PPC-linked draws;
4. contractual repayments;
5. cashflow sweeps;
6. automatic-shortfall facilities;
7. closing balances/capacity.

Facility start/end constrain draw availability, not debt maturity.

## 19. Funded cash position

For facility-enabled scenarios:

```text
Total inflow_t
= Project inflow_t + Facility draws_t

Total outflow_t
= Project outflow_t
  + Principal repayments_t
  + Facility interest_t
  + Facility fees_t

Funded net cash flow_t
= Total inflow_t - Total outflow_t

Closing cash balance_t
= Closing cash balance_(t-1) + Funded net cash flow_t
```

Facility outstanding principal is a **balance**, not an inflow or outflow.

The UI/export presentation groups these as:

```text
PROJECT CASHFLOW
FACILITIES
CASH POSITION
```

## 20. Current snapshot

Core calculated snapshot keys include:

```text
workflow
inflow
outflow
netflow
outflow_with_interest
duration
```

Facility-enabled snapshots additionally include:

```text
facility_rows
facility_inflow
facility_outflow
facility_interest
facility_fees
funded_netflow
pre_financing_balance
unfunded_shortfall
```

Semantics:

- `workflow` — Work Activity cost-loaded execution only;
- `inflow` — client/project cash receipts;
- `outflow` — all Activity project cost/payments;
- `netflow` — pre-facility project net cash;
- `facility_inflow` — actual facility draws;
- `facility_outflow` — principal repayments;
- `funded_netflow` — net cash including facility flows/cost;
- `outflow_with_interest` — closing funded cash balance despite the legacy name;
- `duration` — Work duration, not financial horizon.

Each `facility_rows` item exposes:

```text
id
name
type
draw_method
repayment_method
draw[]
repayment[]
interest[]
fees[]
outstanding[]
available_limit[]
```

## 21. Canonical summary / KPIs

The backend summary includes:

```text
total_inflow
work_cost
scheduled_cost
subcontracted_cost
self_performed_cost
direct_cost
financing_cost
total_cost
total_facility_interest
total_facility_fees
minimum_pre_financing_balance
minimum_pre_financing_period
peak_pre_financing_need
peak_pre_financing_period
peak_facility_outstanding
final_facility_outstanding
final_cash_balance
cash_after_debt_settlement
work_duration
dlp
financial_horizon
```

When facilities are configured it can also include:

```text
contractor_contribution
peak_unfunded_shortfall
```

Definitions:

```text
Project cost = direct_cost = work_cost + scheduled_cost
Financing cost = total_facility_interest + total_facility_fees
Total cost = direct_cost + financing_cost
Cash after debt settlement = final_cash_balance - final_facility_outstanding
Peak funding requirement = max(0, -minimum_pre_financing_balance)
```

`cash_after_debt_settlement` is a principal-only settlement view. It does not invent future interest/maturity beyond the modeled horizon.

Backend period indexes are zero-based. UI/export period labels for users are 1-based.

## 22. Precision and authoritative totals

`CashflowCalculator` rounds serialized period arrays for practical API/display compatibility.

That rounding must not redefine source totals.

Canonical totals should use authoritative source/summary values where available rather than summing visibly rounded period values.

Examples:

- Activity total = authoritative Activity `cost`;
- Project cost = authoritative Work + Scheduled Cost totals;
- Project inflow total = backend summary total;
- facility totals = sums of the authoritative calculated facility series.

This prevents drift such as twelve displayed `833.33` periods producing `9,999.96` for an Activity whose authoritative cost is `10,000.00`.

Excel keeps financial cells numeric and uses number formats separately from underlying values.

## 23. Backend validation

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
- financing facility payloads: validated for supported methods and method-specific values.

### Activity inputs

For every Activity:

- effective `activity_mode`: `work` or `scheduled_cost`;
- effective `distribution_type`: `s_curve`, `linear`, or `manual`;
- `start`, `dlp`, `duration_for_payment`, `mobilization_period`, `no_billing_period`: non-negative integers;
- `advance`, `retention`, `release_retention_eop`, `work_in_excess`, `subcontracted`: each in `[0, 1]`;
- `advance + retention <= 1`;
- `skew`: finite and strictly inside `(-1, 1)`.

Generated Work (`s_curve` or `linear`):

- `cost`: finite and greater than zero;
- `duration`: integer greater than zero;
- schedule may be null/empty.

Manual Work and Scheduled Cost:

- `cost_schedule_json`: non-empty dense list;
- every schedule value: finite, numeric, non-boolean and non-negative;
- schedule total > 0;
- backend derives `cost` and `duration` from the schedule.

Clients mirror useful validation for UX, but backend rules remain authoritative.

## 24. Current backend defaults

### Cashflow scenario defaults

| Parameter | Backend default |
| --- | ---: |
| Client advance | 10% |
| Client retention | 10% |
| Retention released at first release | 50% |
| DLP | 12 periods |
| Client payment period | 1 period |
| Legacy financing rate | 0.5% per period |
| Client WIEB assumption | 20% |
| Contract value | 0 |
| Use Independent inflow curve | `true` |
| Inflow curve type | `s_curve` |
| Inflow curve skew | `0.0` |
| Financing facilities | empty list |

### Activity model defaults

| Parameter | Backend model default |
| --- | ---: |
| Activity type | `General` |
| Activity mode | `work` |
| Distribution type | `s_curve` (legacy direct `activity_type=linear` infers `linear`) |
| Cost schedule | `null` |
| Cost | `0.0` (generated Work creation validation requires `> 0`) |
| Duration unit | `Months` |
| Duration | 4 periods |
| Start | 0 |
| Subcontract advance | 10% |
| Subcontract retention | 10% |
| Retention released at first release | 50% |
| DLP | 0 |
| Subcontract payment period | 1 period |
| Subcontract WIEB assumption | 10% |
| Pre-work period (`mobilization_period`) | 0 periods |
| Subcontracted share | 70% |
| Skew | `0.0` |
| No-billing period | 0 |

Activity presets can provide different starting values and a distribution suggestion. Facility presets likewise provide editable starting values. Presets are input helpers, not immutable calculation identity.

## 25. Removed legacy Activity inputs

These fields are no longer part of the active Activity ORM/API/Flutter source model:

- `mobilization` percentage;
- `profit`;
- `subcontractors_retention`;
- Activity-level `interest_rate`;
- `compounding_period`.

Existing upgraded database installations may physically retain old nullable columns because the Activity-mode schema upgrade is intentionally non-destructive. The active ORM no longer maps or emits them.

`mobilization_period` remains active as the pre-work/no-work period.

## 26. Semantic naming guidance

| Backend/API name | Preferred semantic meaning |
| --- | --- |
| `Cashflow.advance` | Client advance payment |
| `Cashflow.retention` | Client retention |
| `Cashflow.duration_for_payment` | Client payment period |
| `Cashflow.wieb` | Client WIEB assumption (%) |
| `Cashflow.use_independent_inflow_curve` | Inflow forecast method |
| `Cashflow.inflow_curve_type` | Contract value curve type |
| `Cashflow.inflow_curve_skew` | Contract value curve timing/skew |
| `Activity.activity_type` | Activity template/category |
| `Activity.activity_mode` | Work vs Scheduled Cost |
| `Activity.distribution_type` | S-curve / Linear / Manual Work distribution |
| `Activity.cost_schedule_json` | Dense Activity-local manual/scheduled source |
| `Activity.cost` | Estimated Activity cost |
| `Activity.subcontracted` | Subcontracted share of Work Activity |
| `Activity.advance` | Subcontract advance |
| `Activity.retention` | Subcontract retention |
| `Activity.duration_for_payment` | Subcontract payment period |
| `Activity.work_in_excess` | Subcontract WIEB assumption (%) |
| `Activity.mobilization_period` | Pre-work period |
| API `workflow` | Cost-loaded Work Activity execution profile |
| API `inflow` | Project inflow / Client PPC receipts |
| API `outflow` | Project cost/payments |
| API `netflow` | Project net cash before facilities |
| API `funded_netflow` | Net cash including facilities |
| API `outflow_with_interest` | Closing funded cash balance |

User-facing text should expand WIEB and DLP at first use.

## 27. Current calculation boundaries

The engine does not currently calculate:

- critical path or schedule logic;
- delay/EOT entitlement;
- labour/plant/material productivity or resource availability;
- detailed BOQ measurement or earned-value measurement;
- tax, currency, escalation, bonds, and similar mechanisms unless represented indirectly in entered values/costs;
- individual Activity selling values or Activity-specific markup;
- detailed Schedule of Values;
- accounting statements;
- automatic linking of LC draws to Scheduled Cost purchases;
- facility maturity beyond modeled inputs; or
- future interest beyond the modeled horizon.

Those may influence scenario inputs, but are outside the current calculation engine.

## 28. Regression invariants

Calculation changes should preserve or deliberately revise these invariants with tests and documentation together:

1. Generated or Manual Work marginal Activity work sums to Work Activity estimated cost.
2. Total Work Activity outflow sums to Work Activity estimated cost for valid inputs.
3. Scheduled Cost outflow sums to its derived Activity cost and its project-work contribution is zero.
4. Project `workflow` and Work duration use Work Activities only.
5. Project outflow includes both Work and Scheduled Cost Activities.
6. Activity-linked contract value uses `contract_value / Work Activity cost`; Scheduled Cost does not create billed work.
7. Independent contract work uses Work Activity-derived execution duration only.
8. Project inflow sums to contract value for valid client terms when Work Activities provide execution duration.
9. Independent inflow is selected only when `use_independent_inflow_curve is True` and `inflow_curve_type is not NULL`.
10. Null Independent skew means balanced `0.0`; it does not disable Independent mode.
11. Changing inflow method does not change Activity outflow.
12. WIEB applies from the first billing period and shifts timing only.
13. Payment period `N` shifts progress cash exactly `N` periods.
14. DLP `0` releases remaining retention in the same end period; DLP `N` releases it exactly `N` periods later.
15. Advance plus retention cannot exceed 100% at client or Work Activity subcontract level.
16. Deleted Activities do not contribute to current project work/outflow.
17. Positive current skew front-loads an S-curve relative to balanced; negative skew back-loads it.
18. A scenario with Scheduled Cost but no Work may still return outflow/net cash with `workflow=[]` and Work duration `0`.
19. Legacy rows/files without new Activity fields remain Work Activities; legacy `activity_type=linear` remains linear.
20. `cash_flow_json` keeps the same `marginal_work` / `marginal_out_flow` shape for generated Work, Manual Work and Scheduled Cost.
21. Scheduled facility draws are capped by capacity; unavailable requested draw has no cashflow effect and is not carried forward.
22. Revolving repayment restores capacity; non-revolving repayment does not restore cumulative draw capacity.
23. Scheduled same-period draw is not automatically repayable through `% PPC` or sweep beyond opening principal.
24. Facility interest is charged on opening principal.
25. Canonical Activity/project totals must not drift because displayed period values are rounded.
26. User-facing period labels are 1-based while backend indexes/offsets remain compatible with the existing schema.

If a future change intentionally revises one of these rules, update implementation, tests, this reference, and affected overview/UI documentation in the same change.

Last reviewed against current `q_flow` implementation: 14 October 2026.
