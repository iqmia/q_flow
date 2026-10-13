# Activity Modes and Scheduled Cost Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate activity category from distribution behavior, add manual work and scheduled-cost activities, preserve existing payment logic, and keep activity-linked inflow based only on physical work activities.

**Architecture:** `Activity` gains `activity_mode`, `distribution_type`, and `cost_schedule_json`. `Activity_cf` normalizes one base marginal series for generated/manual work and a direct outflow series for scheduled cost; `CashflowCalculator` keeps work activities separate from all activity outflows. Existing rows remain compatible through runtime inference, while portable JSON and Flutter gain explicit fields.

**Tech Stack:** Flask, SQLAlchemy, SQLite/PostgreSQL-compatible schema migration, pytest, Flutter/Dart.

**Spec:** `docs/superpowers/specs/2026-10-13-activity-modes-scheduled-cost-design.md`

## Global Constraints

- Existing Activity rows must calculate without destructive data migration.
- `activity_type` is template/category only after this change.
- New defaults: `activity_mode="work"`, `distribution_type="s_curve"`, `cost_schedule_json=null`.
- Legacy `activity_type="linear"` with no distribution field must still calculate linearly.
- Manual work and scheduled cost use a dense local list; `start` remains a separate project offset.
- Manual/scheduled-cost `cost=sum(schedule)` and `duration=len(schedule)` are server-authoritative.
- `cash_flow_json` remains calculated output with `marginal_work` and `marginal_out_flow` for every mode.
- Scheduled-cost activities affect project cost/outflow but not project work, billed work, or work duration.
- Remove active-model/API/Flutter use of `mobilization`, `profit`, `subcontractors_retention`, Activity `interest_rate`, and `compounding_period`; keep `mobilization_period`.
- Portable `cashflowpot.cashflow` version 1 files without the new fields must remain importable.
- Flutter tests will be run by the user; backend tests should be run where the Python environment is available.

## Review Focus

- Legacy `activity_type="linear"` row with null new fields must remain linear and must not be reclassified as a category during calculation.
- Empty/null schedules must be rejected for manual work and scheduled cost but allowed for generated work.
- Schedule values containing negatives, booleans, NaN/Inf, or a zero-only total must be rejected.
- A scheduled cost later than the last work activity must extend project outflow/financial horizon without extending `workflow` or independent inflow work duration.
- A mixed manual-work + scheduled-cost scenario must preserve total direct cost while activity-linked inflow scales only work cost to contract value.

---

### Task 1: Backend Activity schema, normalization, and validation

**Files:**
- Modify: `q_flow/models/activity.py`
- Modify: `q_flow/routes/activities.py`
- Create: `tests/test_activity_modes.py`
- Add/register schema migration command following the existing independent-inflow migration pattern.

**Interfaces:**
- Produces `Activity.activity_mode`, `Activity.distribution_type`, `Activity.cost_schedule_json`.
- Produces helpers for effective legacy mode/distribution and schedule normalization used by calculator/import routes.

- [ ] Write failing backend tests for defaults, legacy linear inference, schedule-required validation, invalid schedule values, and normalization of cost/duration from a valid schedule.
- [ ] Run `pytest tests/test_activity_modes.py -v` and confirm failures are caused by missing fields/behavior.
- [ ] Add nullable-compatible columns/defaults plus non-destructive schema migration.
- [ ] Remove dead Activity fields from active ORM/validation while leaving old physical DB columns untouched on upgraded installations.
- [ ] Implement normalization before validation: manual/scheduled-cost schedules set `cost` and `duration`; generated work keeps entered cost/duration.
- [ ] Run `pytest tests/test_activity_modes.py -v` and confirm pass.

### Task 2: Activity and project calculation semantics

**Files:**
- Modify: `q_flow/cashflow.py`
- Modify: `q_flow/models/cashflow.py`
- Test: `tests/test_activity_modes.py`
- Test: existing `tests/test_cashflow_model.py`, `tests/test_cashflow_calculation_hardening.py`, `tests/test_independent_inflow_selection.py`

**Interfaces:**
- `Activity_cf` consumes normalized Activity fields and always produces `marginal_work_as_json()` and `out_flow_as_json()`.
- `CashflowCalculator.work_cf` contains work activities only; `outflow_cf` contains all activities.

- [ ] Add failing tests proving manual work replaces only the generated curve and still uses existing subcontract/payment rules.
- [ ] Add failing tests proving scheduled cost has zero work, direct scheduled outflow, start offset, and does not extend work duration.
- [ ] Add failing mixed-scenario test proving activity-linked `value_factor = contract_value / work_activity_cost` and scheduled cost is excluded from billed work.
- [ ] Implement `distribution_type` selection in `Activity_cf`, including legacy linear inference.
- [ ] Implement scheduled-cost direct outflow path while preserving common `cash_flow_json` shape.
- [ ] Update `CashflowCalculator` so snapshot/outflow still works when there are scheduled-cost activities even if work arrays are empty, and so independent/activity-linked work duration uses only work activities.
- [ ] Update cashflow summary direct/subcontract/self-performed totals so scheduled costs count in direct project cost but are not falsely classified as subcontracted work unless explicitly intended by mode.
- [ ] Run the targeted backend calculation tests, then full `pytest`.

### Task 3: Portable JSON and template cleanup

**Files:**
- Modify: `q_flow/routes/cashflows.py`
- Modify: `q_flow/static/activity_types.json`
- Modify: `documentation/reference/cashflow_model.md`
- Modify: `documentation/reference/cashflow_json_format.md`
- Test: `tests/test_cashflow_import.py`

**Interfaces:**
- Version-1 portable JSON accepts/exports `activity_mode`, `distribution_type`, `cost_schedule_json`.
- Older JSON without these keys retains legacy behavior.

- [ ] Add failing import/export tests for manual work, scheduled cost, and an old version-1 activity with no new fields.
- [ ] Extend allowed activity import/export fields and apply the same normalization/validation used by activity routes.
- [ ] Remove dead legacy activity fields from portable source schema/docs/templates.
- [ ] Remove Linear as a semantic ActivityType calculation option; keep compatibility inference for stored/imported legacy `activity_type="linear"`.
- [ ] Run import/export tests and full backend suite.

### Task 4: Flutter Activity model and schedule parsing

**Files:**
- Modify: `cashflowpot/lib/src/models/activity.dart`
- Modify: `cashflowpot/lib/src/utils/cashflow_json.dart`
- Create/modify appropriate Flutter unit tests for Activity JSON and schedule parser.

**Interfaces:**
- Flutter fields: `activityMode`, `distributionType`, `List<double>? costSchedule`.
- UI text `1:500, 4:900` parses to dense local list `[500, 0, 0, 900]`; serialization sends the dense list.

- [ ] Add failing Dart tests for new field round-trip, legacy defaults/inference, and sparse-text-to-dense-list parsing including invalid input.
- [ ] Remove dead legacy Activity fields from Flutter serialization/model.
- [ ] Add reusable parser/formatter for comma-separated `period:value` input with 1-based user periods and dense 0-based list storage.
- [ ] Preserve `cashFlowJson` as calculated response data.
- [ ] User runs targeted Flutter tests after pull.

### Task 5: Flutter Activity form behavior

**Files:**
- Modify: the current activity create/edit form files under `cashflowpot/lib/src/pages/activity/` after reading the exact latest form structure.
- Update affected widget tests.

**Interfaces:**
- Mode choices: Work / Scheduled cost.
- Work distributions: S-curve / Linear / Manual.
- Manual and Scheduled cost expose the schedule text input; generated distributions expose existing duration/cost/skew controls as appropriate.

- [ ] Add/update widget tests for mode/distribution controls and required schedule behavior.
- [ ] Stop mutating `activity_type` when selecting Linear; persist `distribution_type` instead.
- [ ] For Manual Work, parse schedule text and show derived cost/duration read-only or informationally.
- [ ] For Scheduled Cost, hide irrelevant subcontract/payment/curve fields and show schedule-derived cost/duration.
- [ ] Keep activity template selection as creation-time defaults only.
- [ ] User runs full `flutter test`; resolve any regressions reported.

### Task 6: Final compatibility verification

**Files:**
- No new production files unless verification exposes a defect.

**Interfaces:**
- Existing scenarios calculate as before.
- New modes survive API create/update, portable JSON round-trip, and Flutter edit/save/reload.

- [ ] Run full backend `pytest` and record any failures by name.
- [ ] Verify a legacy linear Activity, normal S-curve Activity, manual-work Activity, scheduled-cost Activity, and mixed project snapshot.
- [ ] Compare `master..feature/activity-modes-scheduled-cost` for backend scope and `main..feature/activity-modes-scheduled-cost` for Flutter scope.
- [ ] Have the user run full Flutter tests and perform one visual create/edit check for Manual Work and Scheduled Cost before merge.
