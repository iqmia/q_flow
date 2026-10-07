# CashflowPot UI and UX rules

This document defines the language and interface conventions that should stay consistent across the Flutter app, public website, exports, and future AI-assisted setup.

It is not a screen-by-screen specification. Detailed implementation can evolve as long as these semantic rules remain clear.

## 1. Design goal

A construction/commercial user should be able to understand what a field changes without needing to know the backend schema or read a calculation manual first.

The interface should make three layers easy to distinguish:

1. **Execution** — when activity work and cost are expected to occur.
2. **Contract terms and forecasting assumptions** — how work becomes billings, receipts, and payments.
3. **Cash position** — inflow, outflow, net cash, cumulative balance, and funding requirement.

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
| Independent curve distribution | Linear / S-curve |
| S-curve timing | Back-loaded / Balanced / Front-loaded |
| Client billing delay assumption | Work in Excess of Billings (WIEB) |
| Invoice-to-cash delay | Payment period |
| Retention tail period | Defects Liability Period (DLP) |
| Activity cost | Estimated activity cost |
| Activity outsourced portion | Subcontracted share |
| Activity pre-start zero-work time | Pre-work period |
| Model result before cumulative balance | Net cash flow |
| Most negative cumulative cash | Peak negative cash |
| Funding need | Working capital / funding requirement |

At first use, expand abbreviations such as WIEB and DLP.

Do not use `Billing Deferral` as a replacement for WIEB.

## 3. Contract terms vs forecasting assumptions

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
- activity execution curve/timing;
- independent contract-curve timing;
- subcontracted share where it is not fixed by the commercial arrangement.

Where the user knows an exact contractual value, the interface should present it as a term even though the calculation engine ultimately stores a number in the same way as an estimate.

## 4. Inflow method presentation

New scenarios default to **Independent contract curve** with an S-curve and balanced timing.

The user should be able to understand the difference without backend field names:

### Independent contract curve

Explain that contract value follows its own curve over the activity-derived execution duration, while activities still drive project outflow.

### Activity-linked inflow

Explain that contract value follows the combined activity execution/cost profile.

Do not expose these backend fields as labels:

```text
use_independent_inflow_curve
inflow_curve_type
inflow_curve_skew
```

For S-curve timing, show semantic labels such as Back-loaded, Balanced, and Front-loaded. Numeric skew is an implementation/input detail and should only be exposed where it adds real value.

## 5. WIEB explanation

A short user explanation should stay close to this meaning:

> The estimated share of work performed in a period that is not yet billable and is carried into the following billing period.

At project level it applies to client-side contract-value work.

At activity level it applies only to the subcontracted share. Self-performed cost is paid as incurred.

Avoid wording that implies WIEB changes total project value or total activity cost. It changes timing.

## 6. Project, scenario, and activity hierarchy

The UI should make the hierarchy explicit:

```text
Project
  └── Cash-flow scenarios
        └── Activities
```

A Project is not itself one cash-flow scenario. A project can contain multiple scenarios such as Base, Tender, Current, or Recovery.

When creating a project, CashflowPot creates a Base scenario. Scenario-level contract terms and assumptions can later diverge independently.

## 7. Values and percentages

The API stores percentage-like values as fractions (`0.10 = 10%`). The UI should display and accept normal percentages (`10%`) and perform conversion in the client boundary.

Do not show raw API fractions unless the context is explicitly technical.

Money and numeric output should be formatted consistently and should not imply precision greater than the model supports.

## 8. Periods

The calculation engine uses generic model periods, although normal usage is monthly.

The interface should keep period meaning consistent within one scenario. If the product presents months, all dependent timing inputs and financing-rate language should be understandable as monthly values.

Do not mix annual financing rates with monthly model periods without an explicit conversion.

## 9. Results and KPIs

Use semantic result names rather than legacy API keys.

| API / implementation | UI meaning |
| --- | --- |
| `workflow` | Cost-loaded work / execution cost profile |
| `inflow` | Cash inflow / receipts |
| `outflow` | Cash outflow / payments |
| `netflow` | Net cash flow |
| `outflow_with_interest` | Cumulative cash balance after financing |

Useful decision outputs include:

- total inflow;
- total direct/estimated activity cost;
- self-performed cost;
- subcontracted cost;
- financing cost;
- cumulative balance;
- peak negative cash / working-capital requirement;
- execution duration; and
- financial horizon.

Labels should describe what the number means to the user rather than reproduce database/API names.

## 10. Defaults are starting points

Defaults and activity presets are intended to speed up modelling. They are not statements about universal construction practice.

The UI should allow users to review and change them and should not present default percentages as recommended contract conditions.

## 11. Validation behavior

Validate early in the client so the user receives an understandable message near the field, but keep the backend authoritative.

Important constraints include:

- activity cost > 0;
- duration > 0;
- percentage values between 0% and 100%;
- advance + retention <= 100%;
- timing integers >= 0;
- curve skew strictly between -1 and 1.

Translate backend validation into user language where possible.

## 12. Public site positioning

The public website should describe the product as construction cash-flow simulation/forecasting and focus on decisions such as tendering, financing, lender review, and reforecasting.

Approved positioning themes include:

- turn project execution, contract terms, and assumptions into a cash-flow forecast;
- a forecast designed to be revised;
- build the cash-flow view needed for the decision now, then revise it as the project changes.

Do not position CashflowPot as a lesser or simplified replacement for planning, ERP, accounting, or cost-control products.

### Public metadata and social sharing

Search metadata, structured data, and social-sharing copy must match the visible current product positioning. Do not create a hidden machine-only product claim that contradicts what a human reader sees on the page.

All public pages currently use the shared social image:

```text
https://cashflowpot.com/assets/images/cashflowpot-og.webp
```

Open Graph and Twitter descriptions should use the same clear construction cash-flow language as the visible page. The Flutter `/app/` shell is shareable but intentionally non-indexable; it remains crawlable so its `noindex, follow` directive can be read. `/api/` is not a discovery surface.

`llms.txt` is a supplementary machine-readable content map, not a substitute for visible explanatory content, canonical URLs, the sitemap, or normal indexing controls.

## 13. AI-assisted setup boundary

AI-assisted setup is a future input-assistance workflow, not a replacement calculation engine.

When implemented, AI may propose activities, cost shares, durations, subcontracted shares, and starting assumptions for review. The user must be able to review/edit the proposal before relying on it, and the normal CashflowPot backend calculation engine remains authoritative.

See [`future.md`](future.md).

## 14. Implementation names vs user-facing names

Legacy implementation names can remain where compatibility requires them, but they must not leak into ordinary UI copy when a clearer commercial term exists.

For the detailed backend-to-semantic naming map, see [`reference/cashflow_model.md`](reference/cashflow_model.md).

Last reviewed: 7 October 2026.
