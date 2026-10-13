# Financing Facilities Reference

Last reviewed: 13 October 2026

This reference describes how CashflowPot financing facilities interact with project cashflow. Project activities create project inflow/outflow. Facilities sit on top of that project cashflow and create financing inflows, principal repayments, interest, fees, and outstanding balances.

## Scheduled facility draws

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

## Facility limit

The draw schedule and facility limit are independent.

A schedule may contain total requested draws greater than the facility limit, especially for a revolving facility.

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

## Draw availability window

`start` and `end` define when new drawings are available. They do not stop repayment, interest, fees, or outstanding principal after the last draw period.

The last available draw period is not facility maturity.

## Automatic repayment timing for scheduled draws

For `draw_method = scheduled`, principal drawn in period `P` cannot be automatically repaid in the same period.

This applies to:

- `percent_of_ppc`;
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

Older principal can therefore be repaid during a period that also has a new draw; the new draw itself becomes automatically repayable from the following period.

Explicit `scheduled` repayments and `equal_installments` retain their explicit user-entered timing and are not changed by this one-period eligibility rule.

PPC Discount keeps its existing PPC-issued draw / PPC-receipt repayment behavior because its draw method is not `scheduled`.

## Period calculation order

The financing engine processes each period in this order:

1. project inflow and project outflow;
2. interest on opening facility principal and applicable facility fees;
3. scheduled/PPC-linked facility draws, limited by capacity;
4. contractual repayments such as scheduled, equal-installment, and percent-of-PPC;
5. cashflow sweep repayments using available positive cash and sweep priority;
6. automatic-shortfall facilities such as overdraft and owner/contractor contribution;
7. closing facility outstanding and funded cash balance.

Interest on a draw begins in the following period because facility interest uses opening principal.

## Cashflow presentation

The UI presents financing separately from project economics.

```text
PROJECT CASHFLOW
  Project inflow / Client PPC
  Project cost

FACILITIES
  <Facility name>
    Draw
    Repayment
    Interest & fees
    Outstanding balance

OVERALL CASH POSITION
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

## Decision KPIs

The backend summary exposes canonical metrics for the compact KPI grid:

- `direct_cost`: Project cost (Work + Scheduled Cost);
- `total_facility_interest`;
- `total_facility_fees`;
- `financing_cost`: facility interest + fees;
- `total_cost`: Project cost + financing cost;
- `minimum_pre_financing_balance` and `minimum_pre_financing_period`;
- `peak_facility_outstanding`: maximum combined principal outstanding;
- `final_facility_outstanding`: combined principal still outstanding at the model horizon;
- `final_cash_balance`: funded closing cash balance;
- `cash_after_debt_settlement`: final cash balance minus final outstanding principal;
- `work_duration`;
- `financial_horizon`.

`cash_after_debt_settlement` is a principal-only settlement view. It does not invent future interest or facility maturity beyond the modeled horizon.

The user-facing Peak Funding Requirement is zero when the pre-financing balance never becomes negative; otherwise it shows the most negative pre-financing balance and its one-based display period.

## Out of scope

The current engine does not yet:

- link an LC draw to a Scheduled Cost Activity;
- synchronize a material purchase outflow and LC draw automatically;
- carry an unavailable scheduled draw forward;
- infer facility maturity; or
- calculate unmodeled future interest after the scenario horizon.
