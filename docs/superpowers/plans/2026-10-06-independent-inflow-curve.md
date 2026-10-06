# Independent Inflow Curve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable independent contract-value inflow curve to the CashflowPot backend while preserving activity-linked inflow as the fallback for existing/null-config scenarios.

**Architecture:** Add three nullable scenario columns and a schema-only CLI upgrade command. Refactor `CashflowCalculator` so contract-value work generation is selected independently from client cash-timing logic; API validation/import/export exposes the new fields without changing activity outflow.

**Tech Stack:** Flask, SQLAlchemy, pytest, existing `Work`/`CashflowCalculator` engine.

**Spec:** `docs/superpowers/specs/2026-10-06-independent-inflow-curve-design.md`

## Global Constraints

- Independent inflow is active only when `use_independent_inflow_curve is True` and `inflow_curve_type is not None`.
- New scenarios default to `True`, `"s_curve"`, and `0.0`.
- Existing rows are not backfilled; null curve settings preserve the activity-linked calculation.
- Project/execution duration remains derived from active activity work series.
- Activity outflow/subcontract calculations do not change.
- Client WIEB, advance, retention, payment delay, and DLP semantics do not change.

## Review Focus

- Existing rows with nullable new columns must calculate successfully and use activity-linked inflow.
- A false boolean must override non-null curve settings and remain activity-linked.
- `linear` must ignore stored skew while preserving it for later switching.
- Invalid non-null curve types and active-curve skew values must be rejected by API validation.
- Schema upgrade must add columns idempotently without updating existing row values.

---

### Task 1: Schema and model fields

**Files:**
- Modify: `q_flow/models/cashflow.py`
- Create: `q_flow/commands/add_independent_inflow_columns.py`
- Modify: `q_flow/__init__.py`
- Create: `tests/test_independent_inflow_schema.py`

**Interfaces:**
- Produces `Cashflow.use_independent_inflow_curve`, `Cashflow.inflow_curve_type`, `Cashflow.inflow_curve_skew`.
- Produces CLI command `add-independent-inflow-columns` that adds missing nullable columns only.

- [ ] Write failing tests asserting model defaults for new objects and schema-upgrade idempotence/null preservation.
- [ ] Run `pytest tests/test_independent_inflow_schema.py -v` and confirm failures are caused by missing fields/command.
- [ ] Add nullable SQLAlchemy columns with Python-side defaults `True`, `"s_curve"`, `0.0`; implement/register the schema-only CLI command using SQLAlchemy inspection plus `ALTER TABLE ... ADD COLUMN` without UPDATE statements.
- [ ] Run `pytest tests/test_independent_inflow_schema.py -v` and confirm pass.
- [ ] Commit schema/model task.

### Task 2: Calculator selection and independent contract work

**Files:**
- Modify: `q_flow/cashflow.py`
- Modify: `tests/test_cashflow_calculation_hardening.py`

**Interfaces:**
- Produces `CashflowCalculator.independent_contract_work() -> list`.
- Produces `CashflowCalculator.contract_work() -> list` selecting independent vs `factored_work()`.
- `CashflowCalculator.inflow()` consumes `contract_work()`.

- [ ] Write failing tests for null fallback, false-flag fallback, independent linear distribution, balanced/positive/negative S-curve behavior, contract-value sum invariant, and unchanged outflow.
- [ ] Run targeted calculator tests and confirm expected failures.
- [ ] Implement `independent_contract_work()` with existing `Work(duration, skew, contract_value, curve_type)` math and `contract_work()` with the exact activation rule; refactor `inflow()` to consume `contract_work()`.
- [ ] Run targeted calculator tests and existing cashflow calculation/model tests.
- [ ] Commit calculator task.

### Task 3: API validation and JSON import/export

**Files:**
- Modify: `q_flow/routes/cashflows.py`
- Modify: `tests/test_cashflow_import.py`
- Modify or create route validation tests as appropriate.

**Interfaces:**
- Scenario create/update accepts the three model fields through existing model-column update behavior.
- Import/export allowlist preserves the three fields.
- `_validate_cashflow()` enforces boolean/type/skew rules while allowing nullable legacy settings.

- [ ] Write failing tests for create/update validation, import preservation, and old import payload compatibility.
- [ ] Run targeted route/import tests and confirm expected failures.
- [ ] Add new fields to `_CASHFLOW_IMPORT_FIELDS`; extend `_validate_cashflow()` so non-null type is `s_curve|linear`, supplied flag is boolean, and skew is finite/strictly between -1 and 1 when independent mode is active.
- [ ] Run targeted route/import tests and confirm pass.
- [ ] Commit API task.

### Task 4: Canonical model documentation and regression verification

**Files:**
- Modify: `documentation/cashflow_model.md`

**Interfaces:**
- Documentation defines independent curve as the default for new scenarios and activity-linked fallback for null/disabled settings.

- [ ] Update sections covering contract-value allocation/project inflow to describe both methods, derived duration, activation rule, and unchanged client cash-timing transformation.
- [ ] Run `pytest tests/test_cashflow_calculation_hardening.py tests/test_cashflow_model.py tests/test_cashflow_import.py tests/test_independent_inflow_schema.py -v`.
- [ ] Run full `pytest` and report any failures by test name.
- [ ] Commit documentation/regression task.
