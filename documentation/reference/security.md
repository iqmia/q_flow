# CashflowPot security and QAuth integration

This document describes the current authentication and project-authorization behavior implemented by `q_flow`.

It is a technical reference, not a claim that the application is immune to every security failure. Security-sensitive changes should be verified against the current QAuth implementation and tests.

## 1. Trust boundaries

CashflowPot separates responsibilities between:

- the Flutter client;
- the `q_flow` Flask backend;
- QAuth; and
- QAuth Units used as CashflowPot Projects.

QAuth is authoritative for user identity, application-bound user tokens, Unit identity, Unit roles, and Unit permissions.

`q_flow` is authoritative for local Cashflow scenarios/Activities and enforces QAuth-backed project permissions before protected project/scenario operations.

## 2. Protected API requests

Protected `q_flow` routes use the `auth_required` decorator.

The request must provide a bearer token:

```http
Authorization: Bearer <QAuth user token>
```

If the Authorization header is absent or is not a Bearer token, the request is rejected.

The backend then verifies the token and requires the decoded user to be active. It currently checks:

```text
is_active
app_user_active
```

`app_user_active` defaults to `true` when that claim is absent for compatibility.

## 3. User-token verification

`q_flow.services.user_api.User_API.verify_token()` verifies QAuth user JWTs locally.

Current verification uses the configured values:

```text
APP_ID
PUBLIC_KEY
ALGO
```

The JWT decode includes the application audience:

```text
audience = APP_ID
```

After decode, q_flow also verifies that:

```text
decoded client_app_id == APP_ID
```

This binds the accepted user token to the CashflowPot application rather than accepting a valid QAuth token intended for another application.

Invalid signatures, invalid audience, malformed/invalid tokens, and key/decode failures result in re-authentication style errors rather than granting access.

## 4. Expired user tokens and refresh

When a user token is expired, q_flow currently attempts to obtain a fresh token from QAuth using:

```text
user/get_fresh_token
```

The expired user token is forwarded to QAuth as an Authorization Bearer token.

If QAuth returns a new token, q_flow:

1. stores it for the current request in `g.new_token`;
2. verifies the new token again through the normal `verify_token()` path; and
3. exposes the refreshed token back to the client after the request.

The `User_API` `after_request` hook currently propagates the refreshed token in:

```http
Authorization: Bearer <new-token>
```

and, when the response body is a JSON object, also adds:

```json
{
  "token": "<new-token>"
}
```

If refresh fails or no replacement token is returned, the request requires re-authentication.

## 5. q_flow application identity when calling QAuth

Calls from q_flow to QAuth use an application identity in addition to any user token.

The backend builds a short-lived JWT and sends it in the QAuth request header:

```http
client-app-id: <application JWT>
```

The application JWT is signed with:

```text
APP_SECRET
APP_ALGO
```

Its current payload includes:

```text
client_app_id = APP_ID
iat
exp
```

The token lifetime is currently nine minutes and q_flow caches it until shortly before expiry to avoid unnecessary signing work.

`APP_SECRET` is server-side secret material and must not be exposed to the browser or committed to Git.

## 6. QAuth request headers

For calls from q_flow to QAuth, the current adapter can send:

```http
client-app-id: <short-lived app JWT>
Authorization: Bearer <user token>
unit-id: <QAuth Unit id>
```

The Authorization and Unit headers are included when the operation requires them.

This separates:

- **application identity** — `client-app-id`;
- **user identity** — Authorization Bearer token; and
- **project context** — `unit-id`.

## 7. Project authorization through QAuth Units

A CashflowPot Project is a QAuth Unit.

Protected project/scenario operations use Unit permissions rather than trusting a local project-owner flag.

Current permissions used by q_flow are:

```text
view:cashflow
edit:cashflow
```

The verified/scoped user data contains a `unit_id` and `unit_permissions` list when scoped to a Unit.

If the current user token is not already scoped to the requested Unit, q_flow calls QAuth to load the Unit and obtains a Unit-scoped token. The returned token is verified again before use.

Authorization succeeds only when the scoped user has the requested Unit id and required permission in `unit_permissions`.

A missing permission returns an access-denied response; it does not fall back to local database ownership.

## 8. Project creation and Unit role configuration

Creating a CashflowPot Project creates a QAuth Unit.

q_flow sends CashflowPot's roles configuration file to QAuth when creating the Unit so the Unit can use the application's project permissions.

The local Cashflow scenario stores the Unit id (`unit_id`) and uses that id to authorize later scenario/Activity operations.

## 9. Backend configuration keys

The current QAuth adapter requires these backend configuration values:

```text
USER_API_URL or QAUTH_URL
APP_ID
PUBLIC_KEY
ALGO
APP_SECRET
APP_ALGO
```

`APP_NAME` is also configured for application identity/compatibility but the current required-key check is based on the values above.

Production configuration currently loads values through `Config`, including secret values from `env.json`.

The repository must contain configuration key names only, not production secrets.

### Meaning

- `APP_ID` — CashflowPot/QAuth application identifier and expected JWT audience.
- `PUBLIC_KEY` — QAuth public key used by q_flow to verify user JWTs.
- `ALGO` — algorithm accepted when verifying QAuth user JWTs.
- `APP_SECRET` — server-side secret used to sign q_flow's short-lived application JWT sent to QAuth.
- `APP_ALGO` — algorithm used to sign the application JWT.
- `USER_API_URL` / `QAUTH_URL` — QAuth base URL.

The adapter currently normalizes a legacy QAuth base URL ending in `/user` so old configuration can still point at the QAuth service without duplicating `/user` in new route paths.

## 10. Testing behavior

When Flask `TESTING` is enabled, the QAuth adapter returns a deterministic test user instead of requiring a live QAuth service.

Test configuration uses non-production placeholder values for QAuth keys so tests do not depend on a local secret file or external authentication service.

Tests should mock QAuth at the application boundary when validating QAuth behavior, Unit access, refresh, and error handling.

## 11. Security rules for future changes

1. Protected backend routes must continue to require verified user identity unless explicitly designed as public routes.
2. User JWT verification must remain bound to the CashflowPot `APP_ID` audience/application.
3. `APP_SECRET` and other credentials stay server-side and out of Git/client bundles.
4. Local knowledge of a scenario id is not authorization; project access comes from QAuth Unit permissions.
5. Unit-scoped tokens returned by QAuth must be verified before their permissions are trusted.
6. `view:cashflow` and `edit:cashflow` should remain explicit permission checks rather than broad role-name guesses.
7. Token refresh must not cause an expired/invalid token to be accepted without successful QAuth refresh and re-verification.
8. QAuth network/error responses should fail closed for protected operations.
9. Documentation must not instruct the frontend to store backend signing secrets or the backend `APP_SECRET`.
10. Changes to QAuth token claims, application identity, or Unit permission semantics must update this reference and the corresponding tests together.

## 12. Historical note

An older security document described an `app_key` shared with the frontend and a simpler token flow. That is not the current q_flow implementation.

The current backend uses an application JWT in `client-app-id`, signed server-side with `APP_SECRET`, verifies QAuth user tokens with `PUBLIC_KEY`, binds them to the `APP_ID` audience/application, and authorizes project access through QAuth Unit permissions.

Last reviewed against current `q_flow/services/user_api.py`, `decorators.py`, and `services/units.py`: 7 October 2026.
