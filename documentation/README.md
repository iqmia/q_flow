# CashflowPot documentation

This folder is the source of truth for the **current product**. Start here when returning to CashflowPot after time away, when changing a rule, or when checking whether a behavior is current or only planned.

## Read order

1. [`product.md`](product.md) — what CashflowPot is, who it is for, the model boundaries, terminology, and product/business rules.
2. [`technical.md`](technical.md) — how the repositories, backend, QAuth, data model, calculation engine, import/export, and public site fit together.
3. [`ui-ux.md`](ui-ux.md) — user-facing terminology and interface rules that should stay consistent across the Flutter app, public site, exports, and future AI setup.
4. [`deployment.md`](deployment.md) — production topology and the exact build/deploy workflow for the public site, Flutter app, and Passenger API.
5. [`future.md`](future.md) — approved directions that are **not current product behavior yet**.

## Detailed references

The overview documents above should stay readable. Exact formulas, file formats, and security mechanics live in `reference/`:

- [`reference/cashflow_model.md`](reference/cashflow_model.md) — canonical calculation rules, formulas, defaults, validation, and invariants.
- [`reference/cashflow_json_format.md`](reference/cashflow_json_format.md) — portable `.cashflowpot.json` import/export format.
- [`reference/security.md`](reference/security.md) — current QAuth/JWT authentication, app identity, project-unit authorization, and token refresh behavior.

When a detailed reference and an overview conflict, verify the implementation and fix both documents. Do not preserve a contradiction merely because one document is older.

## Current product vs development history

`documentation/` describes **what CashflowPot is today** and the approved future direction.

The directories below serve a different purpose:

- `docs/superpowers/specs/` — design decisions for individual changes.
- `docs/superpowers/plans/` — implementation plans for those changes.

Those files are useful history, but they are not the current product definition. A superseded spec or plan must not override this documentation or the current tested implementation.

## Documentation rule

When a change affects product meaning, calculations, user-facing terminology, architecture, deployment, security, or an approved future direction, update the relevant file here in the same change. Avoid scattering current rules through temporary plans, chat notes, or code comments only.

Last reviewed: 7 October 2026.
