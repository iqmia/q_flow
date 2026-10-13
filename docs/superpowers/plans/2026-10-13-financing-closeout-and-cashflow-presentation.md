# Financing Closeout and Cashflow Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the current activity/facility modeling chapter by making Scheduled Cost entry absolute-period based, defining scheduled/revolving facility behavior, exposing canonical decision KPIs, and reorganizing the cashflow screen into Project / Facilities / Overall Cash Position with compact high-value number formatting.

**Architecture:** Keep the existing Activity and financing schemas. The backend remains authoritative for facility flows and KPI metrics; Flutter only normalizes Scheduled Cost absolute periods into the existing `start + cost_schedule_json` representation and renders backend results. The cashflow grid gets one ordered row-description source so the fixed-label column and period-value column cannot drift out of alignment.

**Tech Stack:** Flask, SQLAlchemy, pytest, existing `q_flow.financing` engine; Flutter/Dart, Material widgets, flutter_test.

**Spec:** `docs/superpowers/specs/2026-10-13-financing-closeout-and-cashflow-presentation-design.md`

## Global Constraints

- Continue on `feature/activity-modes-scheduled-cost` in both `iqmia/q_flow` and `iqmia/cashflowpot`.
- Do not add a database migration for this closeout.
- Existing facility JSON remains valid.
- Scheduled facility draw schedules are requested financing inflows; only actual capacity-limited draws affect cash.
- Do not carry unavailable requested draw amounts into later periods.
- New principal from a scheduled draw is not eligible for `% PPC` or `cashflow_sweep` repayment until the following period.
- Explicit scheduled repayment and equal-installment timing remain user-controlled.
- Scheduled Cost absolute periods are a Flutter UX normalization onto existing backend `start + dense cost_schedule_json` fields.
- Excel numeric cells remain real numeric values; K/M formatting is Flutter presentation only.
- Preserve existing Work, Activity-linked/Independent inflow, PPC Discount, automatic-shortfall, and portable JSON behavior unless this spec explicitly changes it.

## Review Focus

1. **Scheduled draw plus old debt in the same period:** automatic repayment may repay opening principal but never the newly drawn amount; Task 1 pins this for `% PPC` and sweep.
2. **Unlimited scheduled/revolving facility (`limit = null`):** scheduled draws must remain uncapped and repayment timing must still obey the opening-principal rule; Task 1 adds this case.
3. **Scheduled Cost absolute schedule with leading project periods and gaps:** `4:25000, 7:75000` must round-trip as `start=3`, `[25000,0,0,75000]`, and back to the same absolute periods; Task 4 owns this test.
4. **No facilities / zero outstanding:** KPI summary and table must remain valid, with financing metrics zero and no empty Facilities block; Tasks 2, 6, and 7 cover this.
5. **Very large negative and positive currency values:** threshold scaling, sign, separators, two-decimal precision, and exact-value tooltip must remain correct around `999,999.99` and `999,999.99K`; Tasks 3, 6, and 7 cover this.

---

### Task 1: Scheduled and Revolving Facility Semantics

**Files:**
- Modify: `q_flow/financing.py`
- Modify: `tests/test_financing_engine.py`

**Interfaces:**
- Consumes: existing `calculate_financing(*, inflows, outflows, ppc_base, ppc_issued, facilities) -> dict`.
- Produces: facility rows containing `draw`, `repayment`, `interest`, `fees`, `outstanding`, `available_limit`; no user-facing `unfunded_draw` row data.
- Produces rule: for `draw_method == "scheduled"` and repayment method `percent_of_ppc` or `cashflow_sweep`, period repayment is capped by opening outstanding principal.

- [ ] **Step 1: Write failing financing-engine tests**

Add tests asserting:

```python
def test_scheduled_percent_ppc_repayment_uses_opening_outstanding_only():
    # P1 draw 500 with PPC due -> repayment 0.
    # P2 opening 500, new draw 300, PPC due 200 -> repayment 200, closing 600.
    ...

def test_scheduled_sweep_repayment_uses_opening_outstanding_only():
    # Positive cash in the draw period must not sweep the newly drawn principal.
    ...

def test_revolving_scheduled_draw_capacity_is_restored_by_repayment():
    # limit 1000; draw 800; repay 500; later requested 900 -> actual draw 700.
    ...

def test_non_revolving_repayment_does_not_restore_draw_capacity():
    # limit 1000; cumulative actual draws remain the capacity basis after repayment.
    ...

def test_unlimited_scheduled_facility_is_not_capacity_capped():
    ...

def test_explicit_scheduled_repayment_can_follow_user_schedule_unchanged():
    ...

def test_facility_rows_do_not_return_unfunded_draw():
    ...
```

- [ ] **Step 2: Run the targeted tests and confirm RED**

Run: `pytest tests/test_financing_engine.py -v`

Expected: new same-period repayment and payload-shape tests fail against current behavior.

- [ ] **Step 3: Implement opening-principal repayment eligibility in `q_flow/financing.py`**

Keep `opening_outstanding` captured before period draws. For automatic repayment methods on scheduled-draw facilities, cap principal repayment by both the calculated due/available cash and `opening_outstanding[index]`. Do not apply this cap to `scheduled` or `equal_installments` repayment methods.

Continue to calculate `actual draw = min(requested, available capacity)`. Remove `unfunded_draw` from each returned facility row and stop accumulating it as API-facing data; excess requested draw has no downstream effect.

- [ ] **Step 4: Run financing tests and existing financing regressions**

Run:

```bash
pytest tests/test_financing_engine.py -v
pytest tests/test_cashflow.py tests/test_cashflow_calculation_hardening.py -v
```

Expected: PASS, including existing PPC Discount and automatic-shortfall behavior.

- [ ] **Step 5: Commit**

```bash
git add q_flow/financing.py tests/test_financing_engine.py
git commit -m "feat: define scheduled facility repayment timing"
```

---

### Task 2: Canonical Backend Financing KPIs

**Files:**
- Modify: `q_flow/models/cashflow.py`
- Create: `tests/test_financing_summary.py`
- Modify: `documentation/reference/cashflow_model.md`

**Interfaces:**
- Consumes: snapshot keys `pre_financing_balance`, `facility_rows`, `facility_interest`, `facility_fees`, `outflow_with_interest`, and `duration`.
- Produces summary keys: `total_facility_interest`, `total_facility_fees`, `financing_cost`, `minimum_pre_financing_balance`, `minimum_pre_financing_period`, `peak_facility_outstanding`, `final_facility_outstanding`, `final_cash_balance`, `cash_after_debt_settlement`, plus existing cost/duration/horizon keys.
- Preserve `peak_pre_financing_need` / `peak_pre_financing_period` for compatibility if existing consumers/tests still use them; remove `unfunded_draw_total` because its source row no longer exists.

- [ ] **Step 1: Write failing summary tests**

Assert a scenario can return `minimum_pre_financing_balance == -250000.0`, a zero-based period index that Flutter will display as P21, peak/final combined outstanding principal, financing cost as interest + fees, and `cash_after_debt_settlement = final_cash_balance - final_facility_outstanding`. Add a no-facility case with zero financing metrics.

- [ ] **Step 2: Run the summary tests and confirm RED**

Run: `pytest tests/test_financing_summary.py -v`

- [ ] **Step 3: Implement canonical metrics in `Cashflow.as_dict_with_activities()`**

Compute combined outstanding per period by zipping all facility-row `outstanding` arrays with zero fill. Use the minimum of `pre_financing_balance` directly for the negative-balance KPI. `cash_after_debt_settlement` subtracts principal only and must not invent future interest.

- [ ] **Step 4: Update the calculation reference and run tests**

Run:

```bash
pytest tests/test_financing_summary.py tests/test_financing_engine.py tests/test_activity_modes.py -v
pytest
```

Expected: full backend suite PASS.

- [ ] **Step 5: Commit**

```bash
git add q_flow/models/cashflow.py tests/test_financing_summary.py documentation/reference/cashflow_model.md
git commit -m "feat: expose financing decision metrics"
```

---

### Task 3: Shared High-Value Amount Formatter and Flutter Summary Model

**Files:**
- Modify: `cashflowpot/lib/src/utils/form_values.dart`
- Modify: `cashflowpot/lib/src/models/project.dart`
- Create: `cashflowpot/test/amount_format_test.dart`
- Modify: `cashflowpot/test/project_summary_test.dart`
- Modify scenario-header tests that assert old `12.5M`-style values.

**Interfaces:**
- Produces `compactAmountText(double value) -> String` using the approved threshold rule.
- Produces `exactAmountText(double value) -> String` for tooltip/full-value presentation.
- `CashflowSummary` gains the backend KPI fields from Task 2.

- [ ] **Step 1: Write failing formatter threshold tests**

Pin:

```dart
expect(compactAmountText(250780.25), '250,780.25');
expect(compactAmountText(1750000), '1,750.00K');
expect(compactAmountText(250780250), '250,780.25K');
expect(compactAmountText(999999990), '999,999.99K');
expect(compactAmountText(1250500120), '1,250.50M');
expect(compactAmountText(-1750000), '-1,750.00K');
expect(exactAmountText(1250500120), '1,250,500,120.00');
```

Also pin values immediately below/above both scaling thresholds.

- [ ] **Step 2: Run formatter/model tests and confirm RED**

Run: `flutter test test/amount_format_test.dart test/project_summary_test.dart`

- [ ] **Step 3: Implement formatter and parse new summary fields**

Use base units while `abs(value) <= 999999.99`; otherwise K while `abs(value / 1000) <= 999999.99`; otherwise M. Money-style compact output keeps two decimals and separators. Non-finite values remain `—`.

- [ ] **Step 4: Update existing display-string tests and rerun**

Run:

```bash
flutter test test/amount_format_test.dart test/project_summary_test.dart test/scenario_header_responsive_test.dart test/scenario_header_mobile_layout_test.dart
```

- [ ] **Step 5: Commit**

```bash
git add lib/src/utils/form_values.dart lib/src/models/project.dart test/amount_format_test.dart test/project_summary_test.dart test/scenario_header_responsive_test.dart test/scenario_header_mobile_layout_test.dart
git commit -m "feat: add high-value cashflow formatting"
```

---

### Task 4: Scheduled Cost Absolute-Period UX

**Files:**
- Modify: `cashflowpot/lib/src/utils/activity_schedule.dart`
- Modify: `cashflowpot/lib/src/pages/activity/activity_form.dart`
- Modify: `cashflowpot/test/activity_schedule_test.dart`
- Modify: `cashflowpot/test/activity_form_modes_test.dart`

**Interfaces:**
- Keep relative `parseActivitySchedule` / `formatActivitySchedule` for Manual Work.
- Produce `parseAbsoluteActivitySchedule(String) -> ({int start, List<double> schedule})`.
- Produce `formatAbsoluteActivitySchedule(int start, List<double>? schedule) -> String`.

- [ ] **Step 1: Write failing schedule-normalization tests**

Pin `4: 25000, 7: 75000 -> start 3 + [25000, 0, 0, 75000]` and the exact reverse formatting. Also test unordered input, duplicate periods, gaps, trailing-zero duration marker, invalid and zero-total schedules.

- [ ] **Step 2: Add failing ActivityForm mode tests**

Assert Scheduled Cost hides Start and Work Distribution, uses absolute project-period schedule text, visibly marks cost/duration as calculated/read-only, normalizes start/schedule/cost/duration, and restores the exact previous Work distribution after Work -> Scheduled Cost -> Work. Manual Work must still show Start and relative schedule behavior.

- [ ] **Step 3: Run targeted tests and confirm RED**

Run: `flutter test test/activity_schedule_test.dart test/activity_form_modes_test.dart`

- [ ] **Step 4: Implement absolute Scheduled Cost normalization and distribution preservation**

Do not mutate `tempActivity.distributionType` when entering Scheduled Cost. Scheduled Cost uses the absolute helper and derives `tempActivity.start`; Manual Work keeps the relative helper and visible Start. Use a muted filled/calculated treatment for derived cost/duration fields.

- [ ] **Step 5: Run activity tests**

Run:

```bash
flutter test test/activity_schedule_test.dart test/activity_form_modes_test.dart test/activity_model_test.dart test/cashflow_json_test.dart
```

- [ ] **Step 6: Commit**

```bash
git add lib/src/utils/activity_schedule.dart lib/src/pages/activity/activity_form.dart test/activity_schedule_test.dart test/activity_form_modes_test.dart
git commit -m "feat: simplify scheduled cost entry"
```

---

### Task 5: Scheduled Facility Editor Limit and Draw Total

**Files:**
- Modify: `cashflowpot/lib/src/widgets/financing_facility_editor.dart`
- Create: `cashflowpot/test/financing_facility_editor_test.dart`

**Interfaces:**
- Scheduled `drawSchedule` remains a user-entered sparse period map.
- `limit` remains independently user-entered and nullable.
- Scheduled-draw total is calculated display-only and never overwrites `limit`.

- [ ] **Step 1: Write failing editor tests**

Cover a schedule totaling 2,400 with limit 1,000; changing the schedule changes only the calculated total; blank limit saves as `null`; revolving persists; switching draw method does not silently replace a previously entered limit.

- [ ] **Step 2: Run the editor test and confirm RED**

Run: `flutter test test/financing_facility_editor_test.dart`

- [ ] **Step 3: Implement the editor behavior**

Initialize limit from `widget.value.limit`, add a calculated `Scheduled draws total`, keep schedule/start/end controls, and save the independently entered nullable limit.

- [ ] **Step 4: Run editor + JSON tests**

Run: `flutter test test/financing_facility_editor_test.dart test/cashflow_json_test.dart test/project_form_test.dart`

- [ ] **Step 5: Commit**

```bash
git add lib/src/widgets/financing_facility_editor.dart test/financing_facility_editor_test.dart
git commit -m "feat: separate scheduled draws from facility limit"
```

---

### Task 6: Compact KPI Grid Below the Scenario Header

**Files:**
- Modify: `cashflowpot/lib/src/widgets/scenario_summary_cards.dart`
- Modify: `cashflowpot/lib/src/pages/activity/activities.dart`
- Create or modify: `cashflowpot/test/scenario_summary_cards_test.dart`
- Modify: `cashflowpot/test/project_summary_test.dart`

**Interfaces:**
- Consumes Task 3 summary fields and amount formatters.
- Produces eight compact cards: Project cost, Financing cost, Total cost, Peak funding requirement, Peak facility usage, Outstanding facilities, Closing cash balance, Cash after debt settlement.
- Peak funding displays `P(minimumPreFinancingPeriod + 1)`.

- [ ] **Step 1: Write failing KPI rendering/responsiveness tests**

Assert titles, compact values, financing Interest/Fees subtitle, peak funding amount + P21, exact-value tooltip, and 4/3/2 column behavior for desktop/tablet/narrow screens.

- [ ] **Step 2: Run KPI tests and confirm RED**

Run: `flutter test test/scenario_summary_cards_test.dart test/project_summary_test.dart`

- [ ] **Step 3: Redesign `ScenarioSummaryCards`**

Use compact card height/typography and restrained Material icons. Add Work duration / Financial horizon as compact metadata below the grid.

- [ ] **Step 4: Move KPI grid below the pinned scenario header**

Remove summary cards from `_insightsContent()` and place them before the detailed activity/cashflow workspace. Forecast Insights becomes charts-only.

- [ ] **Step 5: Run layout regressions**

Run: `flutter test test/scenario_summary_cards_test.dart test/scenario_header_responsive_test.dart test/scenario_header_mobile_layout_test.dart test/chart_card_layout_test.dart`

- [ ] **Step 6: Commit**

```bash
git add lib/src/widgets/scenario_summary_cards.dart lib/src/pages/activity/activities.dart test/scenario_summary_cards_test.dart test/project_summary_test.dart
git commit -m "feat: add compact financing KPI grid"
```

---

### Task 7: Project / Facilities / Overall Cashflow Table

**Files:**
- Create: `cashflowpot/lib/src/utils/cashflow_table_rows.dart`
- Modify: `cashflowpot/lib/src/pages/activity/activities.dart`
- Create: `cashflowpot/test/cashflow_table_rows_test.dart`
- Create or modify: `cashflowpot/test/cashflow_table_layout_test.dart`

**Interfaces:**
- Produce one ordered row model consumed by both fixed labels and numeric period cells.
- Sections in order: `PROJECT CASHFLOW`, optional `FACILITIES`, `OVERALL CASH POSITION`.

- [ ] **Step 1: Write failing row-composition tests**

Assert exact row order. Verify total inflow = project inflow + actual facility draws; total outflow = project cost + repayment + interest + fees; net equals backend `funded_netflow`; closing equals funded balance; outstanding summary cell is final outstanding rather than sum; no Facilities section when absent; no `unfunded_draw` row.

- [ ] **Step 2: Run row tests and confirm RED**

Run: `flutter test test/cashflow_table_rows_test.dart`

- [ ] **Step 3: Implement `cashflow_table_rows.dart`**

Build descriptors from project inflow/outflow, facility rows, funded netflow and closing balance. Combine facility interest + fees into one row and zero-fill unequal horizons.

- [ ] **Step 4: Refactor `ListActivities` to render both table halves from the same descriptors**

Replace separate Inflows / Outflows / Balance loops. Keep compact two-line facility labels. Every compact monetary cell gets an exact-value Tooltip. Keep horizontal scrolling and do not add icons to grid rows.

- [ ] **Step 5: Run table/layout tests**

Run: `flutter test test/cashflow_table_rows_test.dart test/cashflow_table_layout_test.dart test/activity_lane_geometry_test.dart test/scenario_header_responsive_test.dart`

- [ ] **Step 6: Commit**

```bash
git add lib/src/utils/cashflow_table_rows.dart lib/src/pages/activity/activities.dart test/cashflow_table_rows_test.dart test/cashflow_table_layout_test.dart
git commit -m "feat: reorganize cashflow table by financial layer"
```

---

### Task 8: Export and Whole-Branch Regression Verification

**Files:**
- Modify only if a regression is found: existing Excel tests/export files.
- Modify `documentation/reference/cashflow_model.md` only if final implementation naming differs from the planned names.

**Interfaces:**
- Confirms Flutter formatting never mutates stored/exported numeric values.
- Confirms Activity/facility JSON compatibility and existing scenario behavior.

- [ ] **Step 1: Run Excel numeric-value regressions**

Run: `flutter test test/excel_export_v2_test.dart test/excel_export_v2_final_polish_test.dart`

- [ ] **Step 2: Run focused Flutter feature suite**

Run:

```bash
flutter test \
  test/amount_format_test.dart \
  test/activity_schedule_test.dart \
  test/activity_form_modes_test.dart \
  test/financing_facility_editor_test.dart \
  test/project_summary_test.dart \
  test/scenario_summary_cards_test.dart \
  test/cashflow_table_rows_test.dart \
  test/cashflow_table_layout_test.dart \
  test/cashflow_json_test.dart
```

- [ ] **Step 3: Run full Flutter suite**

Run: `flutter test`

Expected: PASS. The user may run this locally if the execution environment has no Flutter SDK.

- [ ] **Step 4: Run full backend suite again**

Run: `pytest`

Expected: PASS.

- [ ] **Step 5: Final scope review**

Compare both feature branches to their bases and confirm there is no LC-to-Activity linking, no maturity engine, no carry-forward of unavailable draws, no new database migration, and no textual K/M conversion in Excel cells.

- [ ] **Step 6: Commit final documentation-only corrections only if needed**

```bash
git add documentation/reference/cashflow_model.md
git commit -m "docs: finalize financing closeout reference"
```
