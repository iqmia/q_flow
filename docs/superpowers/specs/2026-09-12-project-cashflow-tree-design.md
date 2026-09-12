# Project Units and Cashflow Scenarios

## Scope

This change separates a construction project from its cashflow scenarios across QAuth, QFlow, and the Cashflowpot Flutter application.

- A project is a QAuth Unit. QAuth owns its identity, lifecycle, membership, roles, and permissions.
- A cashflow is a QFlow financial scenario belonging to one Unit.
- Activities belong to a cashflow.
- One Unit may contain any number of cashflows.
- Unit permissions continue to govern all cashflows in that Unit. Per-cashflow permissions are outside this scope.

The work continues on `feature/qauth-units-phase-1` in all three repositories.

## Alternatives Considered

### Recommended: reuse the existing local table as Cashflow storage

Keep the existing `project` database table and its rows, but represent it in Python as `Cashflow`. Add `unit_id` and reinterpret the existing financial fields as cashflow-level fields. Keep the existing activity foreign-key column physically intact while exposing it as `cashflow_id` in code and API responses.

This minimizes production schema changes, preserves row and activity IDs, and makes rollback practical.

### Copy legacy rows into a new Cashflow table

This produces cleaner physical table names but requires copying every financial row, changing every activity foreign key, validating referential integrity, and deciding when to remove the legacy tables. It adds risk without changing application behavior.

### Keep the current model and add a display-only tree

This avoids migration but leaves one record serving as both Unit and cashflow. Multiple independent scenarios would remain impossible, so this does not meet the requirement.

## QAuth: Generic Service Unit Creation

QAuth's existing `POST /unit/admin/new` route will become a supported service-to-service endpoint. It remains generic and contains no Cashflowpot-specific behavior.

Authentication:

- `active_client_app_required` validates the signed app token supplied through `client-app-id` or `client_app_id`.
- The resolved active application is the complete authority boundary for the request.
- No user token is accepted or required.

Input:

- `owner_user_id` (required)
- `id` (optional caller-supplied Unit ID)
- `name` (required)
- `description` (optional)
- `color` (optional)
- optional multipart `image`
- optional multipart `roles_config`

Validation and isolation:

- The owner must exist and have an AppUser relationship with the calling application. The AppUser may be inactive so dormant legacy users' data is preserved; normal login and access rules still prevent inactive users from using the app.
- The Unit is linked only to the calling application.
- The owner receives the initial creator membership for that application and Unit.
- App-specific roles and permissions may be seeded from `roles_config`.
- The route cannot change the creator of an existing Unit.
- An existing Unit ID is returned as already created only when it is linked to the same application and has the same creator. Any mismatch returns `409`.
- Existing global Unit-name uniqueness remains enforced. Name conflicts return `409` and are never silently renamed.

The route creates one Unit per request. QFlow performs the small batch by making one request per legacy project, giving each project an independent result and retry boundary.

## QFlow Data Model

### Unit/Project

No separate mutable local Project identity is introduced. Project name, description, image, color, lifecycle, membership, roles, and permissions come from QAuth.

### Cashflow

The Python `Cashflow` model maps to the existing physical `project` table for migration safety. It contains:

- its own ID;
- `unit_id`, referencing the QAuth Unit logically;
- scenario name and description;
- show/deleted state;
- advance, retention, end-of-project retention release, DLP, payment duration, interest rate, contract value, and work-in-excess-of-billing;
- related activities and calculated inflow/outflow results.

Each cashflow owns a complete independent set of financial assumptions. Values are not inherited dynamically from the Unit or another cashflow.

### Activity

Activities belong to one cashflow. The existing database column `activity.project_id` remains physically unchanged for migration safety, but the model and external API expose it as `cashflow_id`. Permission checks resolve the activity's cashflow, then check the cashflow's `unit_id` in QAuth.

## API Behavior

`GET /projects` returns the user's QAuth Units, each merged with a compact `cashflows` list from QFlow. Unit identity is canonical.

Project routes continue to manage the QAuth Unit:

- create project;
- update Unit identity;
- deactivate, activate, and delete Unit.

Creating a new project also creates one local cashflow named `Base Cashflow` with default financial assumptions. If local creation fails after QAuth creation, QFlow attempts to remove the newly created Unit and reports the failure.

Cashflow routes provide:

- create under a Unit;
- retrieve with activities and calculations;
- update its name, description, and assumptions;
- soft delete, restore, and hard delete.

Activity routes use cashflow IDs and verify `view:cashflow` or `edit:cashflow` against the parent Unit.

Project deletion affects the Unit lifecycle and does not independently rewrite cashflow data. Unit hard deletion removes all local cashflows and their activities for that Unit after QAuth confirms deletion.

## Flutter Navigation and Forms

The drawer becomes a two-level tree:

- Project/Unit as an expandable parent row;
- cashflows as indented child rows;
- selecting a cashflow opens the existing activity/chart view;
- project actions remain on the parent row;
- cashflow create, edit, and delete actions belong to child rows or the expanded project section.

The current combined form is split by responsibility:

- Project form: Unit name, description, image, and color.
- Cashflow form: scenario name, description, contract value, and all financial assumptions.

The Flutter startup call to `migrate_projects_to_units` is removed. Normal startup only loads projects and cashflows.

## One-Time Production Migration

QFlow registers a CLI command:

```bash
flask migrate-projects-to-cashflows --execute
```

Without `--execute`, the command performs a dry run and reports intended work.

Execution sequence:

1. Verify the QAuth app-token configuration before changing local data.
2. Create a timestamped copy of the SQLite database in the configured storage directory.
3. Add nullable `unit_id` to the existing `project` table when absent.
4. Select legacy rows where `unit_id` is null.
5. For each row, call QAuth `POST /unit/admin/new` using its current ID, identity fields, `created_by` owner, and Cashflowpot roles configuration.
6. After QAuth confirms the Unit, set the local row's `unit_id` to its existing ID, rename the scenario to `Base Cashflow`, and retain all financial fields and attached activities.
7. Preserve soft-deleted state by deactivating the newly created Unit through the app-token admin endpoint.
8. Commit each successful local row independently and continue after individual failures.
9. Print created, already-migrated, failed, and skipped counts; exit nonzero when failures exist.

The command is idempotent. Rows with `unit_id` are skipped. If QAuth creation succeeded but the local update did not, rerunning uses QAuth's matching-ID response and completes the local step.

There is no automatic migration during application startup or user requests.

## Error Handling

- QAuth validation errors are returned without exposing app secrets or signed app tokens.
- Cross-application owner or Unit conflicts return `409`.
- Unit-name collisions are reported for manual resolution.
- Cashflow requests for missing or deleted records return the existing not-found semantics.
- A request with valid Unit access but without the required cashflow permission returns structured `unit_access_denied` with `403`.
- Migration failures do not roll back previously completed projects; the backup and idempotent command provide recovery.

## Testing

QAuth tests cover app-token validation, owner/AppUser validation, creator membership, role seeding, caller-supplied IDs, idempotent retries, and cross-app/conflicting retries.

QFlow tests cover the Cashflow model, Unit/cashflow response shape, cashflow CRUD, Unit-derived permission checks, activity ownership, project creation with a Base Cashflow, and dry-run/executed/idempotent/partial-failure migration behavior.

Flutter changes remain deliberately small. Existing widget flows will be adjusted for the tree and split forms; no broad frontend test suite will be introduced. Available static analysis and build checks will be run.

## Out of Scope

- Cashflow calculation formula changes;
- AI activity generation;
- per-cashflow roles or permissions;
- scenario comparison or approval workflows;
- synchronization with Valrig or other applications;
- changing QAuth's global Unit-name uniqueness rule.
