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

## 5. Not an assumed roadmap item

The following is **not** an approved default future direction:

- per-activity selling values;
- per-activity markup allocation; or
- a detailed Schedule of Values model.

The current Independent contract curve deliberately separates main-contract value timing from activity cost allocation. Do not reintroduce an old “activity-specific selling value and markup allocation” roadmap statement without a new product decision.

## 6. How ideas graduate from future to current

When a future item is implemented:

1. update the relevant current-product document (`product.md`, `technical.md`, `ui-ux.md`, or `deployment.md`);
2. update any affected detailed reference;
3. add/adjust regression tests;
4. remove or rewrite the item here so `future.md` does not describe an already-live feature as future work.

Last reviewed: 7 October 2026.
