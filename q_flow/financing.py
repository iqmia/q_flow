"""Period-by-period cashflow calculation for financing facilities.

Facility definitions are plain dictionaries so the engine can be tested without
database access and used by API serialization and portable cashflow imports.
Rates and amounts are expressed per model period and in the cashflow currency.
"""

from math import isfinite


FACILITY_PRESETS = (
    {"key": "letter_of_credit", "type": "Letter of Credit", "draw_method": "scheduled", "repayment_method": "percent_of_ppc", "revolving": False},
    {"key": "overdraft", "type": "Overdraft", "draw_method": "automatic_shortfall", "repayment_method": "cashflow_sweep", "revolving": True},
    {"key": "ppc_discount", "type": "PPC Discount", "draw_method": "ppc_base", "repayment_method": "percent_of_ppc", "revolving": False},
    {"key": "working_capital", "type": "Working Capital", "draw_method": "scheduled", "repayment_method": "percent_of_ppc", "revolving": False},
    {"key": "equipment_loan", "type": "Equipment Loan", "draw_method": "scheduled", "repayment_method": "scheduled", "revolving": False},
    {"key": "owners_injection", "type": "Owner's Injection", "draw_method": "automatic_shortfall", "repayment_method": "cashflow_sweep", "revolving": False},
    {"key": "other", "type": "Other", "draw_method": "scheduled", "repayment_method": "cashflow_sweep", "revolving": False},
)


def _amount(values, period):
    return float(values[period]) if period < len(values) else 0.0


def _schedule_amount(schedule, period):
    if not isinstance(schedule, dict):
        return 0.0
    value = schedule.get(period, schedule.get(str(period), 0.0))
    return float(value or 0.0)


def _period_count(inflows, outflows, ppc_base, ppc_issued, facilities):
    lengths = [len(inflows), len(outflows), len(ppc_base), len(ppc_issued)]
    for facility in facilities:
        lengths.extend([
            int(facility.get("end") or 0) + 1,
            max((int(period) for period in (facility.get("draw_schedule") or {})), default=-1) + 1,
            max((int(period) for period in (facility.get("repayment_schedule") or {})), default=-1) + 1,
        ])
        if facility.get("repayment_method") == "equal_installments":
            count = int(facility.get("installment_count", 0))
            interval = max(1, int(facility.get("installment_interval", 1)))
            start = int(facility.get("installment_start", 0))
            if count > 0:
                lengths.append(start + (count - 1) * interval + 1)
    return max(lengths, default=0)


def _available_limit(facility, total_drawn, outstanding):
    limit = facility.get("limit")
    if limit is None:
        return float("inf")
    basis = outstanding if facility.get("revolving", False) else total_drawn
    return max(0.0, float(limit) - basis)


def _repayment_due(facility, period, installment_amount, ppc_base):
    method = facility.get("repayment_method", "cashflow_sweep")
    if method == "scheduled":
        return _schedule_amount(facility.get("repayment_schedule"), period)
    if method == "percent_of_ppc":
        return _amount(ppc_base, period) * float(facility.get("repayment_percent", 0.0))
    if method == "equal_installments":
        start = int(facility.get("installment_start", 0))
        interval = max(1, int(facility.get("installment_interval", 1)))
        count = int(facility.get("installment_count", 0))
        if count > 0 and period >= start and (period - start) % interval == 0:
            return installment_amount
    return 0.0


def calculate_financing(*, inflows, outflows, ppc_base, ppc_issued, facilities):
    """Calculate facility flows while preserving the project's cash position.

    Scheduled and PPC-linked draws are entered in full when eligible. They are
    limited by available facility capacity. Contractual repayments are applied
    in full up to outstanding principal, even when they make project cash
    negative. Cashflow sweeps use only positive cash and follow sweep_priority.
    Automatic shortfall draws run after contractual repayments: overdrafts first,
    then owner/contractor contributions to cover the residual.
    """
    facilities = [dict(facility) for facility in facilities]
    period_count = _period_count(inflows, outflows, ppc_base, ppc_issued, facilities)
    cash_balance = 0.0
    total_project_inflows = []
    total_facility_draws = []
    total_principal_repayments = []
    total_interest = []
    total_fees = []
    net_cash_flow = []
    funded_cash_balance = []
    unfunded_shortfall = []
    facility_rows = []
    state = []

    for index, facility in enumerate(facilities):
        facility.setdefault("sweep_priority", index)
        facility.setdefault("revolving", False)
        facility.setdefault("interest_rate", 0.0)
        facility.setdefault("fees", 0.0)
        state.append({"outstanding": 0.0, "total_drawn": 0.0, "fee_charged": False})
        if facility.get("draw_method") == "scheduled":
            planned_draw = sum(
                float(value or 0.0)
                for value in (facility.get("draw_schedule") or {}).values()
            )
        elif facility.get("draw_method") == "ppc_base":
            planned_draw = sum(ppc_issued) * float(facility.get("advance_portion", 0.0))
        else:
            planned_draw = 0.0
        if not facility.get("revolving", False) and facility.get("limit") is not None:
            planned_draw = min(planned_draw, float(facility["limit"]))
        facility["_equal_installment_amount"] = (
            planned_draw / max(1, int(facility.get("installment_count", 1)))
        )
        facility_rows.append({
            "id": facility.get("id"),
            "name": facility.get("name", "Facility"),
            "type": facility.get("type", "Other"),
            "draw_method": facility.get("draw_method", "scheduled"),
            "repayment_method": facility.get("repayment_method", "cashflow_sweep"),
            "draw": [],
            "repayment": [],
            "interest": [],
            "fees": [],
            "outstanding": [],
            "available_limit": [],
            "unfunded_draw": [],
        })

    for period in range(period_count):
        project_inflow = _amount(inflows, period)
        project_outflow = _amount(outflows, period)
        period_interest = [0.0] * len(facilities)
        period_fees = [0.0] * len(facilities)
        period_draws = [0.0] * len(facilities)
        period_repayments = [0.0] * len(facilities)
        period_unfunded_draw = [0.0] * len(facilities)
        opening_outstanding = [entry["outstanding"] for entry in state]

        # Accrue interest on each facility's opening principal. A facility drawn
        # in this period starts accruing interest in the next period.
        for index, facility in enumerate(facilities):
            period_interest[index] = (
                opening_outstanding[index] * float(facility.get("interest_rate", 0.0))
            )
            start = int(facility.get("start", 0))
            if period == start and not state[index]["fee_charged"]:
                period_fees[index] = float(facility.get("fees", 0.0))
                state[index]["fee_charged"] = True

        cash_before_financing = cash_balance + project_inflow - project_outflow
        cash_balance = cash_before_financing - sum(period_interest) - sum(period_fees)

        # Fixed schedule and PPC-base draws happen as planned. Capacity limits
        # still apply; rejected portions are reported explicitly.
        for index, facility in enumerate(facilities):
            method = facility.get("draw_method", "scheduled")
            start = int(facility.get("start", 0))
            end = facility.get("end")
            eligible = period >= start and (end is None or period <= int(end))
            requested = 0.0
            if eligible and method == "scheduled":
                requested = _schedule_amount(facility.get("draw_schedule"), period)
            elif eligible and method == "ppc_base":
                requested = (
                    _amount(ppc_issued, period)
                    * float(facility.get("advance_portion", 0.0))
                )
            if requested <= 0:
                continue
            capacity = _available_limit(
                facility, state[index]["total_drawn"], state[index]["outstanding"]
            )
            draw = min(requested, capacity)
            period_draws[index] += draw
            period_unfunded_draw[index] += requested - draw
            state[index]["outstanding"] += draw
            state[index]["total_drawn"] += draw
            cash_balance += draw

        # Contractual repayments are not conditional on positive project cash.
        for index, facility in enumerate(facilities):
            if facility.get("repayment_method") in (None, "cashflow_sweep"):
                continue
            due = _repayment_due(
                facility,
                period,
                facility["_equal_installment_amount"],
                ppc_base,
            )
            repayment = min(max(0.0, due), state[index]["outstanding"])
            period_repayments[index] += repayment
            state[index]["outstanding"] -= repayment
            cash_balance -= repayment

        # Sweep repayments are the only repayments constrained by available cash.
        sweep_indices = sorted(
            (index for index, facility in enumerate(facilities)
             if facility.get("repayment_method") == "cashflow_sweep"),
            key=lambda index: (
                (0, int(facilities[index]["sweep_priority"]), index)
                if facilities[index].get("sweep_priority") is not None
                else (1, -float(facilities[index].get("interest_rate", 0.0)), index)
            ),
        )
        for index in sweep_indices:
            if cash_balance <= 0:
                break
            repayment = min(cash_balance, state[index]["outstanding"])
            period_repayments[index] += repayment
            state[index]["outstanding"] -= repayment
            cash_balance -= repayment

        # Automatic shortfall sources are ordered by product behavior. OD-like
        # facilities draw first; calculated contractor/owner injection covers
        # whatever remains without a stated limit.
        auto_indices = [
            index for index, facility in enumerate(facilities)
            if facility.get("draw_method") == "automatic_shortfall"
        ]
        auto_indices.sort(key=lambda index: (
            0 if str(facilities[index].get("type", "")).lower() in {"overdraft", "od"} else 1,
            index,
        ))
        for index in auto_indices:
            if cash_balance >= 0:
                break
            facility = facilities[index]
            start = int(facility.get("start", 0))
            end = facility.get("end")
            if period < start or (end is not None and period > int(end)):
                continue
            needed = -cash_balance
            capacity = _available_limit(
                facility, state[index]["total_drawn"], state[index]["outstanding"]
            )
            draw = min(needed, capacity)
            period_draws[index] += draw
            state[index]["outstanding"] += draw
            state[index]["total_drawn"] += draw
            cash_balance += draw

        for index, facility in enumerate(facilities):
            row = facility_rows[index]
            row["draw"].append(round(period_draws[index], 2))
            row["repayment"].append(round(period_repayments[index], 2))
            row["interest"].append(round(period_interest[index], 2))
            row["fees"].append(round(period_fees[index], 2))
            row["outstanding"].append(round(state[index]["outstanding"], 2))
            capacity = _available_limit(
                facility, state[index]["total_drawn"], state[index]["outstanding"]
            )
            row["available_limit"].append(
                None if capacity == float("inf") else round(capacity, 2)
            )
            row["unfunded_draw"].append(round(period_unfunded_draw[index], 2))

        total_draw = sum(period_draws)
        total_repayment = sum(period_repayments)
        total_interest_period = sum(period_interest)
        total_fees_period = sum(period_fees)
        net = (
            project_inflow + total_draw
            - project_outflow - total_repayment
            - total_interest_period - total_fees_period
        )
        total_project_inflows.append(round(project_inflow, 2))
        total_facility_draws.append(round(total_draw, 2))
        total_principal_repayments.append(round(total_repayment, 2))
        total_interest.append(round(total_interest_period, 2))
        total_fees.append(round(total_fees_period, 2))
        net_cash_flow.append(round(net, 2))
        funded_cash_balance.append(round(cash_balance, 2))
        unfunded_shortfall.append(round(max(0.0, -cash_balance), 2))

    return {
        "facilities": facility_rows,
        "project_inflows": total_project_inflows,
        "facility_draws": total_facility_draws,
        "principal_repayments": total_principal_repayments,
        "facility_interest": total_interest,
        "facility_fees": total_fees,
        "net_cash_flow": net_cash_flow,
        "pre_financing_balance": [round(value, 2) for value in _cumulative(inflows, outflows, period_count)],
        "funded_cash_balance": funded_cash_balance,
        "unfunded_shortfall": unfunded_shortfall,
    }


def _cumulative(inflows, outflows, period_count):
    balance = 0.0
    values = []
    for period in range(period_count):
        balance += _amount(inflows, period) - _amount(outflows, period)
        values.append(balance)
    return values


def validate_financing_facilities(facilities):
    """Validate the stored facility payload and return field-level messages."""
    errors = []
    if not isinstance(facilities, list):
        return ["Financing facilities must be a list"]
    methods_draw = {"automatic_shortfall", "scheduled", "ppc_base"}
    methods_repay = {"cashflow_sweep", "percent_of_ppc", "equal_installments", "scheduled"}
    names = set()
    for index, facility in enumerate(facilities):
        prefix = f"Facility {index + 1}"
        if not isinstance(facility, dict):
            errors.append(f"{prefix} must be an object")
            continue
        name = facility.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix} name must be non-empty text")
        elif name.strip().casefold() in names:
            errors.append(f"{prefix} name must be unique")
        else:
            names.add(name.strip().casefold())
        facility_type = facility.get("type")
        if not isinstance(facility_type, str) or not facility_type.strip():
            errors.append(f"{prefix} type must be non-empty text")
        if facility.get("draw_method") not in methods_draw:
            errors.append(f"{prefix} draw method is invalid")
        if facility.get("repayment_method") not in methods_repay:
            errors.append(f"{prefix} repayment method is invalid")
        for field in ("start", "end"):
            value = facility.get(field)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                errors.append(f"{prefix} {field.replace('_', ' ')} must be a non-negative period")
        for field in ("limit", "fees", "interest_rate", "advance_portion", "repayment_percent"):
            value = facility.get(field)
            if value is None and field == "limit":
                continue
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value < 0
            ):
                errors.append(f"{prefix} {field.replace('_', ' ')} must be a finite non-negative number")
        if (
            facility.get("limit") is None
            and str(facility_type or "").casefold() not in {"owner's injection", "contractor contribution"}
        ):
            errors.append(f"{prefix} limit is required")
        for field in ("advance_portion", "repayment_percent"):
            value = facility.get(field)
            if value is not None and value > 1:
                errors.append(f"{prefix} {field.replace('_', ' ')} must not exceed one")
        start_period = facility.get("start", 0)
        end_period = facility.get("end")
        if (
            isinstance(start_period, int) and not isinstance(start_period, bool)
            and isinstance(end_period, int) and not isinstance(end_period, bool)
            and start_period > end_period
        ):
            errors.append(f"{prefix} end must not precede start")
        if not isinstance(facility.get("revolving", False), bool):
            errors.append(f"{prefix} revolving must be boolean")
        priority = facility.get("sweep_priority")
        if priority is not None and (
            not isinstance(priority, int) or isinstance(priority, bool) or priority < 0
        ):
            errors.append(f"{prefix} sweep priority must be a non-negative integer")
        for field in ("draw_schedule", "repayment_schedule"):
            schedule = facility.get(field, {})
            if not isinstance(schedule, dict):
                errors.append(f"{prefix} {field.replace('_', ' ')} must be an object")
                continue
            for period, value in schedule.items():
                try:
                    parsed_period = int(period)
                except (TypeError, ValueError):
                    parsed_period = -1
                if parsed_period < 0:
                    errors.append(f"{prefix} {field.replace('_', ' ')} periods must be non-negative integers")
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                    errors.append(f"{prefix} {field.replace('_', ' ')} amounts must be finite non-negative numbers")
        if facility.get("repayment_method") == "equal_installments":
            for field in ("installment_start", "installment_interval", "installment_count"):
                value = facility.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < (1 if field != "installment_start" else 0):
                    errors.append(f"{prefix} {field.replace('_', ' ')} is invalid")
        if facility.get("draw_method") == "ppc_base" and facility.get("advance_portion") is None:
            errors.append(f"{prefix} advance portion is required for PPC-base draws")
        if facility.get("repayment_method") == "percent_of_ppc" and facility.get("repayment_percent") is None:
            errors.append(f"{prefix} repayment percentage is required for PPC repayments")
    return errors
