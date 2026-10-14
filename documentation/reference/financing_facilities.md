# Financing Facilities Reference

Last reviewed: 14 October 2026

This reference describes how CashflowPot financing facilities interact with project cashflow. Project Activities create project inflow/outflow. Facilities sit on top of that project cashflow and create financing inflows, principal repayments, interest, fees, and outstanding balances.

## 1. Core separation

CashflowPot keeps **project economics** separate from **financing**.

Project cashflow contains:

- Project inflow / Client PPC receipts; and
- Project cost (Work + Scheduled Cost).

Financing then adds:

- facility Draw;
- facility Repayment;
- facility Interest & fees; and
- facility Outstanding balance.

A facility draw is not project revenue and is not project cost. It is financing cash received.

## 2. Scheduled facility draws

A scheduled draw is a requested **facility inflow**. It is not a project outflow and it does not imply a purchase unless a future linking feature explicitly connects the facility to a Scheduled Cost Activity.

For each period:

```text
requested_draw = draw_schedule[period]
actual_draw = min(requested_draw, available_capacity)
```

Only `actual_draw` enters cashflow.

If a requested draw exceeds capacity, the unavailable amount:

- has no cashflow effect;
- is not an additional project cost;
- is not carried into the next period; and
- is not automatically drawn later.

The requested schedule and facility limit are independent. In particular, a revolving facility can legitimately contain scheduled requested draws whose cumulative total exceeds the facility limit because repaid principal can restore capacity.

## 3. Facility limit and capacity

A blank limit means unlimited capacity.

### Non-revolving

```text
available_capacity = limit - cumulative_actual_draws
```

Principal repayment does not restore capacity.

### Revolving

```text
available_capacity = limit - current_outstanding_principal
```

Principal repayment restores capacity.

Example:

```text
limit = 1,000
P1 actual draw 800      -> outstanding 800 -> available 200
P2 repayment 500        -> outstanding 300 -> available 700
P4 requested draw 900   -> actual draw 700 -> outstanding 1,000
```

## 4. Draw availability window

`start` and `end` define when **new drawings** are available. They do not stop repayment, interest, fees, or outstanding principal after the last draw period.

The last available draw period is not facility maturity.

The financial horizon can therefore extend beyond both project Work duration and the facility's last available draw period.

## 5. Draw methods

Current draw methods are:

### Automatic shortfall

Used for overdraft/owner-contribution style funding.

The facility draws only when the funded cash position would otherwise be negative, subject to its availability window and capacity.

Automatic shortfall sources are ordered so overdraft-style facilities run before owner/contractor contribution sources.

### Scheduled

The user requests explicit amounts in explicit periods. Actual draw is capped by available capacity.

CashflowPot does not infer LC/equipment timing from Activities.

### PPC base

The requested draw is based on a configured percentage of **PPC issued** in the certificate period.

This is distinct from PPC repayment timing, which uses client PPC receipts after the project payment delay.

## 6. Repayment methods

Current repayment methods are:

### Cashflow sweep

Repay from positive funded cash only. This is the only repayment method constrained by available positive cash.

If several facilities use sweep, the engine follows saved `sweep_priority`. When no explicit order is available, interest rate/index ordering provides deterministic fallback behavior.

### Percent of PPC

Repayment due is a configured percentage of `ppc_base`, meaning client PPC receipts excluding advance and retention-release cash.

This repayment is contractual and can make cash negative; automatic-shortfall facilities can then fund the resulting deficit if configured.

### Equal installments

Repay a calculated installment on the configured start/interval/count pattern, capped by outstanding principal.

### Scheduled repayment

Repay the explicitly entered amount in that period, capped by outstanding principal.

## 7. Automatic repayment timing for scheduled draws

For `draw_method = scheduled`, principal drawn in period `P` cannot be automatically repaid in the same period through:

- `percent_of_ppc`; or
- `cashflow_sweep`.

The automatic principal repayment cap in period `P` is the opening outstanding principal:

```text
automatic_repayment_P <= opening_outstanding_P
```

Example:

```text
P3 opening outstanding 0
P3 draw 500
P3 automatic repayment 0
P3 closing outstanding 500

P4 opening outstanding 500
P4 draw 300
P4 automatic repayment 200
P4 closing outstanding 600
```

Older principal can therefore be repaid during a period that also has a new scheduled draw; the new draw itself becomes automatically repayable from the following period.

Explicit `scheduled` repayments and `equal_installments` retain their explicit user-entered/calculated timing and are not changed by this one-period eligibility rule.

PPC Discount keeps its PPC-issued draw / PPC-receipt repayment semantics because its draw method is `ppc_base`, not `scheduled`.

## 8. Interest and fees

Facility interest is calculated on **opening outstanding principal**.

A draw made in period `P` therefore begins accruing facility interest in the following period.

Current one-time facility fees are charged at the facility availability start period.

Interest and fees are separate backend series, but the UI/Excel presentation combines them into one **Interest & fees** row per facility while preserving separate KPI detail.

## 9. Period calculation order

The financing engine processes each period in this order:

1. read project inflow and project outflow;
2. calculate interest on opening facility principal and applicable facility fees;
3. establish cash before financing and deduct financing cost;
4. apply scheduled/PPC-linked facility draws, limited by capacity;
5. apply contractual repayments such as scheduled, equal-installment, and percent-of-PPC;
6. apply cashflow-sweep repayments using available positive cash and sweep priority;
7. apply automatic-shortfall facilities such as overdraft and owner/contractor contribution;
8. calculate closing facility outstanding, available capacity, funded net cash, and funded cash balance.

This order matters. Interest uses opening principal; scheduled same-period draws are not included in that period's interest.

## 10. PPC issued vs PPC receipts

The backend exposes two supporting project series for facility logic:

```text
ppc_issued()
```

Net certificate values in certificate periods before the client payment delay.

```text
ppc_base()
```

Client PPC cash receipts after payment timing, excluding client advance and retention-release cash.

PPC Discount uses:

```text
draw request -> ppc_issued
repayment due -> ppc_base
```

These events must remain separately named in UI/documentation because issuance and client receipt can occur in different periods.

## 11. Returned facility rows

Each calculated facility row contains:

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

There is no `unfunded_draw` facility-row cashflow. A requested draw that cannot be funded by capacity simply has no cashflow effect.

Aggregate financing output also includes:

```text
facility_draws
principal_repayments
facility_interest
facility_fees
net_cash_flow
pre_financing_balance
funded_cash_balance
unfunded_shortfall
```

## 12. Cashflow presentation

The UI presents financing separately from project economics:

```text
PROJECT CASHFLOW
  Project inflow
    Client PPC receipts
  Project cost
    Work + scheduled costs

FACILITIES
  <Facility name>
    Draw
    Repayment
    Interest & fees
    Outstanding balance

CASH POSITION
  Total inflow
  Total outflow
  Net cash flow
  Closing cash balance
```

Definitions:

```text
Total inflow
= Project inflow + actual facility draws

Total outflow
= Project cost + facility principal repayments + facility interest + facility fees

Net cash flow
= Total inflow - Total outflow

Closing cash balance_t
= Closing cash balance_(t-1) + Net cash flow_t
```

Facility outstanding is a balance, not an inflow or outflow.

User-facing period labels are 1-based even though backend period indexes are zero-based.

## 13. Decision KPIs

The backend summary exposes canonical metrics for the compact KPI grid:

- `direct_cost`: Project cost (Work + Scheduled Cost);
- `total_facility_interest`;
- `total_facility_fees`;
- `financing_cost`: facility interest + fees;
- `total_cost`: Project cost + financing cost;
- `minimum_pre_financing_balance` and `minimum_pre_financing_period`;
- `peak_pre_financing_need` and `peak_pre_financing_period`;
- `peak_facility_outstanding`: maximum combined principal outstanding;
- `final_facility_outstanding`: combined principal still outstanding at the model horizon;
- `final_cash_balance`: funded closing cash balance;
- `cash_after_debt_settlement`: final cash balance minus final outstanding principal;
- `work_duration`;
- `financial_horizon`.

`cash_after_debt_settlement` is a principal-only settlement view. It does not invent future interest or facility maturity beyond the modeled horizon.

The user-facing Peak Funding Requirement is zero when the pre-financing balance never becomes negative; otherwise it shows the magnitude of the most negative pre-financing balance and its 1-based display period.

## 14. Excel/report conventions

The current Excel export includes the full facility layer rather than a simplified summary.

Below Project Cashflow it presents:

```text
FACILITIES
  each facility:
    Draw
    Repayment
    Interest & fees
    Outstanding balance

CASH POSITION
  Total inflow
  Total outflow
  Net cash flow
  Closing cash balance
```

Facility rows use backend-calculated flows/balances. Excel formulas aggregate/report them; Excel does not independently reproduce revolving-capacity or repayment-order logic.

Current visual conventions include:

- one facility name merged vertically across its four rows;
- four subtle pastel facility backgrounds cycled for additional facilities;
- facility background continuing through the timeline cells;
- one decimal place for report cash amounts;
- real numeric cells/formulas rather than text-formatted numbers;
- Interest + Fees combined visually;
- current charts based on Total inflow, Total outflow, and Closing cash balance;
- Cash after debt settlement in Key Metrics.

## 15. Precision and totals

Period arrays may be serialized/displayed at practical precision. Canonical totals should come from authoritative source values/summary fields rather than summing visibly rounded period labels when that can create drift.

Facility aggregate totals can use the calculated facility series because those series are themselves authoritative outputs of the financing engine.

## 16. Out of scope

The current engine does not yet:

- link an LC draw to a Scheduled Cost Activity automatically;
- synchronize a material purchase outflow and LC draw automatically;
- carry an unavailable scheduled draw forward;
- infer facility maturity;
- calculate unmodeled future interest after the scenario horizon; or
- model guarantee-only LC exposure as a cash draw.

A guarantee-only LC with no cash draw remains outside the cashflow calculation unless a future non-cash facility/exposure model is introduced.
