# CashflowPot Documentation Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile all current CashflowPot application documentation with the implemented activity modes, Scheduled Cost, financing facilities, KPI/presentation model, and Excel export behavior.

**Architecture:** Keep `q_flow/documentation/` as the current-product source of truth. Update overview documents first, then detailed references and roadmap boundaries, then repo READMEs/cross-links. Historical files under `docs/superpowers/specs/` and older `docs/superpowers/plans/` remain historical and are not rewritten as current documentation.

**Tech Stack:** Markdown documentation, Flask/q_flow implementation references, Flutter CashflowPot implementation references.

**Spec:** `docs/superpowers/specs/2026-10-13-activity-modes-scheduled-cost-design.md` and `docs/superpowers/specs/2026-10-13-financing-closeout-and-cashflow-presentation-design.md`

## Global Constraints

- Backend calculation implementation remains authoritative for formulas and facility sequencing.
- Current-product documentation must not describe implemented financing facilities or Scheduled Cost as future work.
- `activity_type` is category/template only; calculation mode/distribution are separate.
- Scheduled Cost affects project cost/outflow/financing but not physical work, PPC, or work duration.
- User-facing periods are 1-based; backend offsets remain 0-based.
- Cashflow presentation is Project Cashflow → Facilities → Cash Position.
- Excel preserves numeric values/formulas and existing print geometry while presenting the full cashflow.

## Review Focus

- PPC issued vs PPC receipt semantics for PPC Discount.
- Work duration vs financial horizon.
- Revolving vs non-revolving facility capacity.
- Canonical totals vs rounded period display totals.
- Portable JSON Version 1 compatibility.

---

### Task 1: Product and UI overview

**Files:**
- Modify: `documentation/product.md`
- Modify: `documentation/ui-ux.md`

- [x] Reframe Activities as Work or Scheduled Cost and document their different calculation effects.
- [x] Document financing facilities as current product behavior and define the Project Cashflow / Facilities / Cash Position presentation.
- [x] Document current KPIs, 1-based period display, authoritative totals, amount scaling, and read-only/calculated fields.
- [x] Update review dates.

### Task 2: Technical and calculation references

**Files:**
- Modify: `documentation/technical.md`
- Modify: `documentation/reference/cashflow_model.md`
- Modify: `documentation/reference/financing_facilities.md`
- Modify: `documentation/reference/cashflow_json_format.md`

- [x] Reconcile Activity source fields, snapshot keys, summary/KPI fields, and duration semantics.
- [x] Reconcile financing draw/repayment/capacity sequencing and current cashflow presentation naming.
- [x] Document display-vs-calculation precision and canonical totals where relevant.
- [x] Confirm JSON v1 compatibility and Scheduled Cost/Manual Work schedule semantics.

### Task 3: Current/future boundary and documentation index

**Files:**
- Modify: `documentation/future.md`
- Modify: `documentation/README.md`
- Review/update: `documentation/deployment.md`
- Review/update: `documentation/reference/security.md`

- [x] Remove implemented financing facilities from future-work framing; retain only genuinely future facility/report improvements.
- [x] Add financing-facilities reference to the documentation index.
- [x] Record that deployment/security were reviewed against this feature and are behaviorally unchanged.

### Task 4: Repository READMEs

**Files:**
- Modify: `README.md` in `q_flow`
- Modify: `README.md` in `iqmia/cashflowpot`

- [x] Update high-level product wording for Work/Scheduled Cost and financing facilities.
- [x] Correct canonical documentation links.
- [x] Keep q_flow as calculation/documentation authority and Flutter as presentation/input/export client.

### Task 5: Verification

- [x] Review current documentation for stale current/future terminology and update the documentation contract test, including `financing_facilities.md`.
- [ ] Run backend documentation tests / full `pytest` locally.
- [ ] Run Flutter tests locally because the README-only client documentation change sits on the active feature branch with the existing UI/Excel changes.

## Verification status

No GitHub Actions run is associated with the latest documentation commit. Local backend/Flutter test execution is therefore still required before the feature branch is considered fully verified.
