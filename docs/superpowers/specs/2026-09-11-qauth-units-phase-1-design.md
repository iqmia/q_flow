# QAuth Units Phase 1 Design

## Scope

Phase 1 modernizes Cashflowpot authentication and makes QAuth Units the identity and authorization boundary for projects. It changes only `q_flow` and `cashflowpot`; `q_auth` is an inspected dependency and must remain unchanged.

Cashflow calculation changes, multiple forecasts, cross-application consumption, and AI activity generation are explicitly deferred.

## Authentication

Cashflowpot retains its embedded `flutter_login` experience for email login, registration, verification, recovery, and password reset. Google sign-in remains native in Flutter. The client sends credentials or the Google ID/access token to QFlow. QFlow signs a short-lived application token with its QAuth application secret and proxies the request to the current QAuth API.

QFlow verifies QAuth JWTs locally. An expired access token is refreshed through `POST /user/get_fresh_token`, which preserves user- or unit-scoped context. QFlow returns a replacement token in `Authorization: Bearer <token>` on any response. When a token cannot be refreshed, QFlow returns HTTP 401 with `code: reauth_required`.

Cashflowpot adopts replacement tokens from the response header (and accepts a response-body token for compatibility). It logs out only for the structured `reauth_required` code, never because an error message happens to contain the word “token”.

## Project and Unit Ownership

A QAuth Unit is the canonical project identity and membership record. For new projects, QFlow generates one UUID and supplies it to QAuth as the Unit ID; the local Project financial profile uses the same ID.

QAuth owns:

- name, description, image, and color;
- active/deleted state;
- members, roles, and permissions.

QFlow owns:

- contract and cashflow assumptions;
- activities and generated cashflow arrays;
- a compatibility mirror of identity fields in the existing Project table, which is not authoritative.

Project responses merge QAuth Unit identity into the local financial profile so the existing Flutter project model remains compatible.

## Roles and Permissions

Every new project sends a versioned `roles_config` JSON file to QAuth. QAuth's common roles and permissions remain available. Cashflowpot adds:

- `view:cashflow`
- `edit:cashflow`

The seeded roles are:

- `creator`: all unit and cashflow permissions;
- `admin`: all unit and cashflow permissions except `change:creator`;
- `editor`: `view:unit`, `edit:unit`, `leave:unit`, `view:cashflow`, and `edit:cashflow`;
- `viewer`: `view:unit`, `leave:unit`, and `view:cashflow`.

QFlow first accepts a valid app-scoped user token. When a project operation needs unit authorization, it loads that Unit through QAuth using the user identity, receives a unit-scoped token, verifies its `unit_id` and `unit_permissions`, and propagates the token to Cashflowpot. A token already scoped to the requested Unit avoids the extra QAuth load.

Reads require `view:cashflow`; project/activity mutations require `edit:cashflow`. Unit edit, deactivate, activate, and delete operations are also performed by QAuth, whose own unit permission decorators remain authoritative.

## Existing Projects

QFlow exposes an idempotent authenticated `POST /migrate_projects_to_units`. It creates a QAuth Unit with the same ID for each legacy project owned by the current user that is not already linked to the Cashflowpot QAuth application. Partial failures are reported per project and successful migrations are not repeated. Cashflowpot calls this once before its first project-page load.

QAuth currently enforces globally unique Unit names. A legacy project whose name conflicts with any QAuth Unit cannot be silently renamed; its migration is reported as failed for the user/operator to resolve.

## Failure and Consistency Rules

- QAuth errors retain their status and safe message through QFlow.
- If QAuth Unit creation succeeds but the local profile cannot be saved, QFlow attempts to delete the newly created Unit and reports failure.
- Soft delete/deactivate and restore/activate update QAuth first and then the local compatibility state.
- Hard delete removes the QAuth Unit before the local profile.
- No QAuth application secret or Google server secret is shipped in Flutter.

## Verification

Backend tests cover the QAuth request contract, fresh-token behavior, structured reauthentication, roles payload, project/Unit creation and migration, merged responses, and unit permissions. Frontend testing is intentionally narrow: token extraction and structured reauthentication behavior are the only new test targets where the available Flutter toolchain permits it.
