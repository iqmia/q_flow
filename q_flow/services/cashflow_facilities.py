"""Pure helpers for addressing financing facilities embedded in a Cashflow.

Facilities deliberately remain plain JSON dictionaries so a complete Cashflow
scenario stays portable. These helpers provide stable IDs and object-level CRUD
without introducing a separate persistence model.
"""

from copy import deepcopy
from math import isfinite
from typing import Any, Mapping, Sequence

from q_flow.exceptions import InvalidData, ProjectNotFound
from q_flow.financing import FACILITY_PRESETS
from q_flow.services.utils import gen_id


def _copy_facilities(facilities: object) -> list[dict[str, Any]]:
    InvalidData.require_condition(
        isinstance(facilities, list),
        "Financing facilities must be a list",
    )
    result: list[dict[str, Any]] = []
    for facility in facilities:
        InvalidData.require_condition(
            isinstance(facility, dict),
            "Each financing facility must be an object",
        )
        result.append(deepcopy(facility))
    return result


def new_facilities_with_defaults(facilities: object) -> list[dict[str, Any]]:
    """Copy new facility inputs and fill omitted fields from backend presets.

    Use only at explicit creation/import boundaries, never on saved scenario
    reads, edits or calculation. Explicit zeros and entered costs are preserved.
    An omitted type and custom facility types use the ``Other`` preset.
    Contract-specific schedules and percentages remain caller inputs.
    Catalog explanation metadata is not added to the saved source inputs.
    """
    result = _copy_facilities(facilities)
    fallback = next(item for item in FACILITY_PRESETS if item["key"] == "other")
    for facility in result:
        facility.setdefault("type", "Other")
        preset = next(
            (item for item in FACILITY_PRESETS if item["type"] == facility.get("type")),
            fallback,
        )
        for field in ("draw_method", "repayment_method", "revolving", "interest_rate"):
            facility.setdefault(field, preset[field])
        if "fees" not in facility:
            facility["fees"] = _default_facility_fee(facility, preset)
        facility.setdefault("start", 0)
    return result


def _default_facility_fee(facility: Mapping[str, Any], preset: Mapping[str, Any]) -> float:
    """Resolve a new facility's omitted fee without masking invalid inputs.

    A limit is the facility value, including for revolving scheduled draws.
    Only unlimited scheduled facilities fall back to their planned draw total.
    Unknown values retain the catalog fallback; validation handles bad inputs.
    """
    rate = preset["default_fees_rate"]
    if not rate:
        return preset["fees"]

    def valid_amount(value: Any) -> bool:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and isfinite(value) and value >= 0)

    value = facility.get("limit")
    if value is None and facility.get("draw_method") == "scheduled":
        schedule = facility.get("draw_schedule", {})
        if isinstance(schedule, dict) and all(valid_amount(item) for item in schedule.values()):
            value = sum(schedule.values())
    if not valid_amount(value):
        return preset["fees"]
    return round(value * rate, 2)


def normalize_facility_ids(
    facilities: object,
) -> tuple[list[dict[str, Any]], bool]:
    """Return a copied facility list with stable IDs assigned where missing.

    Version-1 portable scenarios created before MCP support may contain no
    facility IDs. Assign them lazily when the scenario is next read/edited
    rather than requiring a database migration.
    """
    result = _copy_facilities(facilities)
    changed = False
    seen: set[str] = set()
    for facility in result:
        facility_id = facility.get("id")
        if not isinstance(facility_id, str) or not facility_id.strip():
            facility_id = gen_id()
            facility["id"] = facility_id
            changed = True
        else:
            facility_id = facility_id.strip()
            if facility["id"] != facility_id:
                facility["id"] = facility_id
                changed = True
        InvalidData.require_condition(
            facility_id not in seen,
            "Financing facility ids must be unique",
        )
        seen.add(facility_id)
    return result, changed


def get_facility(facilities: object, facility_id: str) -> dict[str, Any]:
    result, _ = normalize_facility_ids(facilities)
    for facility in result:
        if facility["id"] == facility_id:
            return facility
    ProjectNotFound.require_condition(False, "Financing facility not found")
    raise AssertionError("unreachable")


def add_facility(
    facilities: object,
    data: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    InvalidData.require_condition(
        isinstance(data, Mapping),
        "Financing facility must be an object",
    )
    result, _ = normalize_facility_ids(facilities)
    new_facility = new_facilities_with_defaults([dict(data)])[0]
    facility_id = new_facility.get("id")
    if not isinstance(facility_id, str) or not facility_id.strip():
        facility_id = gen_id()
    else:
        facility_id = facility_id.strip()
    InvalidData.require_condition(
        all(item["id"] != facility_id for item in result),
        "Financing facility id must be unique",
    )
    new_facility["id"] = facility_id
    result.append(new_facility)
    return result, deepcopy(new_facility)


def update_facility(
    facilities: object,
    facility_id: str,
    data: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    InvalidData.require_condition(
        isinstance(data, Mapping),
        "Financing facility update must be an object",
    )
    result, _ = normalize_facility_ids(facilities)
    for index, facility in enumerate(result):
        if facility["id"] != facility_id:
            continue
        replacement = deepcopy(facility)
        for key, value in dict(data).items():
            if key != "id":
                replacement[key] = deepcopy(value)
        replacement["id"] = facility_id
        result[index] = replacement
        return result, deepcopy(replacement)
    ProjectNotFound.require_condition(False, "Financing facility not found")
    raise AssertionError("unreachable")


def delete_facility(
    facilities: object,
    facility_id: str,
) -> list[dict[str, Any]]:
    result, _ = normalize_facility_ids(facilities)
    remaining = [item for item in result if item["id"] != facility_id]
    ProjectNotFound.require_condition(
        len(remaining) != len(result),
        "Financing facility not found",
    )
    return remaining


def set_facility_order(
    facilities: object,
    facility_ids: Sequence[str],
) -> list[dict[str, Any]]:
    result, _ = normalize_facility_ids(facilities)
    InvalidData.require_condition(
        isinstance(facility_ids, (list, tuple))
        and all(isinstance(value, str) and value for value in facility_ids),
        "facility_ids must be a list of facility ids",
    )
    current_ids = [item["id"] for item in result]
    InvalidData.require_condition(
        len(facility_ids) == len(current_ids)
        and len(set(facility_ids)) == len(facility_ids)
        and set(facility_ids) == set(current_ids),
        "facility_ids must contain every current facility id exactly once",
    )
    by_id = {item["id"]: item for item in result}
    ordered: list[dict[str, Any]] = []
    for priority, facility_id in enumerate(facility_ids):
        facility = deepcopy(by_id[facility_id])
        facility["sweep_priority"] = priority
        ordered.append(facility)
    return ordered
