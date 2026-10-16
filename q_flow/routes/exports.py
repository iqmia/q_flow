"""CashflowPot export-link creation and stateless workbook delivery."""

from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, current_app, jsonify, send_file

from q_flow.models.cashflow import Cashflow
from q_flow.reports.cashflow_excel import build_cashflow_excel, excel_filename
from q_flow.services.decorators import auth_required
from q_flow.services.excel_export_tokens import (
    ExcelExportTokenError,
    create_excel_export_token,
    decode_excel_export_token,
)
from q_flow.services.units import (
    VIEW_CASHFLOW,
    ensure_unit_permission,
    load_project_unit,
)


exports = Blueprint("exports", __name__)
_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _active_cashflow(cashflow_id: str) -> Cashflow | None:
    cashflow = Cashflow.query.get(cashflow_id)
    if cashflow is None or cashflow.is_deleted:
        return None
    return cashflow


@exports.route("/cashflow/<cashflow_id>/excel-export", methods=["POST"])
@auth_required
def create_cashflow_excel_export(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    if cashflow is None:
        return jsonify(code="cashflow_not_found", message="Cashflow not found"), 404

    scoped = ensure_unit_permission(user, cashflow.unit_id, VIEW_CASHFLOW)
    if isinstance(scoped, tuple):
        return scoped

    loaded, error = load_project_unit(user, cashflow.unit_id)
    if error:
        return error
    _, unit = loaded
    project_name = (unit or {}).get("name") or "CashflowPot Project"

    now = _utc_now()
    ttl_seconds = int(current_app.config.get("EXCEL_EXPORT_TOKEN_TTL_SECONDS", 600))
    token, expires_at = create_excel_export_token(
        secret=current_app.config.get("SECRET_KEY", ""),
        cashflow_id=cashflow.id,
        unit_id=cashflow.unit_id,
        project_name=project_name,
        ttl_seconds=ttl_seconds,
        now=now,
    )
    public_api = str(
        current_app.config.get("PUBLIC_API_BASE_URL", "https://cashflowpot.com/api")
    ).rstrip("/")
    snapshot = cashflow.as_dict_with_activities()
    return jsonify(
        filename=excel_filename(project_name, snapshot),
        download_url=f"{public_api}/exports/cashflow/{token}.xlsx",
        expires_at=expires_at.isoformat(),
    ), 200


@exports.route("/exports/cashflow/<signed_token>.xlsx", methods=["GET"])
def download_cashflow_excel(signed_token):
    try:
        claims = decode_excel_export_token(
            secret=current_app.config.get("SECRET_KEY", ""),
            token=signed_token,
            now=_utc_now(),
        )
    except ExcelExportTokenError as error:
        return jsonify(code="invalid_export_token", message=str(error)), 401

    cashflow = _active_cashflow(claims.cashflow_id)
    if cashflow is None or cashflow.unit_id != claims.unit_id:
        # Deliberately use the same response for missing and claim mismatch so
        # a possession URL cannot be used to probe other project identifiers.
        return jsonify(code="cashflow_not_found", message="Cashflow not found"), 404

    snapshot = cashflow.as_dict_with_activities()
    workbook = build_cashflow_excel(
        project_name=claims.project_name,
        snapshot=snapshot,
    )
    return send_file(
        BytesIO(workbook),
        mimetype=_EXCEL_MIME,
        as_attachment=True,
        download_name=excel_filename(claims.project_name, snapshot),
        max_age=0,
    )
