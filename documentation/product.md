# CashflowPot product definition and rules

## 1. What CashflowPot is

CashflowPot is a construction cash-flow simulation and forecasting product for contractors, project/commercial teams, finance teams, management, investors, and lenders.

Its core job is to turn **project execution, contract terms, and forecasting assumptions** into a time-phased view of:

- cash received;
- cash paid;
- net cash flow;
- cumulative cash position;
- financing cost; and
- working-capital / funding requirement.

A useful summary is:

> Build the cash-flow view needed for the decision now, then revise it as the project changes.

CashflowPot is designed for decisions such as tendering, bid/no-bid, contractor financing, lender review, feasibility, management what-if analysis, budgeting, recovery planning, and mid-project reforecasting.

The output is a **forecast, not a guarantee**. It depends on the project information, contract terms, and forecasting assumptions supplied by the user.

## 2. Relationship to planning software

Planning software and CashflowPot answer different questions and can complement each other.

A programme can describe when work, resources, or cost are expected to occur. CashflowPot models the next commercial layer: how execution, contract terms, and assumptions are expected to turn into receipts, payments, net cash, and funding exposure.

A detailed programme may inform activity timing when it is current and proportionate to the decision. CashflowPot can also use mathematical execution profiles when a detailed programme is unavailable, stale, or unnecessary for the financial question being answered.

Do not position CashflowPot as a lesser, simplified, or replacement version of Primavera P6, MS Project, ERP, accounting, or cost-control software.

## 3. Product hierarchy

### Project

A CashflowPot project corresponds to a QAuth Unit. The QAuth Unit owns project identity, access, roles, and permissions.

A project can contain multiple independent cash-flow scenarios.

### Cash-flow scenario

A scenario is a complete set of financial assumptions and activities for one view of the project. Typical scenarios include:

- Base;
- Tender;
- Current;
- Recovery; or
- alternative what-if cases.

Each scenario can have its own contract value, client terms, inflow method, financing assumption, and activities.

Creating a project creates a default `Base Cashflow` scenario.

### Activity

Activities model execution timing and project cost. They determine project outflow and the execution duration used by the scenario.

Each activity has an estimated cost, timing/duration, work-curve behavior, subcontracted share, and subcontract commercial assumptions.

## 4. Two inflow forecast methods

CashflowPot supports two current methods for generating main-contract value-of-work before client payment terms are applied.

### Independent contract curve — default for new scenarios

The contract value follows its own linear or S-curve over the execution duration derived from the activities.

For an S-curve, the user can model the timing as:

- Back-loaded;
- Balanced; or
- Front-loaded.

Activities still determine execution duration and outflow, but their cost profile does not allocate contract value.

### Activity-linked inflow — alternative / compatibility method

The combined activity cost-work profile is scaled proportionally to the total contract value. This is useful when the expected client-side value profile should follow the execution-cost profile.

Neither method requires or infers a separate selling value, markup, or Schedule of Values for each activity.

## 5. Outflow is activity-based

Project outflow remains activity-based in both inflow methods.

Each activity is split into:

- self-performed/direct cost; and
- subcontracted cost.

Self-performed cost is paid as incurred. The subcontracted share follows its own advance, retention, Work in Excess of Billings, no-billing period, payment period, and DLP assumptions.

Changing the main-contract inflow method must not change activity work or project outflow.

## 6. Contract terms vs forecasting assumptions

This distinction should remain visible in the product and documentation.

### Contract / commercial terms

Examples include:

- advance payment and recovery;
- retention;
- retention release timing;
- payment period; and
- Defects Liability Period (DLP).

These describe contractual or commercial timing rules.

### Forecasting assumptions

Examples include:

- Work in Excess of Billings (WIEB) percentage;
- execution curve shape and skew;
- subcontracted share where it is not contractually fixed; and
- other modeled behavior used to forecast future cash timing.

Do not describe every model input as an assumption. Where a value represents a known contract term, call it a contract or commercial term.

## 7. WIEB — Work in Excess of Billings

WIEB is the estimated share of work performed in a period that is not yet billable and is carried into the following billing period.

Actual WIEB is a value/amount. CashflowPot stores a **percentage forecasting assumption** used to simulate that timing effect.

At project level, WIEB applies to client-side contract-value work.

At activity level, WIEB applies only to the subcontracted share. Self-performed/direct cost is paid as incurred and is not delayed by WIEB.

WIEB changes timing, not the lifetime value of the work.

Use the user-facing term **Work in Excess of Billings (WIEB)**. Do not use `Billing Deferral` as a replacement label.

## 8. Time convention

The calculation engine works in integer model periods. The app is commonly used monthly, but the engine itself does not require a calendar month.

Within one scenario, timing inputs must use one consistent period convention.

Examples:

- payment period `2` means two model periods after billing;
- DLP `12` means the second retention release occurs twelve model periods after the first release point.

The financing rate is a rate per model period.

## 9. Financing and working capital

CashflowPot combines inflow and outflow into net cash flow and a cumulative cash balance.

When the cumulative balance is negative, the configured financing rate is applied to that negative balance for the model period. The current calculation does not add interest income to positive balances.

The cash-flow view is intended to make peak negative cash, working-capital need, funding duration, and financing exposure visible for decision-making.

## 10. Import/export and calculation authority

The backend calculation engine is authoritative for the financial forecast and backend validation.

The Flutter client can validate inputs early and present them clearly, but it must not maintain a conflicting calculation model.

Portable scenario files use the versioned `cashflowpot.cashflow` JSON format documented in [`reference/cashflow_json_format.md`](reference/cashflow_json_format.md).

Excel and other reporting outputs should present the calculated scenario; they should not silently introduce alternative formulas.

## 11. Product rules that must stay stable unless deliberately changed

1. A project can contain multiple independent scenarios.
2. New scenarios default to the Independent contract curve with a balanced S-curve.
3. Legacy scenarios with null independent-inflow settings remain activity-linked until changed.
4. Activities determine project execution duration and project outflow in both inflow modes.
5. Main-contract inflow terms are applied after the contract-value work profile is generated.
6. Self-performed cost does not use subcontract WIEB.
7. WIEB, retention, payment period, and DLP change timing, not underlying lifetime value.
8. Advance plus retention cannot exceed 100% on either the client or subcontract side.
9. Deleted activities do not participate in the current forecast.
10. The backend is authoritative for validation and calculation.
11. Individual activity selling values / markup allocation / Schedule of Values are not part of the current model and are not an assumed roadmap item.
12. A forecast is intended to be revised as information changes.

Exact formulas and validation limits are defined in [`reference/cashflow_model.md`](reference/cashflow_model.md).

## 12. Current product boundaries

The current calculation engine does not calculate schedule logic or critical path, delay entitlement, resource availability/productivity, detailed BOQ measurement, tax/currency/escalation/bond mechanisms, accounting statements, or activity-specific selling values.

Those subjects may affect the inputs or scenario assumptions, but they are not independently calculated by the current CashflowPot engine.

## 13. Brand and naming

Use **CashflowPot** in current product-facing documentation and copy.

CashflowPot is a Quollnet product. Quollnet should be visible as the parent ecosystem without overpowering the CashflowPot identity.

The public-site positioning should remain consistent with this document: construction cash-flow simulation/forecasting, contract terms and assumptions, revisable scenarios, and decision support for construction commercial/financial questions.

Last reviewed: 7 October 2026.
