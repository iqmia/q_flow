"""Canonical CashflowPot portable scenario contract.

The portable document contains source inputs only. Calculated series, ownership,
server identifiers and cached Activity cash-flow data are intentionally excluded
so the same versioned document can be imported into another project and
recalculated by q_flow.
"""

from copy import deepcopy
from typing import Any

from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow


PORTABLE_FORMAT = "cashflowpot.cashflow"
PORTABLE_VERSION = 1

CASHFLOW_SOURCE_FIELDS = (
    "name",
    "description",
    "advance",
    "retention",
    "release_retention_eop",
    "dlp",
    "duration_for_payment",
    "interest_rate",
    "contract_value",
    "wieb",
    "use_independent_inflow_curve",
    "inflow_curve_type",
    "inflow_curve_skew",
    "financing_facilities",
)

ACTIVITY_SOURCE_FIELDS = (
    "name",
    "activity_type",
    "activity_mode",
    "distribution_type",
    "cost_schedule_json",
    "cost",
    "duration",
    "duration_units",
    "start",
    "advance",
    "retention",
    "release_retention_eop",
    "dlp",
    "duration_for_payment",
    "work_in_excess",
    "mobilization_period",
    "subcontracted",
    "skew",
    "no_billing_period",
)


def _source_fields(model: object, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: deepcopy(getattr(model, field, None)) for field in fields}


def build_portable_cashflow(cashflow: Cashflow) -> dict[str, Any]:
    """Return a version-1 portable source document for ``cashflow``."""
    source = _source_fields(cashflow, CASHFLOW_SOURCE_FIELDS)
    source["activities"] = [
        _source_fields(activity, ACTIVITY_SOURCE_FIELDS)
        for activity in cashflow.activities
        if not activity.is_deleted
    ]
    return {
        "format": PORTABLE_FORMAT,
        "version": PORTABLE_VERSION,
        "cashflow": source,
    }
