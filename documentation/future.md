# CashflowPot future direction

This file records directions that have been discussed and approved as useful future work but are **not current product behavior** unless they are later implemented and moved into the current-product documentation.

Keep this list selective. Ideas that were merely discussed, superseded, rejected, or already implemented should not remain here as roadmap promises.

Current implemented behavior — including Work vs Scheduled Cost Activities, Independent/Activity-linked inflow, financing facilities, facility KPIs, and the full Excel cashflow sections — belongs in `product.md`, `technical.md`, `ui-ux.md`, and `reference/`.

## 1. AI-assisted project and scenario setup

### Goal

Allow a user to describe a construction project in normal language and provide a small amount of known information, such as:

- project scope/description;
- contract value;
- expected duration;
- project type; and
- known commercial/financing conditions.

AI can then propose a starting cash-flow model for user review, including items such as:

- Work Activities;
- Scheduled Cost Activities where appropriate;
- estimated Activity costs;
- Activity duration/timing or manual schedules;
- Work distribution/curve assumptions;
- subcontracted share;
- client commercial terms/forecast assumptions; and
- starting financing-facility definitions when the user asks for funding modelling.

### Boundary

AI is an **input assistant**, not an alternative cash-flow engine.

The generated proposal must be reviewable/editable by the user. After review, the normal CashflowPot data model, backend validation, and calculation engine remain authoritative.

Portable CashflowPot JSON is the natural machine-readable target for AI-generated scenarios because it represents scenario inputs rather than calculated results.

### Current preparation status

The current data model now separates:

- Activity category/template (`activity_type`);
- Activity mode (`work` / `scheduled_cost`); and
- Work distribution (`s_curve` / `linear` / `manual`).

That separation removes the earlier ambiguity that would have made AI-generated Activity definitions unreliable.

Before AI-assisted setup is shipped, the proposal/review UI should still use semantic user-facing concepts rather than legacy backend names and should make uncertain/guessed inputs obvious to the user.

## 2. Full scenario report

The current Excel export is a professional working cashflow report with:

- project/scenario identification;
- contract/key-term context;
- Activity schedule;
- key metrics;
- charts;
- full Project Cashflow;
- full Facilities section;
- Cash Position; and
- reconciliation/notes.

A future **full scenario report** can go beyond the current workbook and become a more narrative decision document suitable for forwarding to management, employers, banks, lenders, or investment/finance reviewers.

The intended direction includes:

- concise executive-summary page;
- clearer separation of inputs, assumptions, forecast results, and interpretation;
- selected charts on dedicated report/chart sheets where appropriate;
- facility utilization/adequacy commentary;
- scenario comparison summaries;
- professionally composed print/PDF output; and
- optional narrative explanation tied to calculated results.

The report must use the existing CashflowPot calculation results and formulas rather than introducing a second financial model in the export/report layer.

## 3. AI-assisted report narrative

Once the scenario report structure is stable, AI may assist with a short narrative/executive summary explaining the forecast, for example:

- peak funding requirement;
- when the funding requirement occurs;
- major timing drivers;
- effect of retention/payment/WIEB assumptions;
- facility utilization and residual debt;
- Cash after debt settlement;
- sensitivity between compared scenarios; and
- issues a lender or management reviewer may want to challenge.

Any narrative must remain clearly tied to the calculated scenario and must not present model assumptions as guaranteed future outcomes.

## 4. Scenario comparison and decision support

CashflowPot already supports multiple independent scenarios per project. A future reporting/analysis layer can make scenario comparison more explicit for decisions such as:

- Tender / Base / Current / Recovery comparisons;
- changed payment terms;
- alternative subcontract strategies;
- front-loaded vs back-loaded execution or contract curves;
- different Scheduled Cost procurement/payment timing;
- alternative facility structures, limits, or repayment methods; and
- financing sensitivity.

Comparison should build on the existing scenario model rather than create a separate parallel forecast structure.

Useful future comparison outputs could include:

- delta in peak funding requirement;
- delta in financing cost;
- delta in peak facility usage;
- final outstanding debt;
- Cash after debt settlement; and
- period-by-period cash-position differences.

## 5. Financing enhancements beyond the current facility engine

Financing facilities are **current product behavior**, not future work. The current engine already supports scheduled/automatic/PPC-linked draws, revolving/non-revolving limits, multiple repayment methods, interest/fees, facility outstanding, KPIs, and full cashflow presentation.

Future financing work should therefore be limited to capabilities that are genuinely not implemented.

### Potential Activity/facility linking

A future optional link could associate a financing draw with a Scheduled Cost Activity, for example an LC funding a specific equipment/material payment.

The purpose would be traceability/convenience, not a new financial model. The link must not double-count cash:

- Scheduled Cost remains project outflow;
- facility draw remains financing inflow.

CashflowPot should not infer procurement relationships unless the user explicitly creates the link.

### Guarantee-only / non-cash facilities

A guarantee-only LC currently stays outside cashflow because no cash draw occurs.

A future facility/exposure layer could track non-cash guarantees, bonds, or contingent limits separately from cashflow without pretending they are cash receipts.

### Explicit facility maturity / post-horizon closeout

The current model does not infer facility maturity or invent future interest beyond the modeled horizon.

A future enhancement could let the user specify maturity/balloon repayment or request an explicit debt-closeout extension of the model horizon.

This must remain user-driven because bank terms differ materially.

### Facility adequacy analysis

A future analysis layer can explain whether facilities are adequate by:

- amount;
- timing;
- availability window;
- revolving capacity;
- repayment timing; and
- residual unfunded shortfall.

This should explain the existing engine result rather than create a different calculation.

## 6. Public-site / educational expansion

The current public site explains CashflowPot and its methodology. Future content can expand with practical construction-commercial examples such as:

- how WIEB changes cash timing;
- Work vs Scheduled Cost examples;
- client payment-delay scenarios;
- overdraft vs PPC Discount vs LC examples;
- revolving vs non-revolving capacity; and
- bid/no-bid financing checks.

Any educational examples must stay consistent with the current calculation references and avoid presenting illustrative defaults as universal practice.

## 7. Not an assumed roadmap item

The following is **not** an approved default future direction:

- per-Activity selling values;
- per-Activity markup allocation; or
- a detailed Schedule of Values model.

The current Independent contract curve deliberately separates main-contract value timing from Activity cost allocation. Do not reintroduce an old “Activity-specific selling value and markup allocation” roadmap statement without a new product decision.

Likewise, CashflowPot is not assumed to evolve into a replacement for Primavera/MS Project, ERP, accounting, detailed BOQ measurement, or resource-loaded planning software.

## 8. How ideas graduate from future to current

When a future item is implemented:

1. update the relevant current-product document (`product.md`, `technical.md`, `ui-ux.md`, or `deployment.md`);
2. update any affected detailed reference;
3. add/adjust regression tests;
4. update portable JSON documentation if the source format changes; and
5. remove or rewrite the item here so `future.md` does not describe already-live behavior as future work.

Last reviewed: 14 October 2026.
