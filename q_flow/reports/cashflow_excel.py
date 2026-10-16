"""Backend CashflowPot Excel report matching the approved Flutter V3 layout."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from itertools import zip_longest
from pathlib import Path
from typing import Any, Mapping

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

from q_flow.reports.cashflow_excel_ooxml import finalize_excel_ooxml


PERIOD_START_COLUMN = 7  # H
GROUP_HEADER_ROW = 36  # Excel 37
ACTIVITY_HEADER_ROW = 37  # Excel 38
ACTIVITY_START_ROW = 38  # Excel 39
LAYOUT_END_COLUMN = 13  # N

BRAND = "F8B96E"
SLATE = "29323A"
WARM_NEUTRAL = "F4EEE8"
ASSUMPTION_FILL = "F1DFCB"
KPI_FILL = "F0E4D7"
WORK_BAR = "F8D5AE"
INFLOW = "5F8F73"
OUTFLOW = "C7775E"
BALANCE = "4F6D86"
MUTED = "667085"
RULE = "D4CEC7"
FACILITY_PASTELS = ("FFEBDD", "EAF5EE", "EAF1FA", "F3ECF8")
MONEY_FORMAT = "#,##0.0;[Red](#,##0.0);;@"
DISPLAY_MONEY_FORMAT = "#,##0.0;[Red](#,##0.0);0.0;@"
PERCENT_FORMAT = "0.0%;[Red](0.0%);0.0%;@"
INTEGER_FORMAT = "0;[Red](0);0;@"


@dataclass(frozen=True)
class FacilityLayout:
    draw_row: int
    repayment_row: int
    cost_row: int
    outstanding_row: int


@dataclass(frozen=True)
class CashflowLayout:
    project_header_row: int
    project_inflow_row: int
    project_cost_row: int
    facilities_header_row: int | None
    facilities: tuple[FacilityLayout, ...]
    cash_position_header_row: int
    total_inflow_row: int
    total_outflow_row: int
    net_row: int
    balance_row: int
    reconciliation_header_row: int
    note_row: int


def _flow(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    return [float(item or 0.0) if isinstance(item, (int, float)) and not isinstance(item, bool) else 0.0 for item in value]


def period_count_for(snapshot: Mapping[str, Any]) -> int:
    lengths = [
        len(_flow(snapshot.get("inflow"))),
        len(_flow(snapshot.get("outflow"))),
        len(_flow(snapshot.get("workflow"))),
        len(_flow(snapshot.get("outflow_with_interest"))),
        len(_flow(snapshot.get("netflow"))),
        len(_flow(snapshot.get("funded_netflow"))),
    ]
    for facility in snapshot.get("facility_rows") or []:
        if not isinstance(facility, Mapping):
            continue
        for key in ("draw", "repayment", "interest", "fees", "outstanding"):
            lengths.append(len(_flow(facility.get(key))))
    for activity in snapshot.get("activities") or []:
        cashflow = activity.get("cash_flow_json") or {}
        lengths.append(len(_flow(cashflow.get("marginal_work"))))
        lengths.append(len(_flow(cashflow.get("marginal_out_flow"))))
    return max(lengths, default=0)


def layout_for(snapshot: Mapping[str, Any]) -> CashflowLayout:
    activities = snapshot.get("activities") or []
    last_activity_row = (
        ACTIVITY_HEADER_ROW
        if not activities
        else ACTIVITY_START_ROW + len(activities) * 2 - 1
    )
    cursor = last_activity_row + 2
    project_header_row = cursor
    project_inflow_row = cursor + 1
    project_cost_row = cursor + 2
    cursor += 4

    facility_rows = snapshot.get("facility_rows") or []
    facilities_header_row: int | None = None
    facilities: list[FacilityLayout] = []
    if facility_rows:
        facilities_header_row = cursor
        cursor += 1
        for _ in facility_rows:
            facilities.append(
                FacilityLayout(
                    draw_row=cursor,
                    repayment_row=cursor + 1,
                    cost_row=cursor + 2,
                    outstanding_row=cursor + 3,
                )
            )
            cursor += 4
        cursor += 1

    cash_position_header_row = cursor
    total_inflow_row = cursor + 1
    total_outflow_row = cursor + 2
    net_row = cursor + 3
    balance_row = cursor + 4
    reconciliation_header_row = balance_row + 2
    note_row = reconciliation_header_row + 6
    return CashflowLayout(
        project_header_row=project_header_row,
        project_inflow_row=project_inflow_row,
        project_cost_row=project_cost_row,
        facilities_header_row=facilities_header_row,
        facilities=tuple(facilities),
        cash_position_header_row=cash_position_header_row,
        total_inflow_row=total_inflow_row,
        total_outflow_row=total_outflow_row,
        net_row=net_row,
        balance_row=balance_row,
        reconciliation_header_row=reconciliation_header_row,
        note_row=note_row,
    )


def _pad(values: Any, count: int) -> list[float]:
    source = _flow(values)
    return [source[index] if index < len(source) else 0.0 for index in range(count)]


def _safe_name(value: str) -> str:
    translation = str.maketrans({char: "-" for char in '<>:"/\\|?*'})
    return " ".join((value or "Cashflow").translate(translation).split())


def excel_filename(project_name: str, snapshot: Mapping[str, Any]) -> str:
    return f"{_safe_name(project_name)} - {_safe_name(str(snapshot.get('name') or 'Cashflow'))} - Cash Flow.xlsx"


def _styles(workbook):
    border = {"border": 1, "border_color": RULE}
    return {
        "brand": workbook.add_format({"font_name": "Arial", "font_size": 14, "bold": True, "font_color": SLATE, "valign": "vcenter"}),
        "project": workbook.add_format({"font_name": "Arial", "font_size": 15, "bold": True, "font_color": SLATE, "valign": "vcenter"}),
        "scenario": workbook.add_format({"font_name": "Arial", "font_size": 11, "bold": True, "font_color": SLATE, "valign": "vcenter"}),
        "subtitle": workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": MUTED, "valign": "vcenter", "text_wrap": True}),
        "section": workbook.add_format({"font_name": "Arial", "font_size": 11, "bold": True, "font_color": "FFFFFF", "bg_color": SLATE, "valign": "vcenter"}),
        "header": workbook.add_format({"font_name": "Arial", "font_size": 9, "bold": True, "font_color": "FFFFFF", "bg_color": SLATE, "align": "center", "valign": "vcenter", "text_wrap": True, "border": 1, "border_color": "FFFFFF"}),
        "assumption_label": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": SLATE, "bg_color": WARM_NEUTRAL, "valign": "vcenter"}),
        "money_value": workbook.add_format({"font_name": "Arial Narrow", "font_size": 11, "bold": True, "align": "right", "valign": "vcenter", "bg_color": ASSUMPTION_FILL, "num_format": DISPLAY_MONEY_FORMAT}),
        "percent_value": workbook.add_format({"font_name": "Arial Narrow", "font_size": 11, "bold": True, "align": "right", "valign": "vcenter", "bg_color": ASSUMPTION_FILL, "num_format": PERCENT_FORMAT}),
        "integer_value": workbook.add_format({"font_name": "Arial Narrow", "font_size": 11, "bold": True, "align": "right", "valign": "vcenter", "bg_color": ASSUMPTION_FILL, "num_format": INTEGER_FORMAT}),
        "kpi_label": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": MUTED, "bg_color": KPI_FILL, "valign": "vcenter"}),
        "kpi": workbook.add_format({"font_name": "Arial Narrow", "font_size": 12, "bold": True, "font_color": SLATE, "bg_color": KPI_FILL, "align": "right", "valign": "vcenter", "num_format": DISPLAY_MONEY_FORMAT}),
        "kpi_out": workbook.add_format({"font_name": "Arial Narrow", "font_size": 12, "bold": True, "font_color": OUTFLOW, "bg_color": KPI_FILL, "align": "right", "valign": "vcenter", "num_format": DISPLAY_MONEY_FORMAT}),
        "kpi_balance": workbook.add_format({"font_name": "Arial Narrow", "font_size": 12, "bold": True, "font_color": BALANCE, "bg_color": KPI_FILL, "align": "right", "valign": "vcenter", "num_format": DISPLAY_MONEY_FORMAT}),
        "activity": workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": SLATE, "bg_color": WARM_NEUTRAL, "valign": "vcenter"}),
        "activity_secondary": workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": MUTED, "valign": "vcenter"}),
        "number": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "font_color": SLATE, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT}),
        "number_bold": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": SLATE, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT}),
        "number_out": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "font_color": OUTFLOW, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT}),
        "work": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "font_color": SLATE, "bg_color": WORK_BAR, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT}),
        "link": workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": MUTED, "underline": 1, "align": "right", "valign": "vcenter"}),
        "summary": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": SLATE, "bg_color": WARM_NEUTRAL, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT, **border}),
        "summary_in": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": INFLOW, "bg_color": WARM_NEUTRAL, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT, **border}),
        "summary_out": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": OUTFLOW, "bg_color": WARM_NEUTRAL, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT, **border}),
        "summary_balance": workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": BALANCE, "bg_color": WARM_NEUTRAL, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT, **border}),
    }


def _merge_label_value(sheet, styles, row: int, label_start: int, label_end: int, value_col: int, label: str, value: Any, value_style, *, kpi=False):
    label_style = styles["kpi_label"] if kpi else styles["assumption_label"]
    if label_end > label_start:
        sheet.merge_range(row, label_start, row, label_end, label, label_style)
    else:
        sheet.write(row, label_start, label, label_style)
    if isinstance(value, str) and value.startswith("="):
        sheet.write_formula(row, value_col, value, value_style)
    else:
        sheet.write(row, value_col, value, value_style)


def _write_section_band(sheet, styles, row: int, title: str):
    sheet.merge_range(row, 0, row, LAYOUT_END_COLUMN, title, styles["section"])


def _configure(sheet, total_column: int):
    sheet.set_column(0, 0, 4)
    sheet.set_column(1, 1, 27)
    sheet.set_column(2, 2, 9.5)
    sheet.set_column(3, 4, 6.5)
    sheet.set_column(5, max(total_column, LAYOUT_END_COLUMN), 9.5)
    heights = {0: 40, 1: 22, 2: 18, 3: 30, 4: 20, 9: 20, 14: 20, 34: 8, 35: 8, GROUP_HEADER_ROW: 19, ACTIVITY_HEADER_ROW: 28}
    for row, height in heights.items():
        sheet.set_row(row, height)
    for row in range(5, 9):
        sheet.set_row(row, 18)
    for row in range(10, 14):
        sheet.set_row(row, 20)
    for row in range(15, 34):
        sheet.set_row(row, 12.75)
    sheet.hide_gridlines(2)
    sheet.set_landscape()
    sheet.set_paper(9)
    sheet.set_margins(0.19685, 0.19685, 0.19685, 0.19685)
    sheet.set_header("", {"margin": 0.15})
    sheet.set_footer("", {"margin": 0.15})


def _write_identity(sheet, styles, project_name: str, snapshot: Mapping[str, Any]):
    sheet.merge_range(0, 1, 0, LAYOUT_END_COLUMN - 1, "CashFlowPot", styles["brand"])
    sheet.write_url(0, LAYOUT_END_COLUMN, "https://cashflowpot.com", styles["link"], "generated by cashflowpot.com")
    sheet.merge_range(1, 1, 1, LAYOUT_END_COLUMN, project_name, styles["project"])
    sheet.merge_range(2, 1, 2, LAYOUT_END_COLUMN, str(snapshot.get("name") or ""), styles["scenario"])
    sheet.merge_range(3, 1, 3, LAYOUT_END_COLUMN, str(snapshot.get("description") or ""), styles["subtitle"])
    _write_section_band(sheet, styles, 4, "Contract & Financing Assumptions")


def _write_assumptions(sheet, styles, snapshot, period_count):
    summary = snapshot.get("summary") or {}
    work_duration = summary.get("work_duration") or snapshot.get("duration") or 0
    financial_horizon = summary.get("financial_horizon") or period_count
    values = [
        (5, 1, 1, 2, "Contract Value", snapshot.get("contract_value", 0), styles["money_value"]),
        (5, 5, 7, 8, "Client Advance", snapshot.get("advance", 0), styles["percent_value"]),
        (5, 10, 12, 13, "Client Retention", snapshot.get("retention", 0), styles["percent_value"]),
        (6, 1, 1, 2, "Retention Released at Completion", snapshot.get("release_retention_eop", 0), styles["percent_value"]),
        (6, 5, 7, 8, "Defects Liability Period", snapshot.get("dlp", 0), styles["integer_value"]),
        (6, 10, 12, 13, "Client Payment Delay", snapshot.get("duration_for_payment", 0), styles["integer_value"]),
        (7, 1, 1, 2, "Billing Deferral", snapshot.get("wieb", 0), styles["percent_value"]),
        (7, 5, 7, 8, "Financing Rate per Period", snapshot.get("interest_rate", 0), styles["percent_value"]),
        (7, 10, 12, 13, "Work Duration", work_duration, styles["integer_value"]),
        (8, 1, 1, 2, "Financial Horizon", financial_horizon, styles["integer_value"]),
    ]
    for item in values:
        _merge_label_value(sheet, styles, *item)


def _write_kpis(sheet, styles, snapshot, layout):
    _write_section_band(sheet, styles, 9, "Key Metrics")
    summary = snapshot.get("summary") or {}
    rows = [
        (10, 1, 1, 2, "Contract Value", "=C6", styles["kpi"]),
        (10, 5, 7, 8, "Direct Cost", float(summary.get("direct_cost") or 0), styles["kpi"]),
        (10, 10, 12, 13, "Financing Cost", float(summary.get("financing_cost") or 0), styles["kpi_out"]),
        (11, 1, 1, 2, "Total Forecast Cost", float(summary.get("total_cost") or 0), styles["kpi"]),
        (11, 5, 7, 8, "Forecast Margin Before Financing", float(snapshot.get("contract_value") or 0) - float(summary.get("direct_cost") or 0), styles["kpi"]),
        (11, 10, 12, 13, "Forecast Margin After Financing", float(snapshot.get("contract_value") or 0) - float(summary.get("total_cost") or 0), styles["kpi"]),
        (12, 1, 1, 2, "Closing Cash Balance", float(summary.get("final_cash_balance") or 0), styles["kpi_balance"]),
        (12, 5, 7, 8, "Peak Funding Requirement", float(summary.get("peak_pre_financing_need") or 0), styles["kpi_out"]),
        (12, 10, 12, 13, "Peak Funding Period", (summary.get("peak_pre_financing_period") if summary.get("peak_pre_financing_period") is not None else "-"), styles["integer_value"]),
        (13, 1, 1, 2, "Work Duration", int(summary.get("work_duration") or snapshot.get("duration") or 0), styles["integer_value"]),
        (13, 5, 7, 8, "Financial Horizon", int(summary.get("financial_horizon") or period_count_for(snapshot)), styles["integer_value"]),
        (13, 10, 12, 13, "Cash after debt settlement", float(summary.get("cash_after_debt_settlement") or 0), styles["kpi_balance"]),
    ]
    for item in rows:
        _merge_label_value(sheet, styles, *item, kpi=True)
    _write_section_band(sheet, styles, 14, "Charts")


def _write_schedule(sheet, styles, snapshot, period_count, total_column):
    sheet.merge_range(GROUP_HEADER_ROW, 0, GROUP_HEADER_ROW, 1, "Cashflow Schedule", styles["section"])
    headers = {2: "Duration", 3: "Start", 4: "Pre Work", 5: "Estimated Cost", 6: "Flow"}
    for col, title in headers.items():
        sheet.merge_range(GROUP_HEADER_ROW, col, ACTIVITY_HEADER_ROW, col, title, styles["header"])
    sheet.write(ACTIVITY_HEADER_ROW, 0, "No.", styles["header"])
    sheet.write(ACTIVITY_HEADER_ROW, 1, "Activity", styles["header"])
    for group_start in range(0, period_count, 4):
        start_col = PERIOD_START_COLUMN + group_start
        end_col = min(start_col + 3, PERIOD_START_COLUMN + period_count - 1)
        sheet.merge_range(GROUP_HEADER_ROW, start_col, GROUP_HEADER_ROW, end_col, f"Group {group_start // 4 + 1}", styles["header"])
    for period in range(period_count):
        sheet.write(ACTIVITY_HEADER_ROW, PERIOD_START_COLUMN + period, period + 1, styles["header"])
    sheet.merge_range(GROUP_HEADER_ROW, total_column, ACTIVITY_HEADER_ROW, total_column, "Total / Closing", styles["header"])

    for index, activity in enumerate(snapshot.get("activities") or []):
        main_row = ACTIVITY_START_ROW + index * 2
        outflow_row = main_row + 1
        sheet.set_row(main_row, 15)
        sheet.set_row(outflow_row, 15)
        cashflow = activity.get("cash_flow_json") or {}
        work = _pad(cashflow.get("marginal_work"), period_count)
        outflow = _pad(cashflow.get("marginal_out_flow"), period_count)
        mode = activity.get("activity_mode") or "work"
        flow_name = "Scheduled cost" if mode == "scheduled_cost" else "Work"
        sheet.write(main_row, 0, index + 1, styles["activity"])
        sheet.write(main_row, 1, activity.get("name") or "", styles["activity"])
        sheet.write(main_row, 2, activity.get("duration") or 0, styles["activity"])
        sheet.write(main_row, 3, int(activity.get("start") or 0) + 1, styles["activity"])
        sheet.write(main_row, 4, activity.get("mobilization_period") or 0, styles["activity"])
        sheet.write(main_row, 5, float(activity.get("cost") or 0), styles["number_bold"])
        sheet.write(main_row, 6, flow_name, styles["activity"])
        sheet.write(outflow_row, 6, "Outflow", styles["activity_secondary"])
        for period in range(period_count):
            sheet.write(main_row, PERIOD_START_COLUMN + period, work[period], styles["work"] if work[period] else styles["number"])
            sheet.write(outflow_row, PERIOD_START_COLUMN + period, outflow[period], styles["number_out"])
        # V3 totals use exact source activity cost so rounded period cells cannot drift.
        source_cost_cell = xl_rowcol_to_cell(main_row, 5)
        sheet.write_formula(main_row, total_column, f"={source_cost_cell}", styles["number_bold"])
        sheet.write_formula(outflow_row, total_column, f"={source_cost_cell}", styles["number_out"])


def _cashflow_row_formats(workbook, background: str, font_color: str):
    border = {"top": 1, "bottom": 1, "top_color": RULE, "bottom_color": RULE}
    item = workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": SLATE, "bg_color": background, "align": "center", "valign": "vcenter", **border})
    title = workbook.add_format({"font_name": "Arial", "font_size": 9, "bold": True, "font_color": SLATE, "bg_color": background, "valign": "vcenter", "text_wrap": True, **border})
    number = workbook.add_format({"font_name": "Arial Narrow", "font_size": 9, "bold": True, "font_color": font_color, "bg_color": background, "align": "right", "valign": "vcenter", "num_format": MONEY_FORMAT, **border})
    return item, title, number


def _write_cashflow_section_header(sheet, styles, row, title, period_count):
    sheet.merge_range(row, 0, row, 6, title, styles["section"])
    for period in range(period_count):
        sheet.write(row, PERIOD_START_COLUMN + period, period + 1, styles["header"])


def _write_cashflow_value_row(workbook, sheet, row, label, values, period_count, *, item_number=None, color=SLATE, background=WARM_NEUTRAL, total_formula=None, closing_total=False):
    item, title, number = _cashflow_row_formats(workbook, background, color)
    sheet.write(row, 0, item_number if item_number is not None else "", item)
    sheet.merge_range(row, 1, row, 4, label, title)
    sheet.merge_range(row, 5, row, 6, "", number)
    for period in range(period_count):
        sheet.write(row, PERIOD_START_COLUMN + period, values[period], number)
    if total_formula:
        sheet.write_formula(row, 5, total_formula, number)
    elif period_count:
        if closing_total:
            sheet.write_formula(row, 5, f"={xl_rowcol_to_cell(row, PERIOD_START_COLUMN + period_count - 1)}", number)
        else:
            first = xl_rowcol_to_cell(row, PERIOD_START_COLUMN)
            last = xl_rowcol_to_cell(row, PERIOD_START_COLUMN + period_count - 1)
            sheet.write_formula(row, 5, f"=SUM({first}:{last})", number)


def _write_cashflow_sections(workbook, sheet, styles, snapshot, layout, period_count):
    _write_cashflow_section_header(sheet, styles, layout.project_header_row, "PROJECT CASHFLOW", period_count)
    _write_cashflow_value_row(workbook, sheet, layout.project_inflow_row, "Project inflow\nClient PPC receipts", _pad(snapshot.get("inflow"), period_count), period_count, item_number=1, color=INFLOW, total_formula="=C6")
    activities = snapshot.get("activities") or []
    if activities:
        last_activity_row = ACTIVITY_START_ROW + len(activities) * 2 - 1
        project_cost_total = f"=SUM(F{ACTIVITY_START_ROW + 1}:F{last_activity_row + 1})"
    else:
        project_cost_total = None
    _write_cashflow_value_row(workbook, sheet, layout.project_cost_row, "Project cost\nWork + scheduled costs", _pad(snapshot.get("outflow"), period_count), period_count, item_number=2, color=OUTFLOW, total_formula=project_cost_total)

    facility_rows = snapshot.get("facility_rows") or []
    if layout.facilities_header_row is not None:
        _write_cashflow_section_header(sheet, styles, layout.facilities_header_row, "FACILITIES", period_count)
        for index, facility in enumerate(facility_rows):
            rows = layout.facilities[index]
            background = FACILITY_PASTELS[index % len(FACILITY_PASTELS)]
            name_format = workbook.add_format({"font_name": "Arial", "font_size": 9, "bold": True, "font_color": SLATE, "bg_color": background, "align": "center", "valign": "vcenter", "rotation": 90, "text_wrap": True, "top": 1, "bottom": 1, "top_color": RULE, "bottom_color": RULE})
            sheet.merge_range(rows.draw_row, 0, rows.outstanding_row, 0, str(facility.get("name") or f"Facility {index + 1}"), name_format)
            draw = _pad(facility.get("draw"), period_count)
            repayment = _pad(facility.get("repayment"), period_count)
            interest = _pad(facility.get("interest"), period_count)
            fees = _pad(facility.get("fees"), period_count)
            costs = [a + b for a, b in zip(interest, fees)]
            outstanding = _pad(facility.get("outstanding"), period_count)
            _write_cashflow_value_row(workbook, sheet, rows.draw_row, "Draw", draw, period_count, color=INFLOW, background=background)
            _write_cashflow_value_row(workbook, sheet, rows.repayment_row, "Repayment", repayment, period_count, color=OUTFLOW, background=background)
            _write_cashflow_value_row(workbook, sheet, rows.cost_row, "Interest & fees", costs, period_count, color=OUTFLOW, background=background)
            _write_cashflow_value_row(workbook, sheet, rows.outstanding_row, "Outstanding balance", outstanding, period_count, color=BALANCE, background=background, closing_total=True)
            # Restore merged vertical facility name after row writers touched column A.
            sheet.merge_range(rows.draw_row, 0, rows.outstanding_row, 0, str(facility.get("name") or f"Facility {index + 1}"), name_format)

    _write_cashflow_section_header(sheet, styles, layout.cash_position_header_row, "CASH POSITION", period_count)
    cash_start = 3 + len(layout.facilities)
    labels = [
        (layout.total_inflow_row, "Total inflow", cash_start, INFLOW),
        (layout.total_outflow_row, "Total outflow", cash_start + 1, OUTFLOW),
        (layout.net_row, "Net cash flow", cash_start + 2, SLATE),
        (layout.balance_row, "Closing cash balance", cash_start + 3, BALANCE),
    ]
    for row, label, number, color in labels:
        _write_cashflow_value_row(workbook, sheet, row, label, [0.0] * period_count, period_count, item_number=number, color=color)

    for period in range(period_count):
        col = PERIOD_START_COLUMN + period
        project_inflow = xl_rowcol_to_cell(layout.project_inflow_row, col)
        project_cost = xl_rowcol_to_cell(layout.project_cost_row, col)
        draws = [xl_rowcol_to_cell(rows.draw_row, col) for rows in layout.facilities]
        outs = [cell for rows in layout.facilities for cell in (xl_rowcol_to_cell(rows.repayment_row, col), xl_rowcol_to_cell(rows.cost_row, col))]
        total_inflow = xl_rowcol_to_cell(layout.total_inflow_row, col)
        total_outflow = xl_rowcol_to_cell(layout.total_outflow_row, col)
        net = xl_rowcol_to_cell(layout.net_row, col)
        sheet.write_formula(layout.total_inflow_row, col, "=" + "+".join([project_inflow, *draws]), styles["summary_in"])
        sheet.write_formula(layout.total_outflow_row, col, "=" + "+".join([project_cost, *outs]), styles["summary_out"])
        sheet.write_formula(layout.net_row, col, f"={total_inflow}-{total_outflow}", styles["summary"])
        if period == 0:
            balance_formula = f"={net}"
        else:
            prior = xl_rowcol_to_cell(layout.balance_row, col - 1)
            balance_formula = f"={prior}+{net}"
        sheet.write_formula(layout.balance_row, col, balance_formula, styles["summary_balance"])

    # Fixed totals in F:G, matching V3 final framing.
    project_inflow_total = xl_rowcol_to_cell(layout.project_inflow_row, 5)
    project_cost_total = xl_rowcol_to_cell(layout.project_cost_row, 5)
    draw_totals = [xl_rowcol_to_cell(rows.draw_row, 5) for rows in layout.facilities]
    out_totals = [cell for rows in layout.facilities for cell in (xl_rowcol_to_cell(rows.repayment_row, 5), xl_rowcol_to_cell(rows.cost_row, 5))]
    sheet.write_formula(layout.total_inflow_row, 5, "=" + "+".join([project_inflow_total, *draw_totals]), styles["summary_in"])
    sheet.write_formula(layout.total_outflow_row, 5, "=" + "+".join([project_cost_total, *out_totals]), styles["summary_out"])
    sheet.write_formula(layout.net_row, 5, f"={xl_rowcol_to_cell(layout.total_inflow_row, 5)}-{xl_rowcol_to_cell(layout.total_outflow_row, 5)}", styles["summary"])
    if period_count:
        sheet.write_formula(layout.balance_row, 5, f"={xl_rowcol_to_cell(layout.balance_row, PERIOD_START_COLUMN + period_count - 1)}", styles["summary_balance"])


def _write_reconciliation(sheet, styles, snapshot, layout):
    _write_section_band(sheet, styles, layout.reconciliation_header_row, "Reconciliation")
    summary = snapshot.get("summary") or {}
    lines = [
        ("Contract value", float(snapshot.get("contract_value") or 0)),
        ("Project direct cost", float(summary.get("direct_cost") or 0)),
        ("Financing cost", float(summary.get("financing_cost") or 0)),
        ("Closing cash balance", float(summary.get("final_cash_balance") or 0)),
    ]
    for offset, (label, value) in enumerate(lines, 1):
        row = layout.reconciliation_header_row + offset
        sheet.merge_range(row, 1, row, 3, label, styles["assumption_label"])
        sheet.merge_range(row, 4, row, 5, value, styles["money_value"])
    sheet.merge_range(layout.note_row, 1, layout.note_row + 1, LAYOUT_END_COLUMN, "CashFlowPot report. All project and financing calculations are supplied by the authoritative CashflowPot backend; workbook formulas present and reconcile those results.", styles["subtitle"])


def _add_charts(workbook, sheet, layout, period_count):
    if period_count <= 0:
        return
    last_col = PERIOD_START_COLUMN + period_count - 1
    movement = workbook.add_chart({"type": "column"})
    movement.add_series({"name": "Total inflow", "categories": ["Cash Flow", ACTIVITY_HEADER_ROW, PERIOD_START_COLUMN, ACTIVITY_HEADER_ROW, last_col], "values": ["Cash Flow", layout.total_inflow_row, PERIOD_START_COLUMN, layout.total_inflow_row, last_col], "fill": {"color": INFLOW}, "border": {"color": INFLOW}})
    movement.add_series({"name": "Total outflow", "categories": ["Cash Flow", ACTIVITY_HEADER_ROW, PERIOD_START_COLUMN, ACTIVITY_HEADER_ROW, last_col], "values": ["Cash Flow", layout.total_outflow_row, PERIOD_START_COLUMN, layout.total_outflow_row, last_col], "fill": {"color": OUTFLOW}, "border": {"color": OUTFLOW}})
    movement.set_title({"name": "Cash Movement by Period"})
    movement.set_legend({"position": "bottom"})
    movement.set_chartarea({"fill": {"color": "FBE7D6"}, "border": {"none": True}})
    movement.set_plotarea({"fill": {"color": "FFFFFF"}, "border": {"none": True}})

    liquidity = workbook.add_chart({"type": "line"})
    liquidity.add_series({"name": "Closing cash balance", "categories": ["Cash Flow", ACTIVITY_HEADER_ROW, PERIOD_START_COLUMN, ACTIVITY_HEADER_ROW, last_col], "values": ["Cash Flow", layout.balance_row, PERIOD_START_COLUMN, layout.balance_row, last_col], "line": {"color": BALANCE, "width": 2.25}})
    liquidity.set_title({"name": "Liquidity / Funding Profile"})
    liquidity.set_legend({"position": "bottom"})
    liquidity.set_chartarea({"fill": {"color": "FBE7D6"}, "border": {"none": True}})
    liquidity.set_plotarea({"fill": {"color": "FFFFFF"}, "border": {"none": True}})

    # XlsxWriter creates chart parts/relationships; the finalizer replaces only
    # drawing anchors with the approved absolute EMU geometry.
    sheet.insert_chart("I16", movement, {"x_scale": 1.0, "y_scale": 1.0})
    sheet.insert_chart("B16", liquidity, {"x_scale": 1.0, "y_scale": 1.0})


def build_cashflow_excel(*, project_name: str, snapshot: Mapping[str, Any]) -> bytes:
    """Build the approved CashflowPot workbook entirely in memory."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties({"title": "CashFlowPot Cash Flow", "company": "Quollnet"})
    sheet = workbook.add_worksheet("Cash Flow")
    styles = _styles(workbook)
    period_count = period_count_for(snapshot)
    total_column = PERIOD_START_COLUMN + period_count
    layout = layout_for(snapshot)
    _configure(sheet, total_column)
    _write_identity(sheet, styles, project_name, snapshot)
    _write_assumptions(sheet, styles, snapshot, period_count)
    _write_kpis(sheet, styles, snapshot, layout)
    _write_schedule(sheet, styles, snapshot, period_count, total_column)
    _write_cashflow_sections(workbook, sheet, styles, snapshot, layout, period_count)
    _write_reconciliation(sheet, styles, snapshot, layout)
    _add_charts(workbook, sheet, layout, period_count)
    sheet.set_print_area(0, 0, layout.note_row + 1, max(total_column, LAYOUT_END_COLUMN))
    sheet.fit_to_pages(1, 0)
    workbook.close()
    return finalize_excel_ooxml(output.getvalue())
