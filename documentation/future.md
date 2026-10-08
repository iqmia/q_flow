# CashflowPot future direction

This file records directions that have been discussed and approved as useful future work but are **not current product behavior** unless they are later implemented and moved into the current-product documentation.

Keep this list selective. Ideas that were merely discussed, superseded, or rejected should not become roadmap promises here.

## 1. AI-assisted project and scenario setup

### Goal

Allow a user to describe a construction project in normal language and provide a small amount of known information, such as:

- project scope/description;
- contract value;
- expected duration;
- project type; and
- any known commercial conditions.

AI can then propose a starting cash-flow model for user review, including items such as:

- activity structure;
- estimated activity cost allocation;
- activity duration/timing;
- curve/timing assumptions;
- subcontracted share; and
- starting commercial/forecast assumptions where appropriate.

### Boundary

AI is an **input assistant**, not an alternative cash-flow engine.

The generated proposal must be reviewable/editable by the user. After review, the normal CashflowPot data model, backend validation, and calculation engine remain authoritative.

Portable CashflowPot JSON is a natural machine-readable target for AI-generated scenarios because it already represents scenario inputs rather than calculated results.

### Preparation before implementation

The AI schema should use semantic user-facing concepts rather than legacy backend names.

In particular, the current `activity_type` field mixes trade/category meaning with a calculation switch for the exact value `linear`. Before AI-generated models become authoritative, activity/trade category and work-distribution type should be treated as separate semantic concepts even if database compatibility temporarily preserves the old field.

## 2. Full scenario report

The current Excel export is a working schedule/output. A future **scenario report** should be a more complete decision document suitable for forwarding to management, employers, banks, lenders, or investment/finance reviewers.

The intended direction includes:

- concise project/scenario identification;
- contract and key commercial terms;
- forecasting assumptions;
- key cash-flow KPIs;
- selected charts on dedicated report/chart sheets where appropriate;
- an executive-summary style overview;
- clear distinction between inputs, forecast results, and interpretation; and
- professional formatting suitable for external circulation.

The report should use the existing CashflowPot calculation results and formulas rather than introducing a second calculation model in the export layer.

## 3. AI-assisted report narrative

Once the scenario report structure is stable, AI may assist with a short narrative/executive summary explaining the forecast, for example:

- peak funding requirement;
- when the funding requirement occurs;
- major timing drivers;
- effect of retention/payment/WIEB assumptions;
- sensitivity between compared scenarios; and
- issues a lender or management reviewer may want to challenge.

Any narrative must remain clearly tied to the calculated scenario and must not present model assumptions as guaranteed future outcomes.

## 4. Scenario comparison and decision support

CashflowPot already supports multiple independent scenarios per project. A future reporting/analysis layer can make scenario comparison more explicit for decisions such as:

- tender/base/current/recovery comparisons;
- changed payment terms;
- alternative subcontract strategies;
- front-loaded vs back-loaded execution or contract curves; and
- financing sensitivity.

This should build on the existing scenario model rather than create a separate parallel forecast structure.

## 5. Project financing facilities

### Goal

Add a financing layer that helps contractors assess whether a project can be funded, what facilities may be required, and whether those facilities are available in the periods when the project needs them.

Typical uses include bid/no-bid review, bank-facility planning, facility-adequacy checks, and financing scenario comparison.

### Core principle

Keep the model cash-flow-native. CashflowPot does not need supplier, purchase-order, or procurement relationships to model financing.

A facility draw is added to project inflow. Principal repayments, fees, and interest are added to project outflow. The model should preserve the project cash position before financing as well as the funded cash position after financing so financing does not hide the underlying project funding requirement.

A future facility should have common terms such as:

- facility type/name;
- availability start and end;
- limit;
- fees;
- interest/cost; and
- outstanding principal/capacity.

For a limited facility, available capacity is based on the facility limit less outstanding principal, where outstanding principal is principal drawn minus principal repaid.

### Facility setup and calculation rules

The user selects a suggested facility model or creates a custom one. A preset supplies editable defaults; it does not lock the facility to a product-specific calculation. Each saved facility has a user-defined name for its cashflow rows, a product type, draw method, repayment method, availability start/end, limit, fees, interest rate, and revolving setting. Method-specific inputs include a scheduled draw/repayment table, PPC advance/repayment percentages, equal-installment start/interval/count, or sweep priority.

Draw methods:

- **Automatic shortfall:** draw only to cover a negative funded cash position, within availability and remaining capacity. OD draws run before calculated contractor/owner contribution, which covers the residual shortfall.
- **Scheduled:** draw the entered amount in the entered period. CashflowPot does not infer LC or equipment timing from activities. A draw above remaining capacity is capped and the undrawn amount is reported.
- **PPC base:** draw the configured share of the net PPC certificate in its issue period, capped by remaining capacity. PPC repayments use employer PPC receipts after the project payment delay.

One repayment method applies to each facility:

- **Cashflow sweep:** repay from positive cash after all other period flows. This is the only repayment method that depends on available cash. If several facilities use it, apply their user-editable priority order; when no order is saved, the higher interest rate is repaid first.
- **Percent of PPC:** apply the configured percentage to that period's employer PPC receipts, even if the repayment makes cash negative.
- **Equal installments:** divide total principal drawn by the configured payment count and pay on the configured start period and interval. Pay the installment even if cash becomes negative.
- **Scheduled:** pay the entered amount in that period, up to principal outstanding, even if cash becomes negative.

Every draw is an inflow row; principal repayment is an outflow row; fees and interest are separate outflow rows. Available capacity is `limit - outstanding principal` for revolving facilities and `limit - total principal drawn` for non-revolving facilities. Outstanding principal is `total drawn - total principal repaid`.

The current backend convention charges a one-time facility fee in its availability start period and calculates interest each period on the opening principal balance. Interest is a cash outflow, not capitalized directly into that facility's principal. If cash is insufficient, automatic shortfall facilities may fund that cost according to their draw rules.

The initial editable suggestions are:

| Facility type | Draw default | Repayment default |
|---|---|---|
| Letter of Credit | Scheduled | Percent of PPC |
| Overdraft | Automatic shortfall | Cashflow sweep |
| PPC Discount | PPC base | Percent of PPC |
| Working Capital | Scheduled | Percent of PPC |
| Equipment Loan | Scheduled | Scheduled |
| Owner's Injection | Automatic shortfall | Cashflow sweep |
| Other | Scheduled | Cashflow sweep |

A guarantee-only LC has no cash draw and stays outside the cashflow calculation. If the bank pays a supplier, enter the funded amount as a scheduled LC draw and model repayment using the selected method.

### Intended outputs

The financing layer should eventually show at least:

- project cash position before financing;
- facility draws and repayments;
- funded cash position;
- peak underlying funding need and when it occurs;
- utilization and remaining capacity by facility;
- total financing cost; and
- any remaining unfunded shortfall.

Facility adequacy should be judged by **amount, timing, availability, and outstanding capacity**, not simply by adding nominal facility limits.

### Implementation sequence and remaining work

The approved sequence is Python calculation/API first, Flutter facility editing second, and Excel report rows last. The calculation must expose pre-financing cash, facility draws, principal repayments, interest, fees, balances, available capacity, and any unfunded shortfall. The current Excel workbook is print-formatted for A4 landscape and A3; facility rows must preserve its existing column widths and scaling.

Backend conventions above make the period loop deterministic. They should be revisited only if bank negotiations require different terms. Guarantee-only LC capacity/fees, additional facility types, and sensitivity/report presentation can be addressed separately.

## 6. Not an assumed roadmap item

The following is **not** an approved default future direction:

- per-activity selling values;
- per-activity markup allocation; or
- a detailed Schedule of Values model.

The current Independent contract curve deliberately separates main-contract value timing from activity cost allocation. Do not reintroduce an old “activity-specific selling value and markup allocation” roadmap statement without a new product decision.

## 7. How ideas graduate from future to current

When a future item is implemented:

1. update the relevant current-product document (`product.md`, `technical.md`, `ui-ux.md`, or `deployment.md`);
2. update any affected detailed reference;
3. add/adjust regression tests;
4. remove or rewrite the item here so `future.md` does not describe an already-live feature as future work.

Last reviewed: 7 October 2026.
