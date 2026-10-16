"""Short-lived signed tokens for stateless CashflowPot Excel downloads."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError


ISSUER = "cashflowpot"
AUDIENCE = "cashflowpot-excel-export"
PURPOSE = "cashflow_excel"
ALGORITHM = "HS256"


class ExcelExportTokenError(ValueError):
    """Raised when an Excel export link token is invalid or expired."""


@dataclass(frozen=True)
class ExcelExportClaims:
    cashflow_id: str
    unit_id: str
    project_name: str
    expires_at: datetime


def _utc(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def create_excel_export_token(
    *,
    secret: str,
    cashflow_id: str,
    unit_id: str,
    project_name: str,
    ttl_seconds: int,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    """Create a possession-based token for one Cashflow Excel export."""
    if not secret:
        raise ExcelExportTokenError("Excel export signing key is not configured")
    if not cashflow_id or not unit_id:
        raise ExcelExportTokenError("Excel export target is incomplete")
    if ttl_seconds <= 0:
        raise ExcelExportTokenError("Excel export token lifetime must be positive")

    issued_at = _utc(now)
    expires_at = issued_at + timedelta(seconds=int(ttl_seconds))
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "purpose": PURPOSE,
        "cashflow_id": str(cashflow_id),
        "unit_id": str(unit_id),
        "project_name": str(project_name or "CashflowPot Project"),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM), expires_at


def decode_excel_export_token(
    *,
    secret: str,
    token: str,
    now: datetime | None = None,
) -> ExcelExportClaims:
    """Verify a signed Excel link and return its strongly scoped claims."""
    if not secret or not token:
        raise ExcelExportTokenError("Invalid Excel export token")
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": [
                    "iss",
                    "aud",
                    "purpose",
                    "cashflow_id",
                    "unit_id",
                    "project_name",
                    "iat",
                    "exp",
                ],
                # Validate expiry against the injectable clock below so tests
                # and callers use one deterministic definition of "now".
                "verify_exp": False,
            },
        )
    except (InvalidTokenError, TypeError, ValueError) as error:
        raise ExcelExportTokenError("Invalid Excel export token") from error

    if claims.get("purpose") != PURPOSE:
        raise ExcelExportTokenError("Invalid Excel export token purpose")

    cashflow_id = claims.get("cashflow_id")
    unit_id = claims.get("unit_id")
    project_name = claims.get("project_name")
    exp = claims.get("exp")
    if (
        not isinstance(cashflow_id, str)
        or not cashflow_id
        or not isinstance(unit_id, str)
        or not unit_id
        or not isinstance(project_name, str)
        or not project_name
        or not isinstance(exp, (int, float))
    ):
        raise ExcelExportTokenError("Invalid Excel export token claims")

    expires_at = datetime.fromtimestamp(float(exp), tz=timezone.utc)
    if _utc(now) >= expires_at:
        raise ExcelExportTokenError("Excel export link has expired")

    return ExcelExportClaims(
        cashflow_id=cashflow_id,
        unit_id=unit_id,
        project_name=project_name,
        expires_at=expires_at,
    )
