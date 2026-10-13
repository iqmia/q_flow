# CashflowPot Financing Closeout and Cashflow Presentation Design

Date: 2026-10-13
Status: Proposed for implementation after user approval
Applies to: q_flow backend and CashflowPot Flutter frontend
Builds on: 2026-10-13 activity-modes-scheduled-cost design

## 1. Purpose

Close the current activity/facility modeling chapter by making four related behaviors coherent:

1. Scheduled Cost entry should be simple and should not expose irrelevant Work controls.
2. Scheduled/revolving financing facilities should have well-defined draw-capacity and repayment timing rules.
3. The cashflow table should separate project economics from financing mechanics before reconciling them into the final cash position.
4. Large values should remain readable in countries where nominal currency values can be large, without sacrificing too much precision.

The target user should be able to distinguish clearly between:

- project work and project costs;
- financing inflows and financing outflows;
- principal outstanding versus cash balance;
- project funding need before financing versus the actual funded cash position.

## 2. Scheduled Cost UX

Scheduled Cost remains an Activity mode whose purpose is:

- contributes to project cost/outflow;
- does not contribute to Work, workflow, PPC, contract-value allocation, or Work duration.

Typical example:

- MEP Work = 300,000 as a normal Work Activity;
- MEP Materials = 100,000 as Scheduled Cost paid on specified project periods.

### 2.1 Absolute project periods

For Scheduled Cost, the user enters absolute project periods directly:

```text
4: 25000, 7: 75000
```

The UI does not show Start period for Scheduled Cost.

The frontend normalizes this for the existing backend representation:

```text
start = first entered project period - 1
cost_schedule_json = dense values from first entered period through last entered period
cost = sum(cost_schedule_json)
duration = len(cost_schedule_json)
```

Example:

```text
User input: 4: 25000, 7: 75000
Stored start: 3
Stored cost_schedule_json: [25000, 0, 0, 75000]
Derived cost: 100000
Derived duration: 4
```

The backend schema does not need to change for this UX improvement.

### 2.2 Derived fields

For Scheduled Cost:

- Estimated activity cost is read-only and visibly styled as calculated.
- Schedule duration is read-only and visibly styled as calculated.
- Both are derived from the normalized dense schedule.
- The UI should use a muted/calculated treatment rather than looking like disabled editable fields.

### 2.3 Distribution state

Scheduled Cost does not use Work distribution.

When switching from Work to Scheduled Cost:

- hide the Work distribution control;
- do not overwrite `distribution_type` just to make Scheduled Cost work;
- preserve the user's previous Work distribution selection in UI state/model state.

When switching back to Work, restore the prior Work distribution selection exactly, e.g. S-curve, Linear, or Manual.

For persistence, Scheduled Cost may still carry an ignored/default distribution value for compatibility, but UI toggling must not destroy the user's previous Work choice.

### 2.4 Manual Work remains different

Manual Work still uses an activity-local schedule plus Start period. Its entered periods are relative to the Activity, not absolute project periods.

## 3. Scheduled Facility Draw Semantics

A scheduled facility draw is a requested financing inflow schedule. It is not a project outflow and does not imply that a corresponding project purchase exists unless linking is added later.

For each scheduled draw period:

```text
requested draw = draw_schedule[period]
actual draw = min(requested draw, available facility capacity)
```

Only `actual draw` enters project cash as a facility inflow.

If requested draw exceeds capacity:

- the excess has no cashflow effect;
- it is not converted into project outflow;
- it is not carried forward automatically;
- it is not automatically drawn later.

The current `unfunded_draw` diagnostic is not required in the user-facing product. Unless another internal use is found, remove it from the returned facility rows/API payload rather than creating another frontend row for it.

## 4. Facility Limit and Revolving Behavior

The draw schedule and facility limit are independent concepts.

### 4.1 UI fields

For scheduled facilities show:

```text
Draw schedule          user input
Scheduled draws total  calculated display only
Facility limit         user input; blank means unlimited
Revolving facility     boolean
```

Do not calculate Facility Limit from the sum of scheduled draws.

### 4.2 Non-revolving facility

For non-revolving facilities:

```text
available capacity = limit - cumulative actual draws
```

Principal repayment does not restore drawing capacity.

Example:

```text
limit = 1000
actual draw = 500
repay = 300
available capacity remains 500
```

### 4.3 Revolving facility

For revolving facilities:

```text
available capacity = limit - current outstanding principal
```

Principal repayment restores capacity.

Example:

```text
limit = 1000
P1 draw 800 -> outstanding 800 -> available 200
P2 repay 500 -> outstanding 300 -> available 700
P4 requested draw 900 -> actual draw 700 -> outstanding 1000
```

A revolving scheduled facility may therefore have total scheduled draws much larger than its facility limit.

### 4.4 Availability window

`start` / First available period and `end` / Last available period apply to new drawings only.

Repayment, interest, fees, and outstanding principal may continue after the last available draw period.

The last available draw period is not interpreted as facility maturity.

## 5. Repayment Timing for Scheduled-Draw Facilities

For a facility with `draw_method = scheduled`, newly drawn principal in period `P` is not eligible for automatic repayment in the same period.

This applies to automatic repayment methods:

- `percent_of_ppc`
- `cashflow_sweep`

Repayment in period `P` may act only against principal that was outstanding at the opening of period `P`.

Therefore:

```text
repayable principal in P <= opening outstanding principal
```

A new draw in P first becomes repayable in P+1.

Example:

```text
P3 opening outstanding 0
P3 draw 500
P3 automatic repayment 0
P3 closing outstanding 500

P4 opening outstanding 500
P4 draw 300
P4 %PPC due 200
P4 repayment 200
P4 closing outstanding 600
```

The P4 repayment may repay P3 principal, but may not repay the P4 draw immediately.

### 5.1 Explicit repayment methods

Explicitly scheduled repayment remains user-controlled.

Equal installments remain controlled by their explicit first-installment period/interval/count settings and are not reinterpreted by the automatic one-period delay rule.

### 5.2 PPC Discount

PPC Discount remains its own product behavior and is not changed by this scheduled-LC rule unless its draw method is explicitly changed to scheduled in the future.

## 6. Cashflow Table Information Architecture

The current table mixes project economics, financing flows, and facility balances in one inflow/outflow/balance arrangement. Replace it with three visually distinct sections.

### 6.1 Project Cashflow

```text
PROJECT CASHFLOW
Project inflow / Client PPC
Project cost
```

Project cost includes Work Activity outflow and Scheduled Cost outflow.

The project section should not include facility draws, repayments, interest, fees, or outstanding principal.

### 6.2 Facilities Cashflow

Each facility is a compact grouped block:

```text
FACILITIES
F-001
  Draw
  Repayment
  Interest & fees
  Outstanding balance

LC - MEP Material
  Draw
  Repayment
  Interest & fees
  Outstanding balance

...
```

Facility Draw is financing inflow.
Facility Repayment and Interest & fees are financing outflow.
Outstanding balance is a balance row, not an inflow/outflow.

Do not expose `unfunded_draw` as a table row.

### 6.3 Overall Cash Position

```text
OVERALL CASH POSITION
Total inflow
Total outflow
Net cash flow
Closing cash balance
```

Definitions:

```text
Total inflow
= Project inflow + sum(actual facility draws)

Total outflow
= Project cost + facility principal repayments + facility interest + facility fees

Net cash flow
= Total inflow - Total outflow

Closing cash balance_t
= Closing cash balance_(t-1) + Net cash flow_t
```

This section is the reconciliation point between project and financing.

## 7. KPI Area

Place a compact KPI grid below the scenario header and above the detailed cashflow table.

Recommended KPI cards:

1. Project cost
   - Work + Scheduled Cost.
2. Financing cost
   - Interest + fees.
   - Small subtitle should show the two components separately.
3. Total cost
   - Project cost + financing cost.
4. Peak funding requirement
   - Most negative project/pre-financing cumulative cash position.
   - Show amount and period, e.g. `-250K · P21`.
5. Peak facility usage
   - Highest combined outstanding facility principal over the modeled horizon.
6. Outstanding facilities
   - Total final outstanding principal at the end of the modeled horizon.
7. Closing cash balance
   - Actual funded cash balance at the end of the modeled horizon.
8. Cash after debt settlement
   - Closing cash balance minus final outstanding facility principal.
   - This is principal settlement only; do not imply unmodeled future interest has been included.

Secondary compact metadata below or within the KPI area:

```text
Work duration: N periods · Financial horizon: M periods
```

Do not create oversized dashboard cards. The purpose is rapid decision support, not a marketing-style dashboard.

### 7.1 Responsive layout

Desktop: typically 4 cards per row.
Tablet: typically 3 cards per row.
Small screens/mobile viewing: 2 cards per row, or 3 only when the available width keeps labels readable.

Cards should use restrained, semantically appropriate icons and compact typography.

## 8. Compact Number Formatting

Introduce one shared presentation formatter for monetary/large numeric values in the app.

The design goal is to preserve precision for currencies where nominal values may be very large while keeping table cells compact.

### 8.1 Scaling rule

Base-unit values remain unscaled while their absolute value is at most `999,999.99`.

If the base-unit value exceeds that threshold, divide by 1,000 and append `K`.

Keep the K representation while its absolute scaled value is at most `999,999.99K`.

If the K representation exceeds that threshold, divide the original value by 1,000,000 and append `M`.

Conceptually:

```text
if abs(value) <= 999999.99:
    display base units
else if abs(value / 1000) <= 999999.99:
    display value / 1000 + "K"
else:
    display value / 1000000 + "M"
```

Examples:

```text
875.25           -> 875.25
250,780.25       -> 250,780.25
1,750,000.00     -> 1,750.00K
250,780,250.00   -> 250,780.25K
999,999,990.00   -> 999,999.99K
1,250,500,120.00 -> 1,250.50M
```

The visual width target is approximate rather than a hard character-count constraint; preserving this threshold/precision rule takes priority over forcing every value into exactly 10 characters.

### 8.2 Decimal and sign behavior

- Preserve up to two decimal places for money-style values.
- Keep negative signs.
- Use thousands separators.
- Avoid unnecessary trailing `.00` only where the existing visual style intentionally trims whole values; otherwise monetary rows may keep two decimals for alignment.
- The final formatter API should support the table/KPI context consistently rather than duplicating ad-hoc formatting functions.

### 8.3 Exact-value access

Where a compact K/M value is shown interactively, provide the exact underlying amount in a tooltip or equivalent hover detail.

### 8.4 Excel/export behavior

Do not convert numeric Excel cells to text such as `1.75M`.

Exports must retain real numeric cell values. Presentation formatting in Flutter does not change calculation precision or exported values.

## 9. Backend KPI / Snapshot Data

Prefer calculating canonical financial metrics in the backend snapshot/summary so Flutter does not need to reimplement financial logic.

Add or expose enough summary data to support:

- project cost;
- total facility interest;
- total facility fees;
- financing cost;
- total cost;
- minimum pre-financing cumulative balance and its period;
- peak combined facility outstanding;
- final combined facility outstanding;
- final funded/closing cash balance;
- cash after outstanding-principal settlement;
- Work duration;
- financial horizon.

Naming should clearly distinguish balances from period flows.

## 10. Frontend Presentation Rules

- Use grouped section headers for Project Cashflow, Facilities, and Overall Cash Position.
- Use two-line facility labels where helpful: facility name first, row name second.
- Keep row height compact.
- Facility outstanding belongs inside each facility group rather than in a disconnected balance block at the bottom.
- Use semantic icons only in KPI cards/controls, not in every grid row.
- Preserve horizontal usability for long scenarios.
- Small-screen presentation must remain viewable even though desktop is the primary design target.

## 11. Compatibility

- Existing facility JSON remains valid.
- No new database migration is required for the Scheduled Cost absolute-period UX.
- Facility limit semantics change only in frontend behavior for scheduled facilities; backend `limit` already supports independent limit and revolving/non-revolving capacity logic.
- Existing non-revolving and automatic-shortfall facility behavior should remain unchanged except where the agreed scheduled-draw repayment timing rule applies.
- Existing project/Activity calculations must remain unchanged outside the specified Scheduled Cost UI normalization and facility repayment timing changes.

## 12. Out of Scope

The following remain future work:

- linking an LC draw schedule to a specific Scheduled Cost Activity;
- automatic synchronization between purchase outflow and facility draw;
- facility maturity logic beyond existing explicit schedules/settings;
- carrying an unavailable scheduled draw into future periods;
- adding user-facing `unfunded_draw` reporting;
- new accounting statements or lender covenant analysis.

## 13. Acceptance Criteria

Backend:

1. Scheduled-draw facility actual inflow is capped by available capacity.
2. Excess requested draw has no downstream cashflow effect and is not carried forward.
3. Non-revolving capacity uses cumulative actual draws.
4. Revolving capacity uses current outstanding principal and repayments restore capacity.
5. Scheduled facility `% PPC` repayment cannot repay principal drawn in the same period.
6. Scheduled facility sweep cannot repay principal drawn in the same period.
7. Older outstanding principal can still be repaid in a period that also contains a new draw.
8. Explicit scheduled repayments remain unchanged.
9. PPC Discount existing behavior remains unchanged.
10. Summary metrics expose the agreed KPI values and period for peak funding requirement.
11. `unfunded_draw` is removed from user-facing returned facility rows if it has no other required consumer.

Flutter:

12. Scheduled Cost hides Start period and Work distribution.
13. Scheduled Cost accepts absolute project-period schedule entry.
14. Scheduled Cost normalizes absolute schedule into backend start + dense local list.
15. Cost and duration are visibly derived/read-only.
16. Switching Work -> Scheduled Cost -> Work restores the previous Work distribution selection.
17. Scheduled facility limit is editable/optional and no longer auto-equals scheduled draw total.
18. Scheduled draw total is shown separately as a calculated value.
19. Cashflow table is grouped into Project Cashflow, Facilities, and Overall Cash Position.
20. Each facility block shows Draw, Repayment, Interest & fees, Outstanding balance.
21. KPI grid shows the agreed metrics with compact responsive cards.
22. Mobile/small screen uses compact wrapping, normally two KPI cards per row.
23. Shared number formatter follows the 999,999.99 base/K/M scaling thresholds.
24. Exact values remain available via tooltip where compact values are shown.
25. Excel/exported numeric values remain numeric and unscaled.

## 14. Testing

Backend tests should cover facility draw-capacity semantics, revolving restoration, same-period repayment prevention, KPI summary calculations, and regression behavior for existing facility types.

Flutter tests should cover Scheduled Cost mode toggling/normalization, scheduled facility editor behavior, grouped cashflow sections, KPI responsiveness, formatter thresholds/signs/tooltips, and existing scenario-header/table regressions.
