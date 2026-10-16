from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import jwt
import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.cashflow import Cashflow
from q_flow.services.excel_export_tokens import (
    ExcelExportTokenError,
    create_excel_export_token,
    decode_excel_export_token,
)


NOW = datetime(2026, 10, 16, 16, 0, tzinfo=timezone.utc)
SECRET = "excel-export-test-secret"


def test_excel_export_token_round_trip_and_expiry():
    token, expires_at = create_excel_export_token(
        secret=SECRET,
        cashflow_id="cf-1",
        unit_id="unit-1",
        project_name="Harbour Tower",
        ttl_seconds=600,
        now=NOW,
    )

    assert expires_at == NOW + timedelta(seconds=600)
    claims = decode_excel_export_token(secret=SECRET, token=token, now=NOW)
    assert claims.cashflow_id == "cf-1"
    assert claims.unit_id == "unit-1"
    assert claims.project_name == "Harbour Tower"
    assert claims.expires_at == expires_at

    with pytest.raises(ExcelExportTokenError):
        decode_excel_export_token(
            secret=SECRET,
            token=token,
            now=NOW + timedelta(seconds=601),
        )


def test_excel_export_token_rejects_tampering_wrong_audience_and_purpose():
    token, _ = create_excel_export_token(
        secret=SECRET,
        cashflow_id="cf-1",
        unit_id="unit-1",
        project_name="Tower",
        ttl_seconds=600,
        now=NOW,
    )
    with pytest.raises(ExcelExportTokenError):
        decode_excel_export_token(secret="different-secret", token=token, now=NOW)

    base = {
        "iss": "cashflowpot",
        "aud": "cashflowpot-excel-export",
        "purpose": "cashflow_excel",
        "cashflow_id": "cf-1",
        "unit_id": "unit-1",
        "project_name": "Tower",
        "iat": int(NOW.timestamp()),
        "exp": int((NOW + timedelta(seconds=600)).timestamp()),
    }
    for change in (
        {"aud": "wrong"},
        {"purpose": "wrong"},
    ):
        bad = jwt.encode({**base, **change}, SECRET, algorithm="HS256")
        with pytest.raises(ExcelExportTokenError):
            decode_excel_export_token(secret=SECRET, token=bad, now=NOW)


@pytest.fixture
def app(tmp_path):
    class ExportConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)
        SECRET_KEY = SECRET
        PUBLIC_API_BASE_URL = "https://cashflowpot.com/api"
        EXCEL_EXPORT_TOKEN_TTL_SECONDS = 600

    app = create_app(ExportConfig)
    user = {
        "user_id": "owner-1",
        "name": "Owner",
        "is_active": True,
        "unit_id": "unit-1",
        "unit_permissions": ["view:cashflow", "edit:cashflow"],
        "token": "unit-token",
    }
    with patch("q_flow.services.decorators.u_api.verify_token", return_value=user):
        yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _auth():
    return {"Authorization": "Bearer unit-token"}


def _create_cashflow(app):
    with app.app_context():
        cashflow = Cashflow(
            id="cf-export",
            unit_id="unit-1",
            name="Tender / Base",
            description="Export me",
            created_by="owner-1",
            contract_value=0,
            advance=0,
            retention=0,
            release_retention_eop=0.5,
            dlp=0,
            duration_for_payment=0,
            interest_rate=0,
            wieb=0,
            financing_facilities=[],
        )
        db.session.add(cashflow)
        db.session.commit()


def test_creation_route_returns_short_lived_public_download_url(app):
    _create_cashflow(app)
    scoped = {"unit_id": "unit-1", "unit_permissions": ["view:cashflow"]}
    with (
        patch("q_flow.routes.exports.ensure_unit_permission", return_value=scoped),
        patch(
            "q_flow.routes.exports.load_project_unit",
            return_value=((scoped, {"id": "unit-1", "name": "Harbour Tower"}), None),
        ),
        patch("q_flow.routes.exports._utc_now", return_value=NOW),
    ):
        response = app.test_client().post(
            "/cashflow/cf-export/excel-export",
            headers=_auth(),
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["filename"] == "Harbour Tower - Tender - Base - Cash Flow.xlsx"
    assert data["download_url"].startswith(
        "https://cashflowpot.com/api/exports/cashflow/"
    )
    assert data["download_url"].endswith(".xlsx")
    assert data["expires_at"].startswith("2026-10-16T16:10:00")
    assert "unit-token" not in data["download_url"]


def test_download_route_streams_current_workbook_without_authorization_or_storage(app, tmp_path):
    _create_cashflow(app)
    token, _ = create_excel_export_token(
        secret=SECRET,
        cashflow_id="cf-export",
        unit_id="unit-1",
        project_name="Harbour Tower",
        ttl_seconds=600,
        now=NOW,
    )
    before = set(Path(tmp_path).rglob("*.xlsx"))

    with (
        patch("q_flow.routes.exports._utc_now", return_value=NOW),
        patch(
            "q_flow.routes.exports.build_cashflow_excel",
            return_value=b"PK\x03\x04fake-xlsx",
        ) as builder,
    ):
        response = app.test_client().get(
            f"/exports/cashflow/{token}.xlsx"
        )

    assert response.status_code == 200
    assert response.data == b"PK\x03\x04fake-xlsx"
    assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "Harbour Tower - Tender - Base - Cash Flow.xlsx" in response.headers["Content-Disposition"]
    builder.assert_called_once()
    assert set(Path(tmp_path).rglob("*.xlsx")) == before


def test_download_passes_deployed_cashflowpot_logo_to_excel_builder(app, tmp_path):
    _create_cashflow(app)
    logo = tmp_path / "qflow_logo.png"
    logo.write_bytes(b"cashflowpot-logo-bytes")
    app.config["EXCEL_LOGO_PATH"] = str(logo)
    token, _ = create_excel_export_token(
        secret=SECRET,
        cashflow_id="cf-export",
        unit_id="unit-1",
        project_name="Harbour Tower",
        ttl_seconds=600,
        now=NOW,
    )

    with (
        patch("q_flow.routes.exports._utc_now", return_value=NOW),
        patch(
            "q_flow.routes.exports.build_cashflow_excel",
            return_value=b"PK\x03\x04fake-xlsx",
        ) as builder,
    ):
        response = app.test_client().get(f"/exports/cashflow/{token}.xlsx")

    assert response.status_code == 200
    assert builder.call_args.kwargs["logo_bytes"] == b"cashflowpot-logo-bytes"


def test_download_rejects_expired_token_and_unit_mismatch(app):
    _create_cashflow(app)
    token, _ = create_excel_export_token(
        secret=SECRET,
        cashflow_id="cf-export",
        unit_id="unit-1",
        project_name="Harbour Tower",
        ttl_seconds=600,
        now=NOW,
    )
    with patch("q_flow.routes.exports._utc_now", return_value=NOW + timedelta(seconds=601)):
        expired = app.test_client().get(f"/exports/cashflow/{token}.xlsx")
    assert expired.status_code == 401

    wrong_unit, _ = create_excel_export_token(
        secret=SECRET,
        cashflow_id="cf-export",
        unit_id="other-unit",
        project_name="Harbour Tower",
        ttl_seconds=600,
        now=NOW,
    )
    with patch("q_flow.routes.exports._utc_now", return_value=NOW):
        mismatch = app.test_client().get(f"/exports/cashflow/{wrong_unit}.xlsx")
    assert mismatch.status_code == 404
