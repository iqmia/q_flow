# CashflowPot UI and UX rules

This document defines the language and interface conventions that should stay consistent across the Flutter app, public website, exports, and future AI-assisted setup.

It is not a screen-by-screen specification. Detailed implementation can evolve as long as these semantic rules remain clear.

## 1. Design goal

A construction/commercial user should be able to understand what a field changes without needing to know the backend schema or read a calculation manual first.

The interface should make four layers easy to distinguish:

1. **Execution** — when physical/work Activities are expected to occur.
2. **Project cost** — Work Activity outflow plus Scheduled Cost.
3. **Contract/commercial and financing terms** — how work becomes billings/receipts and how facilities fund the project.
4. **Cash position** — total inflow, total outflow, net cash, closing cash, debt, and funding requirement.

Prefer construction/commercial language over implementation language.

## 2. Product terminology

Use **CashflowPot** as the product name.

Preferred user-facing terms include:

| Meaning | Preferred UI term |
| --- | --- |
| Total client value | Contract value |
| Main-contract inflow method | Inflow forecast method |
| Default inflow mode | Independent contract curve |
| Compatibility/alternative mode | Activity-linked inflow |
| Physical/cost-loaded activity | Work |
| Direct period-based project expenditure | Scheduled Cost |
| Work distribution | S-curve / Linear / Manual |
| S-curve timing | Back-loaded / Balanced / Front-loaded |
| Client billing delay assumption | Work in Excess of Billings (WIEB) |
| Invoice-to-cash delay | Payment period |
| Retention tail period | Defects Liability Period (DLP) |
| Activity cost | Estimated activity cost |
| Activity outsourced portion | Subcontracted share |
| Activity pre-start zero-work time | Pre-work period |
| Client cash received | Project inflow / Client PPC receipts |
| Work + Scheduled Cost outflow | Project cost |
| Facility money received | Draw |
| Facility principal paid back | Repayment |
| Facility financing charges | Interest & fees |
| Facility debt remaining | Outstanding balance |
| Model result before cumulative balance | Net cash flow |
| Most negative pre-financing cash | Peak funding requirement |
| Funded cumulative result | Closing cash balance |
| Final cash less outstanding principal | Cash after debt settlement |

At first use, expand abbreviations such as WIEB and DLP.

Do not use `Billing Deferral` as a replacement for WIEB.

## 3. Activity mode and distribution

The UI must distinguish **what the Activity is** from **how it is calculated**.

### Activity type/category

Category/template names such as Structure, MEP, Facade, and General can suggest defaults, but they must not appear to be the calculation switch.

### Work

Work Activities represent physical/cost-loaded execution and can use:

- S-curve;
- Linear; or
- Manual schedule.

Generated Work uses entered cost and duration. Manual Work derives cost and duration from the schedule.

Work Activities can expose subcontract terms where applicable.

### Scheduled Cost

Scheduled Cost represents direct project expenditure by period and does not create physical/billable work.

When `Scheduled Cost` is selected:

- hide fields that do not affect it, including Work distribution/skew, subcontract terms, pre-work, WIEB, advance, retention, payment delay, and DLP;
- derive cost and duration from the entered schedule;
- present the schedule using **absolute user-facing project periods**;
- do not expose the internal `start = firstPeriod - 1` conversion as ordinary UI language.

A Scheduled Cost switch back to Work should preserve the previously entered Work distribution settings where practical rather than destroying them.

## 4. Manual schedules

Manual Work and Scheduled Cost both use dense backend schedules but have different user semantics.

### Manual Work

The schedule is Activity-local and is combined with the Activity Start period.

A compact entry such as:

```text
1:500, 4:900
```

means local Activity periods 1 and 4 have cost/work values and intermediate local periods are zero.

### Scheduled Cost

The schedule editor uses absolute project periods, for example:

```text
4:25000, 7:75000
```

means project P4 and P7.

The client converts that to the backend's start offset and dense local schedule. The user should not have to calculate that offset.

## 5. Contract terms vs forecasting assumptions

The UI should not call every input an assumption.

### Contract/commercial terms

Use contract/commercial wording for inputs such as:

- advance payment and recovery;
- retention;
- retention release;
- payment period; and
- DLP.

### Forecasting assumptions

Use forecasting-assumption wording for modeled behavior such as:

- WIEB percentage;
- Work execution curve/timing;
- independent contract-curve timing;
- subcontracted share where it is not fixed by the commercial arrangement.

Where the user knows an exact contractual value, the interface should present it as a term even though the calculation engine ultimately stores a number in the same way as an estimate.

## 6. Inflow method presentation

New scenarios default to **Independent contract curve** with an S-curve and balanced timing.

The user should be able to understand the difference without backend field names.

### Independent contract curve

Explain that contract value follows its own curve over **Work duration**, while all Activities still contribute to project outflow according to their mode.

Scheduled Cost does not extend Work duration or the independent contract-value curve.

### Activity-linked inflow

Explain that contract value follows the combined **Work Activity** execution/cost profile.

Scheduled Cost is excluded from the Work-cost denominator and does not create client value-of-work.

Do not expose these backend fields as labels:

```text
use_independent_inflow_curve
inflow_curve_type
inflow_curve_skew
```

For S-curve timing, show semantic labels such as Back-loaded, Balanced, and Front-loaded. Numeric skew is an implementation/input detail and should only be exposed where it adds real value.

## 7. WIEB explanation

A short user explanation should stay close to this meaning:

> The estimated share of work performed in a period that is not yet billable and is carried into the following billing period.

At project level it applies to client-side contract-value work.

At Work Activity level it applies only to the subcontracted share. Self-performed cost is paid as incurred.

Scheduled Cost does not use WIEB.

Avoid wording that implies WIEB changes total project value or total activity cost. It changes timing.

## 8. Project, scenario, and activity hierarchy

The UI should make the hierarchy explicit:

```text
Project
  └── Cash-flow scenarios
        └── Activities
              ├── Work
              └── Scheduled Cost
```

A Project is not itself one cash-flow scenario. A project can contain multiple scenarios such as Base, Tender, Current, or Recovery.

When creating a project, CashflowPot creates a Base scenario. Scenario-level contract terms, financing facilities, and assumptions can later diverge independently.

## 9. Financing facility setup

A facility has one user-facing name used in the cashflow table. The preset/product type is a suggested model, not a second competing display name.

Common facility inputs include:

- facility name;
- facility type/preset;
- first available period;
- last available period;
- optional limit;
- interest rate;
- fees;
- revolving setting;
- draw method; and
- repayment method.

Method-specific fields should appear only when relevant.

Examples:

- **Cashflow sweep priority** appears only for cashflow-sweep repayment.
- Scheduled-draw total/derived values should be visibly **read-only/calculated** rather than looking like editable fields.
- A blank optional limit must remain possible when the model supports unlimited capacity.

Facility presets are editable starting points, not hard-coded banking products.

## 10. Financing terminology and behavior

The UI must not imply that a requested scheduled draw is project cost.

Use these concepts consistently:

- Draw = actual facility inflow.
- Repayment = principal outflow.
- Interest & fees = financing-cost outflow.
- Outstanding balance = principal balance, not cashflow.

For limited facilities, the UI should make the effect of `revolving` understandable:

- revolving repayment restores capacity;
- non-revolving repayment does not restore cumulative draw capacity.

The availability start/end is a draw window, not debt maturity.

## 11. PPC Discount presentation

PPC Discount uses two different project series:

- discount draw is based on the **PPC issued/certificate** value;
- repayment is based on **client PPC receipts** after the project payment delay.

Do not label these as the same event.

## 12. Values and percentages

The API stores percentage-like values as fractions (`0.10 = 10%`). The UI should display and accept normal percentages (`10%`) and perform conversion at the client boundary.

Do not show raw API fractions unless the context is explicitly technical.

Percentage text should be formatted intentionally rather than using raw floating-point `.toString()` values that can expose artifacts such as `0.9000000000000001`.

## 13. Periods

The calculation engine uses generic model periods, although normal usage is monthly.

The interface should keep period meaning consistent within one scenario. If the product presents months, all dependent timing inputs and financing-rate language should be understandable as monthly values.

Do not mix annual financing rates with monthly model periods without an explicit conversion.

### Display convention

All user-facing periods are **1-based**:

```text
P1, P2, P3, ...
```

This applies to:

- Activity Start;
- Work starts;
- Scheduled Cost period pairs;
- table headings;
- chart tooltips/axis labels; and
- KPI period labels.

Backend zero-based offsets remain an implementation detail.

## 14. Cashflow result table

The current financial result table is grouped as:

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

Major sections should be visually separated. Section rows may repeat period numbers to keep long horizontal tables readable.

Activity result rows should use compact two-line labels:

- `Planned cost` + Activity name for Work;
- `Scheduled cost` + Activity name for Scheduled Cost;
- `Outflow` + Activity name.

Facility rows should keep the facility name visually associated with its four result rows without consuming unnecessary horizontal width.

## 15. Result definitions

Use semantic result names rather than legacy API keys.

| API / implementation | UI meaning |
| --- | --- |
| `workflow` | Cost-loaded Work execution profile |
| `inflow` | Project inflow / Client PPC receipts |
| `outflow` | Project cost / project payments |
| `netflow` | Pre-facility project net cash flow |
| `facility_inflow` | Facility draws |
| `facility_outflow` | Facility principal repayments |
| `facility_interest` + `facility_fees` | Interest & fees |
| `funded_netflow` | Total/funded net cash flow |
| `outflow_with_interest` | Closing funded cash balance |

Do not expose the legacy `outflow_with_interest` name to users.

## 16. KPI presentation

The compact KPI set is:

- Project cost;
- Financing cost, with interest + fees detail;
- Total cost;
- Peak funding requirement, with period when applicable;
- Peak facility usage;
- Outstanding facilities;
- Closing cash balance;
- Cash after debt settlement.

Supporting information includes Work duration and financial horizon.

Definitions should follow backend summary fields. In particular:

```text
Cash after debt settlement
= final cash balance - final outstanding facility principal
```

Peak funding requirement is zero when pre-financing cash never goes negative.

On responsive layouts, KPI cards should remain compact and readable rather than stretching into oversized full-width cards.

## 17. Numeric display and authoritative totals

Period cells may use practical display precision, but totals should use authoritative backend/model values when available.

Do not calculate a displayed Activity total by summing rounded period labels. For example:

```text
12 displayed periods × 833.33 != authoritative cost 10,000.00
```

The Activity total should show the authoritative `10,000.00` value.

The same principle applies to Project inflow and Project cost totals.

### Large-number scaling

The UI may scale large values to keep tables compact. Current display convention uses the unscaled value up to `999,999.99`, then `K`, then `M` as needed, while preserving the exact value through tooltip/detail presentation.

Examples:

```text
250,780.25       -> 250,780.25
1,750,000        -> 1,750.00K
250,780,250      -> 250,780.25K
999,999,990      -> 999,999.99K
1,250,500,120    -> 1,250.50M
```

Negative signs are preserved.

## 18. Excel export conventions

The current Excel workbook is a professional working cashflow report, not a second calculation engine.

Preserve these conventions unless deliberately redesigned:

- A4 landscape print setup and existing tight margins;
- compatible A3 printing;
- existing column widths;
- no gridlines;
- no frozen panes;
- numeric cells remain numeric;
- zeros can be visually blank where appropriate;
- negative values remain visually distinct;
- one decimal place for cashflow/report amounts;
- Activity schedule remains in the report;
- full lower cashflow is Project Cashflow → Facilities → Cash Position;
- Interest + Fees is one facility row;
- facility blocks use subtle repeating pastel backgrounds across the full timeline;
- the facility name can occupy a vertically merged first-column block;
- cashflow row title area uses merged B:E cells and row total uses merged F:G cells;
- borders must cover every physical cell, including cells inside merged ranges;
- charts must reference total inflow/outflow and closing cash position rather than only project cashflow;
- Key Metrics includes Cash after debt settlement.

Excel formulas should reconcile to authoritative totals and calculated facility results; they must not reconstruct facility banking rules independently where the backend already provides the canonical result.

## 19. Defaults are starting points

Defaults, Activity templates, and facility presets are intended to speed up modelling. They are not statements about universal construction or banking practice.

The UI should allow users to review and change them and should not present default percentages or facility terms as recommended contract conditions.

## 20. Validation behavior

Validate early in the client so the user receives an understandable message near the field, but keep the backend authoritative.

Important constraints include:

- generated Work Activity cost > 0;
- generated Work duration > 0;
- Manual Work/Scheduled Cost schedule total > 0;
- schedule values finite and non-negative;
- percentage values between 0% and 100%;
- advance + retention <= 100%;
- timing values valid for their user-facing 1-based or backend-offset representation;
- curve skew strictly between -1 and 1.

Translate backend validation into user language where possible.

## 21. Public site positioning

The public website should describe the product as construction cash-flow simulation/forecasting and focus on decisions such as tendering, financing, lender review, and reforecasting.

Approved positioning themes include:

- turn project execution, costs, contract terms, financing, and assumptions into a cash-flow forecast;
- a forecast designed to be revised;
- build the cash-flow view needed for the decision now, then revise it as the project changes.

Do not position CashflowPot as a lesser or simplified replacement for planning, ERP, accounting, or cost-control products.

### Public metadata and social sharing

Search metadata, structured data, and social-sharing copy must match the visible current product positioning. Do not create a hidden machine-only product claim that contradicts what a human reader sees on the page.

All public pages currently use the shared social image:

```text
https://cashflowpot.com/assets/images/cashflowpot-og.webp
```

The Flutter `/app/` shell is shareable but intentionally non-indexable; it remains crawlable so its `noindex, follow` directive can be read. `/api/` is not a discovery surface.

`llms.txt` is a supplementary machine-readable content map, not a substitute for visible explanatory content, canonical URLs, the sitemap, or normal indexing controls.

## 22. AI-assisted setup boundary

AI-assisted setup is a future input-assistance workflow, not a replacement calculation engine.

When implemented, AI may propose Work/Scheduled Cost Activities, costs, durations, schedules, subcontracted shares, financing starting points, and other assumptions for review. The user must be able to review/edit the proposal before relying on it, and the normal CashflowPot backend calculation engine remains authoritative.

See [`future.md`](future.md).

## 23. Implementation names vs user-facing names

Legacy implementation names can remain where compatibility requires them, but they must not leak into ordinary UI copy when a clearer commercial term exists.

For the detailed backend-to-semantic naming map, see [`reference/cashflow_model.md`](reference/cashflow_model.md).

Last reviewed: 14 October 2026.
