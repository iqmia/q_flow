# QAuth Units Phase 1 Implementation Plan

> **Spec:** [../specs/2026-09-11-qauth-units-phase-1-design.md](../specs/2026-09-11-qauth-units-phase-1-design.md)

## Goal

Keep Cashflowpot's embedded Flutter authentication UX while using the current QAuth token APIs, and replace local project ownership with QAuth Unit membership, roles, and permissions.

## Tasks

- [x] Make backend tests portable and repair only stale route/setup assumptions needed for a trustworthy baseline.
- [x] Add focused failing tests for `User_API` URL construction, signed app headers, `get_fresh_token` refresh, response token propagation, and structured `reauth_required` failures.
- [x] Update `q_flow/config.py`, `q_flow/services/user_api.py`, `q_flow/services/decorators.py`, and `q_flow/routes/users.py` to proxy the current QAuth authentication endpoints and Google token login.
- [x] Add a versioned Cashflowpot roles/permissions JSON file and tests proving it is sent as `roles_config` for Unit creation.
- [x] Add unit-loading and permission helpers that verify `unit_id` plus `unit_permissions`, with failing tests for wrong Unit and missing permissions.
- [x] Refactor project routes so QAuth owns project identity/lifecycle and QFlow merges Unit identity with its local financial profile.
- [x] Add and test the idempotent legacy-project migration endpoint.
- [x] Refactor activity routes to require Unit-scoped cashflow permissions rather than `created_by` ownership.
- [x] Update the minimum Cashflowpot files: adopt `Authorization` response tokens, handle only `reauth_required`, proxy Google with the current field names, and call project migration before the first list request.
- [x] Run focused tests after every red/green cycle, then the complete backend suite and available static checks.
- [x] Review both diffs for secrets and scope, confirm `q_auth` is unchanged, commit, and publish `feature/qauth-units-phase-1` in both repositories.
