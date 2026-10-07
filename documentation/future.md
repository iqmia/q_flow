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

### Composable draw and repayment rules

The main design direction is to treat a financing product as a combination of a **draw method** and a **repayment method**, rather than building a separate calculation model for every named banking product.

Possible draw methods include:

- **Automatic cash-shortfall draw** — draw when the pre-financing cash balance would otherwise be negative, subject to available capacity. This fits overdraft-style funding and can also represent contractor funding used to close residual gaps.
- **Scheduled draw** — the user specifies the project period and amount. This can represent funded LCs, equipment finance, contract-specific working-capital loans, or other planned facilities without requiring CashflowPot to know what the financing paid for.
- **PPC-linked draw** — draw is triggered by an eligible PPC/certification amount, for products such as PPC discounting. The exact eligible series and timing rules need to be defined before implementation.

Possible repayment methods include:

- **Cashflow sweep** — use available positive project cash to repay outstanding principal;
- **Percentage of PPC** — repay an agreed percentage of eligible PPC receipts;
- **Equal installments** — repay equal amounts at a selected interval; and
- **Scheduled repayments** — user-defined repayment amounts by project period.

These methods should be combinable. For example, a user could schedule an LC draw in period 5 and configure its repayment as 20% of each PPC starting from period 10.

### Initial facility examples

- **Overdraft:** automatic cash-shortfall draw, facility limit, fees/interest, normally repaid by cashflow sweep.
- **Contractor funding:** may use the same automatic draw mechanics as an overdraft, with its own optional limit and funding cost.
- **PPC discounting:** PPC-linked draw with an advance percentage and facility limit; later receipts repay the outstanding advance according to the agreed terms.
- **Funded LC:** scheduled draw, with repayment selected independently from the draw schedule.
- **Equipment finance:** scheduled draw with installment, scheduled, or other agreed repayment terms.
- **Contract-specific working-capital finance:** planned/scheduled draw with sweep, installment, PPC-linked, or scheduled repayment.

A guarantee-only LC does not create a project cash movement and therefore does not need to be included in this cash-flow feature unless CashflowPot later adds a separate non-cash facility-capacity model.

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

### Details to settle before implementation

The following remain intentionally open for later design:

- priority when multiple automatic facilities can fund the same shortfall;
- exact PPC-linked draw and repayment mechanics;
- interest and fee calculation conventions by facility;
- repayment ordering when several facilities are outstanding;
- contractor-funding repayment behavior; and
- interaction between financing repayments and available positive cash.

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
