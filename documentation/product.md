# CashflowPot product definition and rules

## 1. What CashflowPot is

CashflowPot is a construction cash-flow simulation and forecasting product for contractors, project/commercial teams, finance teams, management, investors, and lenders.

Its core job is to turn **project execution, project costs, contract terms, financing facilities, and forecasting assumptions** into a time-phased view of:

- client/project receipts;
- project costs and payments;
- financing draws, repayments, interest, and fees;
- net cash flow;
- cumulative cash position;
- outstanding facility principal; and
- working-capital / funding requirement.

A useful summary is:

> Build the cash-flow view needed for the decision now, then revise it as the project changes.

CashflowPot is designed for decisions such as tendering, bid/no-bid, contractor financing, lender review, feasibility, management what-if analysis, budgeting, recovery planning, and mid-project reforecasting.

The output is a **forecast, not a guarantee**. It depends on the project information, contract terms, facility terms, and forecasting assumptions supplied by the user.

## 2. Relationship to planning software

Planning software and CashflowPot answer different questions and can complement each other.

A programme can describe when work, resources, or cost are expected to occur. CashflowPot models the commercial/financial layer: how execution, project costs, contract terms, and financing are expected to turn into receipts, payments, funding exposure, and cash position.

A detailed programme may inform activity timing when it is current and proportionate to the decision. CashflowPot can also use generated or manually entered execution/cost profiles when a detailed programme is unavailable, stale, or unnecessary for the financial question being answered.

Do not position CashflowPot as a lesser, simplified, or replacement version of Primavera P6, MS Project, ERP, accounting, or cost-control software.

## 3. Product hierarchy

### Project

A CashflowPot project corresponds to a QAuth Unit. The QAuth Unit owns project identity, access, roles, and permissions.

A project can contain multiple independent cash-flow scenarios.

### Cash-flow scenario

A scenario is a complete set of financial assumptions, activities, client terms, inflow settings, and financing facilities for one view of the project. Typical scenarios include:

- Base;
- Tender;
- Current;
- Recovery; or
- alternative what-if cases.

Creating a project creates a default `Base Cashflow` scenario.

### Activity

Activities model project cost and timing. Calculation behavior is explicitly separated from activity category/template.

Current Activity modes are:

- **Work** — physical/cost-loaded execution that contributes to project work duration and, depending on the selected inflow method, can drive client contract-value work.
- **Scheduled Cost** — project cost/outflow entered directly by period that does not represent physical/billable work and does not extend project work duration.

Work Activities can use:

- S-curve;
- Linear; or
- Manual schedule distribution.

`activity_type` is a category/template such as Structure, MEP, or Facade. It is not the calculation switch.

## 4. Work Activities

A Work Activity has estimated contractor cost, timing, and a work distribution. Its calculated work is then split between self-performed/direct and subcontracted portions.

For generated S-curve or Linear Work, cost and duration are user inputs. For Manual Work, the entered dense schedule is authoritative and the backend derives:

```text
cost     = sum(schedule)
duration = number of schedule periods
```

Work subcontract terms can include advance, retention, Work in Excess of Billings (WIEB), no-billing period, payment period, and DLP.

Pre-work time is supported through the legacy backend `mobilization_period` field, presented as a pre-work/no-work period rather than a mobilization percentage.

## 5. Scheduled Cost Activities

Scheduled Cost represents project cost/outflow that should be placed directly into specific project periods, for example an equipment purchase or other discrete project expenditure that should not be treated as physical progress.

Scheduled Cost:

- creates project cost and outflow;
- affects net cash, financing need, financial horizon, and total project cost;
- creates zero project work;
- does not create client PPC/billed work;
- does not extend work duration; and
- does not apply Work subcontract terms, WIEB, advance, retention, payment delay, DLP, or pre-work transformations.

The backend derives Scheduled Cost `cost` and `duration` from its dense cost schedule.

In the Flutter UI, Scheduled Cost is entered using user-facing **absolute project periods**. The client converts that representation to the backend's start offset plus dense local schedule.

## 6. Two inflow forecast methods

CashflowPot supports two methods for generating main-contract value-of-work before client payment terms are applied.

### Independent contract curve — default for new scenarios

The contract value follows its own Linear or S-curve over the **Work Activity execution duration**.

For an S-curve, the user can model timing as:

- Back-loaded;
- Balanced; or
- Front-loaded.

Activities still determine project outflow, but Scheduled Cost does not allocate client contract value and does not extend the independent inflow curve.

### Activity-linked inflow — alternative / compatibility method

The combined **Work Activity** cost-work profile is scaled proportionally to the total contract value.

Scheduled Cost is excluded from both the Work-cost denominator and the contract-value work profile.

Neither method requires or infers a separate selling value, markup, or Schedule of Values for each activity.

## 7. Project outflow

Project outflow is the sum of all current Activity outflows:

- Work Activity outflow; plus
- Scheduled Cost outflow.

Deleted Activities do not participate in the current forecast.

Changing the main-contract inflow method must not change Activity work or project outflow.

## 8. Contract terms vs forecasting assumptions

This distinction should remain visible in the product and documentation.

### Contract / commercial terms

Examples include:

- advance payment and recovery;
- retention;
- retention release timing;
- payment period; and
- Defects Liability Period (DLP).

### Forecasting assumptions

Examples include:

- Work in Excess of Billings (WIEB) percentage;
- execution curve shape and skew;
- subcontracted share where it is not contractually fixed; and
- other modeled behavior used to forecast future cash timing.

Do not describe every model input as an assumption. Where a value represents a known contract term, call it a contract or commercial term.

## 9. WIEB — Work in Excess of Billings

WIEB is the estimated share of work performed in a period that is not yet billable and is carried into the following billing period.

Actual WIEB is a value/amount. CashflowPot stores a **percentage forecasting assumption** used to simulate that timing effect.

At project level, WIEB applies to client-side contract-value work.

At Work Activity level, WIEB applies only to the subcontracted share. Self-performed/direct cost is paid as incurred.

Scheduled Cost does not use WIEB.

WIEB changes timing, not lifetime value.

Use the user-facing term **Work in Excess of Billings (WIEB)**. Do not use `Billing Deferral` as a replacement label.

## 10. Client PPC and project inflow

CashflowPot distinguishes certificate timing from cash receipt timing.

- **PPC issued** represents net progress-certificate value in the certificate period, before the client payment delay.
- **Project inflow / Client PPC receipts** represents cash actually received after the configured payment timing, plus client advance and retention releases where applicable.

This distinction matters for PPC Discount facilities: discount draws are based on certificate issuance, while PPC-linked repayment uses employer/client PPC receipts.

## 11. Time convention

The calculation engine works in integer model periods. The app is commonly used monthly, but the engine itself does not require a calendar month.

Within one scenario, timing inputs must use one consistent period convention.

Backend offsets are zero-based where required by the data model. **User-facing period labels are 1-based** (`P1`, `P2`, ...).

Examples:

- payment period `2` means two model periods after billing;
- DLP `12` means the second retention release occurs twelve model periods after the first release point.

Facility and legacy financing rates are rates per model period.

## 12. Financing facilities

Financing facilities are a current calculation layer placed on top of project cashflow.

Facility definitions can model:

- scheduled draws;
- automatic-shortfall draws such as overdraft/owner contribution;
- PPC-based draws;
- cashflow-sweep repayment;
- percent-of-PPC repayment;
- scheduled repayment;
- equal installments;
- interest;
- fees;
- revolving or non-revolving capacity; and
- availability start/end periods.

A facility draw is a financing inflow, not a new project cost. Principal repayment, interest, and fees are financing outflows.

For a **revolving** facility, repayment restores capacity because available capacity is based on current outstanding principal. For a **non-revolving** facility, repayment does not restore draw capacity because capacity is based on cumulative actual draws.

A requested scheduled draw above available capacity is capped. The unavailable amount has no cashflow effect and is not carried forward automatically.

Facility availability start/end constrain new drawings; they do not erase outstanding debt or prevent later repayment/interest from extending the financial horizon.

Detailed rules are in [`reference/financing_facilities.md`](reference/financing_facilities.md).

## 13. Legacy scenario financing

When explicit financing facilities are not configured, the legacy scenario `interest_rate` behavior remains available: financing cost is applied only when cumulative cash is negative.

When facilities are configured, the facility engine becomes the financing layer and exposes facility draws, principal repayments, interest, fees, funded cash balance, and outstanding principal.

The UI should not present the legacy `outflow_with_interest` API name directly; it represents the resulting cumulative financed cash balance.

## 14. Cashflow presentation

The current UI and Excel report present the calculated forecast in three financial sections:

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

## 15. Decision KPIs

The compact result set includes:

- Project cost;
- Financing cost, with interest and fees detail;
- Total cost;
- Peak funding requirement and its period;
- Peak facility usage;
- Outstanding facilities at the model horizon;
- Closing cash balance;
- Cash after debt settlement;
- Work duration; and
- Financial horizon.

`cash_after_debt_settlement` means final cash balance minus final outstanding facility principal. It is a principal-only settlement view; it does not invent future interest or maturity beyond the modeled horizon.

Peak Funding Requirement is zero when the pre-financing cash balance never becomes negative. Otherwise it is the magnitude of the most negative pre-financing balance, displayed with a 1-based period.

## 16. Work duration vs financial horizon

These are deliberately different measures.

- **Work duration** is derived from Work Activity work only.
- **Financial horizon** is the length of the calculated cashflow and can extend because of Scheduled Cost, client/subcontract payment timing, WIEB carry, retention/DLP, facility availability, repayments, fees, interest, and outstanding financing activity.

A Scheduled Cost after physical work finishes can therefore extend the financial forecast without extending project Work duration.

## 17. Numeric precision and totals

The backend calculation engine is authoritative for source values and canonical summary totals.

Period arrays are serialized/displayed at practical precision, so report/UI totals must not be reconstructed by adding visibly rounded period labels when an authoritative total exists.

For example, twelve displayed values of `833.33` must not cause an Activity with an authoritative cost of `10,000` to be reported as `9,999.96`.

The Flutter UI may use scaled display notation for very large values while retaining exact values in tooltips/details. Excel keeps real numeric cells and formulas; it does not convert financial values to formatted text.

## 18. Import/export and calculation authority

The backend calculation engine is authoritative for the financial forecast and backend validation.

The Flutter client validates inputs early and presents them clearly, but it must not maintain a conflicting financial model.

Portable scenario files use the versioned `cashflowpot.cashflow` JSON format documented in [`reference/cashflow_json_format.md`](reference/cashflow_json_format.md).

The current Excel export presents the complete calculated scenario, including project cashflow, facility flows/balances, cash position, KPIs, charts, and reconciliation while preserving the approved print geometry. It must not silently introduce alternative project or facility formulas.

## 19. Product rules that must stay stable unless deliberately changed

1. A project can contain multiple independent scenarios.
2. New scenarios default to the Independent contract curve with a balanced S-curve.
3. Legacy scenarios with null independent-inflow settings remain activity-linked until changed.
4. Activity category/template is separate from Activity calculation mode and Work distribution.
5. Work Activities determine execution/work duration; Scheduled Cost does not.
6. Project outflow includes both Work and Scheduled Cost Activities.
7. Scheduled Cost does not create client PPC/billed work.
8. Main-contract inflow terms are applied after the contract-value work profile is generated.
9. Self-performed cost does not use subcontract WIEB.
10. WIEB, retention, payment period, and DLP change timing, not underlying lifetime value.
11. Advance plus retention cannot exceed 100% on either the client or Work-subcontract side.
12. Deleted Activities do not participate in the current forecast.
13. Facility draw schedules request financing inflows; they are not project-cost schedules.
14. Revolving repayment restores capacity; non-revolving repayment does not restore cumulative draw capacity.
15. The backend is authoritative for validation and calculation.
16. Individual Activity selling values / markup allocation / Schedule of Values are not part of the current model and are not an assumed roadmap item.
17. A forecast is intended to be revised as information changes.

Exact formulas and validation limits are defined in [`reference/cashflow_model.md`](reference/cashflow_model.md).

## 20. Current product boundaries

The current calculation engine does not calculate schedule logic or critical path, delay entitlement, resource availability/productivity, detailed BOQ measurement, tax/currency/escalation/bond mechanisms, accounting statements, or Activity-specific selling values.

It also does not infer facility maturity beyond entered/modelled timing, carry unavailable scheduled draws forward automatically, or link an LC draw automatically to a Scheduled Cost purchase.

Those subjects may affect inputs or scenario assumptions, but they are not independently calculated by the current CashflowPot engine.

## 21. Brand and naming

Use **CashflowPot** in current product-facing documentation and copy.

CashflowPot is a Quollnet product. Quollnet should be visible as the parent ecosystem without overpowering the CashflowPot identity.

The public-site positioning should remain consistent with this document: construction cash-flow simulation/forecasting, contract terms and assumptions, financing facilities, revisable scenarios, and decision support for construction commercial/financial questions.

Last reviewed: 14 October 2026.
