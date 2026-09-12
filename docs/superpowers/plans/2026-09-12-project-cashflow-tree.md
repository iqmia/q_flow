# Project Units and Cashflow Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate QAuth Unit projects from multiple independent QFlow cashflow scenarios and present them as a project/cashflow tree in Flutter.

**Architecture:** QAuth supplies a generic app-token endpoint that creates a Unit for an existing AppUser. QFlow reuses its physical `project` table as Cashflow storage, adds `unit_id`, and provides explicit one-time migration plus Unit/cashflow APIs. Flutter renders QAuth Units as expandable parents and QFlow cashflows as selectable children.

**Tech Stack:** Flask, Flask-SQLAlchemy, SQLite, Click, pytest, QAuth HTTP API, Flutter/Dart, Material widgets

**Spec:** `docs/superpowers/specs/2026-09-12-project-cashflow-tree-design.md`

## Global Constraints

- Work on `feature/qauth-units-phase-1` in `iqmia/q_auth`, `iqmia/q_flow`, and `iqmia/cashflowpot`.
- QAuth behavior must remain generic; do not add QFlow or Cashflowpot concepts to QAuth.
- Projects are QAuth Units; cashflows and activities remain local to QFlow.
- Each cashflow owns all financial assumptions independently.
- Unit-level `view:cashflow` and `edit:cashflow` permissions govern every cashflow in the Unit.
- Migration is an explicit CLI operation and is never called during Flutter or API startup.
- Preserve existing local IDs and activity data.
- Do not change cashflow calculation formulas in this feature.
- Minimize Flutter tests and avoid unrelated UI or shared-style changes.

---

### Task 1: Complete QAuth app-token Unit creation

**Files:**
- Modify: `q_auth/routes/units.py`
- Modify: `q_auth/services/services_unit.py`
- Test: `tests/test_unit_routes.py`

**Interfaces:**
- Consumes: signed app token in `client-app-id`, `owner_user_id`, optional caller Unit `id`, identity fields, optional `roles_config`.
- Produces: `POST /unit/admin/new` returning `{data: {unit, already_exists}, message}` with status `201` for creation, `200` for a matching retry, and `409` for conflicts.

- [ ] **Step 1: Add failing app-service route tests**

Add focused tests that generate an app token and call the route without a user token:

```python
def test_admin_new_creates_unit_for_app_user(self):
    response = self.client.post(
        "/unit/admin/new",
        data={
            "owner_user_id": self.userTest.id,
            "id": "legacy-project-1",
            "name": "Legacy Tower",
            "description": "Imported by app",
            "color": "#123456",
        },
        headers={"client-app-id": generate_app_token(self.clientApp)},
    )
    self.assertEqual(response.status_code, 201)
    unit = response.json["data"]["unit"]
    self.assertEqual(unit["id"], "legacy-project-1")
    member = Member.query.filter_by(
        user_id=self.userTest.id,
        unit_id=unit["id"],
        client_app_id=self.clientApp.id,
    ).one()
    self.assertIn("creator", {role.name for role in member.roles})
```

Also cover missing owner, owner not registered with the calling app, roles file seeding, matching retry, different-owner retry, and existing ID linked to another app.

- [ ] **Step 2: Run the new QAuth tests and confirm the current route fails**

Run: `pytest -q tests/test_unit_routes.py -k admin_new`

Expected: failures because the route does not accept an owner or ID and calls `US.create_unit` without `user_id`.

- [ ] **Step 3: Make Unit creation reusable and idempotent**

Update the service boundary with an explicit lookup helper:

```python
@staticmethod
def get_creator_member(unit_id: str, client_app_id: str) -> Member | None:
    return (
        Member.query.join(Member.roles)
        .filter(
            Member.unit_id == unit_id,
            Member.client_app_id == client_app_id,
            Role.name == "creator",
        )
        .first()
    )
```

Update `new_unit_admin` to validate the resolved app, `User`, and `AppUser`, accept the complete generic payload and multipart files, seed supplied roles, and return a matching existing Unit without changing it. Conflict responses must use a stable code such as `unit_creation_conflict`.

- [ ] **Step 4: Run focused and complete QAuth tests**

Run:

```bash
pytest -q tests/test_unit_routes.py -k admin_new
pytest -q
```

Expected: new tests pass; complete suite has no new failures.

- [ ] **Step 5: Commit the QAuth capability**

```bash
git add q_auth/routes/units.py q_auth/services/services_unit.py tests/test_unit_routes.py
git commit -m "Add app-authorized Unit creation"
```

---

### Task 2: Introduce the local Cashflow model without copying legacy rows

**Files:**
- Create: `q_flow/models/cashflow.py`
- Modify: `q_flow/models/project.py`
- Modify: `q_flow/models/activity.py`
- Modify: `q_flow/cashflow.py`
- Test: `tests/test_cashflow_model.py`
- Modify: `tests/test_cashflow.py`
- Modify: `tests/test_activity_type.py`

**Interfaces:**
- Consumes: the existing physical `project` and `activity.project_id` schema.
- Produces: `Cashflow` mapped to table `project`, `Cashflow.unit_id`, `Activity.cashflow_id`, and calculation class `CashflowCalculator` accepting a Cashflow-like object.

- [ ] **Step 1: Write failing model compatibility tests**

```python
def test_cashflow_uses_legacy_table_and_activity_column(app):
    with app.app_context():
        cashflow = Cashflow(
            name="Tender",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=1_000_000,
        ).commit()
        activity = Activity(
            name="Concrete",
            cashflow_id=cashflow.id,
            created_by="user-1",
        ).commit()
        assert Cashflow.__tablename__ == "project"
        assert activity.cashflow_id == cashflow.id
        assert activity.as_dict()["cashflow_id"] == cashflow.id
        assert "project_id" not in activity.as_dict()
```

- [ ] **Step 2: Run the model test and verify it fails**

Run: `pytest -q tests/test_cashflow_model.py`

Expected: import/model failures because `Cashflow`, `unit_id`, and `cashflow_id` do not exist.

- [ ] **Step 3: Add the compatibility model layer**

Create `Cashflow` with `__tablename__ = "project"`, all existing financial columns, `unit_id = db.Column(db.String(64), index=True)`, and the activity relationship. Keep `q_flow/models/project.py` as a temporary import alias:

```python
from q_flow.models.cashflow import Cashflow

Project = Cashflow
```

Map the activity attribute to the existing column:

```python
cashflow_id = db.Column(
    "project_id",
    db.String(64),
    db.ForeignKey("project.id"),
    nullable=False,
)
```

Override activity serialization so clients receive `cashflow_id`. Rename `Project_cf` to `CashflowCalculator` while retaining `Project_cf = CashflowCalculator` as a compatibility alias for old imports and tests.

- [ ] **Step 4: Run model and calculation tests**

Run: `pytest -q tests/test_cashflow_model.py tests/test_cashflow.py tests/test_activity_type.py`

Expected: all pass with unchanged calculation outputs.

- [ ] **Step 5: Commit the model boundary**

```bash
git add q_flow/models q_flow/cashflow.py tests/test_cashflow_model.py tests/test_cashflow.py tests/test_activity_type.py
git commit -m "Separate local cashflows from project Units"
```

---

### Task 3: Add the one-time QFlow migration CLI

**Files:**
- Create: `q_flow/commands/__init__.py`
- Create: `q_flow/commands/migrate_project_cashflows.py`
- Modify: `q_flow/__init__.py`
- Modify: `q_flow/services/units.py`
- Modify: `q_flow/services/user_api.py`
- Remove route: `q_flow/routes/projects.py` (`/migrate_projects_to_units` only)
- Test: `tests/test_project_cashflow_migration.py`

**Interfaces:**
- Consumes: `User_API.post("unit/admin/new", ...)`, app-token authentication, legacy rows with missing `unit_id`, Cashflowpot roles JSON, SQLite storage path.
- Produces: Click command `migrate-projects-to-cashflows` with dry-run default and explicit `--execute` mutation.

- [ ] **Step 1: Add failing CLI tests**

```python
def test_migration_dry_run_does_not_change_data(app, runner, legacy_project):
    result = runner.invoke(args=["migrate-projects-to-cashflows"])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    with app.app_context():
        assert Cashflow.query.get(legacy_project.id).unit_id is None


def test_migration_creates_unit_and_converts_row(app, runner, legacy_project):
    with patch("q_flow.commands.migrate_project_cashflows.create_unit_for_owner") as create:
        create.return_value = ({"id": legacy_project.id}, False)
        result = runner.invoke(args=["migrate-projects-to-cashflows", "--execute"])
    assert result.exit_code == 0
    with app.app_context():
        cashflow = Cashflow.query.get(legacy_project.id)
        assert cashflow.unit_id == legacy_project.id
        assert cashflow.name == "Base Cashflow"
        assert cashflow.activities[0].name == "Concrete"
```

Also test an already migrated row, matching QAuth retry, soft-deleted Unit deactivation, one failed project while later projects continue, backup creation, and nonzero failure exit.

- [ ] **Step 2: Run CLI tests and verify failure**

Run: `pytest -q tests/test_project_cashflow_migration.py`

Expected: command and migration helpers are missing.

- [ ] **Step 3: Add the generic QAuth service call**

Add:

```python
def create_unit_for_owner(api, *, owner_user_id: str, unit_id: str,
                          name: str, description: str, color: str) -> tuple[dict, bool]:
    response = api.post(
        "unit/admin/new",
        data={
            "owner_user_id": owner_user_id,
            "id": unit_id,
            "name": name,
            "description": description,
            "color": color,
        },
        files={"roles_config": roles_config_file()},
    )
    if response.error:
        raise QAuthUnitError(response)
    payload = response_json(response).get("data") or {}
    return payload["unit"], bool(payload.get("already_exists"))
```

The User API already generates a fresh short-lived app token for each request; no user token is passed.

- [ ] **Step 4: Implement guarded schema/data migration**

The command must inspect `project` columns, add `unit_id VARCHAR(64)` only if missing, make a timestamped `q_flow.db.backup-YYYYMMDD-HHMMSS` before any executed change, and process rows one at a time. Capture old identity values before renaming the row. Flush/commit after each successful Unit and local conversion. Print deterministic counts and raise `click.ClickException` after processing when failures are nonzero.

- [ ] **Step 5: Remove request-time migration**

Delete `/migrate_projects_to_units` from project routes. Normal endpoints must not create missing Units from local rows.

- [ ] **Step 6: Run migration and regression tests**

Run:

```bash
pytest -q tests/test_project_cashflow_migration.py
pytest -q
```

Expected: CLI tests pass; complete suite has no new failures.

- [ ] **Step 7: Commit the migration command**

```bash
git add q_flow/commands q_flow/__init__.py q_flow/services q_flow/routes/projects.py tests/test_project_cashflow_migration.py
git commit -m "Add one-time project cashflow migration"
```

---

### Task 4: Refactor QFlow project and cashflow APIs

**Files:**
- Modify: `q_flow/routes/projects.py`
- Create: `q_flow/routes/cashflows.py`
- Modify: `q_flow/routes/activities.py`
- Modify: `q_flow/__init__.py`
- Modify: `tests/base.py`
- Modify: `tests/test_project_routes.py`
- Create: `tests/test_cashflow_routes.py`
- Modify: `tests/test_activity.py`
- Modify: `tests/test_qauth_phase1.py`

**Interfaces:**
- Consumes: QAuth Unit routes, `Cashflow.unit_id`, `view:cashflow`, `edit:cashflow`.
- Produces: Unit parents containing compact cashflow children; cashflow CRUD endpoints; activity endpoints keyed and serialized by cashflow.

- [ ] **Step 1: Add failing project tree and Cashflow CRUD tests**

```python
def test_projects_return_units_with_cashflow_children(app, unit_response):
    with app.app_context():
        Cashflow(id="cf-1", unit_id="unit-1", name="Tender", created_by="u1").commit()
    with patch("q_flow.routes.projects.u_api.get", return_value=unit_response):
        response = app.test_client().get(
            "/projects", headers={"Authorization": "Bearer user-token"})
    assert response.status_code == 200
    project = response.get_json()["data"][0]
    assert project["id"] == "unit-1"
    assert project["cashflows"] == [{
        "id": "cf-1", "unit_id": "unit-1", "name": "Tender", "description": ""
    }]
```

Add tests for new project plus Base Cashflow, new independent cashflow, retrieve/update/delete/restore/hard-delete cashflow, no cross-Unit access, Unit hard delete cascading local data, and activity permissions resolved through `cashflow.unit_id`.

- [ ] **Step 2: Run focused route tests and verify failures**

Run: `pytest -q tests/test_project_routes.py tests/test_cashflow_routes.py tests/test_activity.py tests/test_qauth_phase1.py`

Expected: failures showing the old one-Unit/one-local-row response and missing Cashflow endpoints.

- [ ] **Step 3: Restrict project routes to Unit responsibility**

Return QAuth Unit identity plus `Cashflow.compact_dict()` children. `new_project` creates the Unit first and then `Base Cashflow`. Unit update sends only identity fields to QAuth. Unit deactivate/activate retains local cashflows; hard delete removes related activities and cashflows only after QAuth succeeds.

- [ ] **Step 4: Implement Cashflow CRUD**

Provide these routes:

```text
POST   /project/<unit_id>/cashflows
GET    /cashflow/<cashflow_id>
PUT    /cashflow/<cashflow_id>
DELETE /cashflow/<cashflow_id>
PUT    /cashflow/<cashflow_id>/restore
DELETE /cashflow/<cashflow_id>/hard
```

Every route resolves the Cashflow's `unit_id` before calling `ensure_unit_permission`. Responses use the existing `{data, message}` convention.

- [ ] **Step 5: Re-key activity routes to cashflows**

Change creation and deleted-activity list routes to use `<cashflow_id>`. For existing route compatibility, aliases may remain temporarily, but all emitted activity JSON must use `cashflow_id`. Permission checks always use the parent cashflow's Unit ID.

- [ ] **Step 6: Run focused and complete QFlow tests**

Run:

```bash
pytest -q tests/test_project_routes.py tests/test_cashflow_routes.py tests/test_activity.py tests/test_qauth_phase1.py
pytest -q
python -m compileall -q q_flow tests
git diff --check
```

Expected: all tests and checks pass.

- [ ] **Step 7: Commit the API separation**

```bash
git add q_flow/routes q_flow/__init__.py tests
git commit -m "Add Unit cashflow hierarchy APIs"
```

---

### Task 5: Render the project/cashflow tree in Flutter

**Files:**
- Create: `lib/src/models/cashflow.dart`
- Modify: `lib/src/models/project.dart`
- Modify: `lib/src/models/activity.dart`
- Modify: `lib/src/pages/main_page.dart`
- Modify: `lib/src/pages/project/project_form.dart`
- Create: `lib/src/pages/cashflow/cashflow_form.dart`
- Modify: `lib/src/pages/activity/activities.dart`
- Modify: `lib/src/pages/activity/activity_form.dart`
- Modify: `lib/src/pages/activity/restore_deleted.dart`
- Modify: `lib/src/utils/cashflow.dart`
- Modify: `lib/src/utils/export_excel.dart`

**Interfaces:**
- Consumes: project objects with `cashflows`, Cashflow CRUD routes, activity JSON with `cashflow_id`.
- Produces: expandable Unit rows, selectable Cashflow children, split project and Cashflow forms, existing chart/activity view operating on a Cashflow.

- [ ] **Step 1: Add Dart models for the API hierarchy**

Define:

```dart
class Project {
  String id;
  String name;
  String description;
  String photo;
  String color;
  List<Cashflow> cashflows;
}

class Cashflow {
  String id;
  String unitId;
  String name;
  String description;
  List<Activity> activities;
  // existing financial and calculated fields
}
```

- [ ] **Step 2: Remove automatic migration and change selected state**

Delete `_projectMigrationAttempted` and the `migrate_projects_to_units` request. Replace `_currentProject` as the content selection with `_currentCashflow`, while retaining the owning Project for the app-bar context.

- [ ] **Step 3: Build the two-level drawer**

Use `ExpansionTile` for each Project. Render its Cashflows as indented `ListTile` children. Project actions edit/delete the Unit; child actions edit/delete the Cashflow. Add Cashflow is visible inside the expanded project to users whose returned permissions allow editing.

- [ ] **Step 4: Split project and Cashflow forms**

Project form sends only Unit identity fields. Cashflow form owns scenario name, description, contract value, advance, retention, retention release, DLP, payment duration, interest, and work-in-excess. New Unit creation receives the returned Base Cashflow. New Cashflow posts to `/project/<unit_id>/cashflows`.

- [ ] **Step 5: Rewire activity/chart/export views**

Change the existing activity list, form, deleted-item restoration, calculation utilities, and Excel export types from Project to Cashflow. Use `cashflow.id` in activity routes and preserve current chart/export behavior.

- [ ] **Step 6: Run available Flutter checks**

Run when Flutter is installed:

```bash
dart format lib
flutter analyze
flutter test
```

If Flutter is unavailable, run repository text checks for stale automatic migration calls and stale activity `project_id` serialization, and report that build verification remains outstanding.

- [ ] **Step 7: Commit the Flutter hierarchy**

```bash
git add lib/src
git commit -m "Show project cashflows as a navigation tree"
```

---

### Task 6: Cross-repository verification and publication

**Files:**
- Verify all changed files in all three repositories.

**Interfaces:**
- Consumes: completed QAuth, QFlow, and Flutter commits.
- Produces: three published `feature/qauth-units-phase-1` branches with documented verification evidence.

- [ ] **Step 1: Verify QAuth**

Run:

```bash
pytest -q
python -m compileall -q q_auth tests
git diff --check
```

- [ ] **Step 2: Verify QFlow**

Run:

```bash
pytest -q
python -m compileall -q q_flow tests
flask migrate-projects-to-cashflows
git diff --check
```

The migration command invocation must remain a dry run because `--execute` is absent.

- [ ] **Step 3: Verify Flutter as available**

Run `dart format --output=none --set-exit-if-changed lib`, `flutter analyze`, and `flutter test` when the SDK is available. Otherwise document the missing SDK and perform the stale-reference checks from Task 5.

- [ ] **Step 4: Review scope and secrets**

Confirm no environment files, database backups, tokens, app secrets, generated storage, or unrelated changes are tracked. Confirm formula outputs remain unchanged.

- [ ] **Step 5: Publish and compare branches**

Publish `feature/qauth-units-phase-1` in all three repositories. Compare each branch to its default branch and verify the received file list and commit count. Do not merge or open a pull request unless requested.
