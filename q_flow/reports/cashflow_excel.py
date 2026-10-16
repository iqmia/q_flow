"""Backend CashflowPot Excel report matching the approved Flutter V3 layout."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Mapping

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from q_flow.reports.cashflow_excel_ooxml import finalize_excel_ooxml

PERIOD_START_COLUMN = 7
GROUP_HEADER_ROW = 36
ACTIVITY_HEADER_ROW = 37
ACTIVITY_START_ROW = 38
LAYOUT_END_COLUMN = 13

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
    return [
        float(item or 0.0)
        if isinstance(item, (int, float)) and not isinstance(item, bool)
        else 0.0
        for item in value
    ]


def _pad(value: Any, count: int) -> list[float]:
    values = _flow(value)
    return [values[i] if i < len(values) else 0.0 for i in range(count)]


def period_count_for(snapshot: Mapping[str, Any]) -> int:
    lengths = [
        len(_flow(snapshot.get(key)))
        for key in (
            "inflow",
            "outflow",
            "workflow",
            "outflow_with_interest",
            "netflow",
            "funded_netflow",
        )
    ]
    for facility in snapshot.get("facility_rows") or []:
        for key in ("draw", "repayment", "interest", "fees", "outstanding"):
            lengths.append(len(_flow(facility.get(key))))
    for activity in snapshot.get("activities") or []:
        values = activity.get("cash_flow_json") or {}
        lengths.append(len(_flow(values.get("marginal_work"))))
        lengths.append(len(_flow(values.get("marginal_out_flow"))))
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
    facilities_header_row = None
    facilities: list[FacilityLayout] = []
    if snapshot.get("facility_rows"):
        facilities_header_row = cursor
        cursor += 1
        for _ in snapshot["facility_rows"]:
            facilities.append(
                FacilityLayout(cursor, cursor + 1, cursor + 2, cursor + 3)
            )
            cursor += 4
        cursor += 1
    cash_position_header_row = cursor
    return CashflowLayout(
        project_header_row,
        project_inflow_row,
        project_cost_row,
        facilities_header_row,
        tuple(facilities),
        cash_position_header_row,
        cash_position_header_row + 1,
        cash_position_header_row + 2,
        cash_position_header_row + 3,
        cash_position_header_row + 4,
        cash_position_header_row + 6,
        cash_position_header_row + 12,
    )


def _safe_name(value: str) -> str:
    for char in '<>:"/\\|?*':
        value = value.replace(char, "-")
    return " ".join(value.split()).strip() or "Cashflow"


def excel_filename(project_name: str, snapshot: Mapping[str, Any]) -> str:
    return (
        f"{_safe_name(project_name)} - "
        f"{_safe_name(str(snapshot.get('name') or 'Cashflow'))} - Cash Flow.xlsx"
    )


def _styles(workbook):
    def fmt(**kwargs):
        return workbook.add_format(kwargs)

    number = {
        "font_name": "Arial Narrow",
        "font_size": 9,
        "align": "right",
        "valign": "vcenter",
        "num_format": MONEY_FORMAT,
    }
    summary = {
        **number,
        "bold": True,
        "bg_color": WARM_NEUTRAL,
        "top": 1,
        "bottom": 1,
        "top_color": RULE,
        "bottom_color": RULE,
    }
    return {
        "brand": fmt(
            font_name="Arial", font_size=14, bold=True, font_color=SLATE,
            valign="vcenter"
        ),
        "project": fmt(
            font_name="Arial", font_size=15, bold=True, font_color=SLATE,
            valign="vcenter"
        ),
        "scenario": fmt(
            font_name="Arial", font_size=11, bold=True, font_color=SLATE,
            valign="vcenter"
        ),
        "subtitle": fmt(
            font_name="Arial", font_size=9, font_color=MUTED,
            valign="vcenter", text_wrap=True
        ),
        "section": fmt(
            font_name="Arial", font_size=11, bold=True, font_color="FFFFFF",
            bg_color=SLATE, valign="vcenter"
        ),
        "table_header": fmt(
            font_name="Arial", font_size=9, bold=True, font_color="FFFFFF",
            bg_color=SLATE, align="center", valign="vcenter", text_wrap=True
        ),
        "grouped_header": fmt(
            font_name="Arial", font_size=9, bold=True, font_color="FFFFFF",
            bg_color=SLATE, align="center", valign="vcenter", text_wrap=True,
            left=1, right=1, bottom=1,
            left_color="FFFFFF", right_color="FFFFFF", bottom_color="FFFFFF"
        ),
        "assumption_label": fmt(
            font_name="Arial", font_size=10, font_color=SLATE,
            bg_color=WARM_NEUTRAL, valign="vcenter"
        ),
        "money_value": fmt(
            font_name="Arial Narrow", font_size=11, bold=True, align="right",
            valign="vcenter", bg_color=ASSUMPTION_FILL,
            num_format=DISPLAY_MONEY_FORMAT
        ),
        "percent_value": fmt(
            font_name="Arial Narrow", font_size=11, bold=True, align="right",
            valign="vcenter", bg_color=ASSUMPTION_FILL,
            num_format=PERCENT_FORMAT
        ),
        "integer_value": fmt(
            font_name="Arial Narrow", font_size=11, bold=True, align="right",
            valign="vcenter", bg_color=ASSUMPTION_FILL,
            num_format=INTEGER_FORMAT
        ),
        "kpi_label": fmt(
            font_name="Arial", font_size=10, font_color=MUTED,
            bg_color=KPI_FILL, valign="vcenter"
        ),
        "kpi": fmt(
            font_name="Arial Narrow", font_size=12, bold=True,
            font_color=SLATE, bg_color=KPI_FILL, align="right",
            valign="vcenter", num_format=DISPLAY_MONEY_FORMAT
        ),
        "kpi_out": fmt(
            font_name="Arial Narrow", font_size=12, bold=True,
            font_color=OUTFLOW, bg_color=KPI_FILL, align="right",
            valign="vcenter", num_format=DISPLAY_MONEY_FORMAT
        ),
        "kpi_balance": fmt(
            font_name="Arial Narrow", font_size=12, bold=True,
            font_color=BALANCE, bg_color=KPI_FILL, align="right",
            valign="vcenter", num_format=DISPLAY_MONEY_FORMAT
        ),
        "kpi_integer": fmt(
            font_name="Arial Narrow", font_size=12, bold=True,
            font_color=SLATE, bg_color=KPI_FILL, align="right",
            valign="vcenter", num_format=INTEGER_FORMAT
        ),
        "activity": fmt(
            font_name="Arial", font_size=9, font_color=SLATE,
            bg_color=WARM_NEUTRAL, valign="vcenter"
        ),
        "activity_secondary": fmt(
            font_name="Arial", font_size=9, font_color=MUTED,
            valign="vcenter"
        ),
        "number": fmt(**number, font_color=SLATE),
        "number_bold": fmt(**number, font_color=SLATE, bold=True),
        "number_out": fmt(**number, font_color=OUTFLOW),
        "work": fmt(**number, font_color=SLATE, bg_color=WORK_BAR),
        "link": fmt(
            font_name="Arial", font_size=9, font_color=MUTED, underline=1,
            align="right", valign="vcenter"
        ),
        "label": fmt(
            font_name="Arial", font_size=10, font_color=SLATE,
            valign="vcenter"
        ),
        "label_bold": fmt(
            font_name="Arial", font_size=10, bold=True, font_color=SLATE,
            valign="vcenter"
        ),
        "summary": fmt(**summary, font_color=SLATE),
        "summary_in": fmt(**summary, font_color=INFLOW),
        "summary_out": fmt(**summary, font_color=OUTFLOW),
        "summary_balance": fmt(**summary, font_color=BALANCE),
    }


def _configure(sheet, total_column: int):
    sheet.set_column(0, 0, 4)
    sheet.set_column(1, 1, 27)
    sheet.set_column(2, 2, 9.5)
    sheet.set_column(3, 4, 6.5)
    sheet.set_column(5, max(total_column, LAYOUT_END_COLUMN), 9.5)
    sheet.set_column(8, 8, 11.5)  # Flutter final polish widens I.
    for row, height in {
        0: 40,
        1: 22,
        2: 18,
        3: 30,
        4: 20,
        9: 20,
        14: 20,
        34: 8,
        35: 8,
        36: 19,
        37: 28,
    }.items():
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


def _section(sheet, styles, row: int, title: str):
    sheet.merge_range(row, 0, row, LAYOUT_END_COLUMN, title, styles["section"])


def _label_value(
    sheet,
    styles,
    row,
    start,
    end,
    value_col,
    label,
    value,
    value_style,
    *,
    kpi=False,
):
    label_style = styles["kpi_label"] if kpi else styles["assumption_label"]
    if start == end:
        sheet.write(row, start, label, label_style)
    else:
        sheet.merge_range(row, start, row, end, label, label_style)

    # Flutter's final pass merges the left value block C:D.
    if value_col == 2:
        sheet.merge_range(row, 2, row, 3, value, value_style)
    elif isinstance(value, str) and value.startswith("="):
        sheet.write_formula(row, value_col, value, value_style)
    else:
        sheet.write(row, value_col, value, value_style)


def _write_top(sheet, styles, project_name, snapshot, periods):
    # The Flutter final pass unmerges row one to make room for the logo and the
    # generated-by link, then indents the brand with non-breaking spaces.
    sheet.write(0, 1, "\u00a0" * 10 + "CashFlowPot", styles["brand"])
    sheet.write_formula(
        0,
        13,
        '=HYPERLINK("https://cashflowpot.com","generated by cashflowpot.com")',
        styles["link"],
    )
    sheet.merge_range(1, 1, 1, 13, project_name, styles["project"])
    sheet.merge_range(
        2, 1, 2, 13, str(snapshot.get("name") or ""), styles["scenario"]
    )
    sheet.merge_range(
        3, 1, 3, 13, str(snapshot.get("description") or ""), styles["subtitle"]
    )
    _section(sheet, styles, 4, "Contract & Financing Assumptions")
    summary = snapshot.get("summary") or {}
    for item in [
        (5, 1, 1, 2, "Contract Value", snapshot.get("contract_value", 0), styles["money_value"]),
        (5, 5, 7, 8, "Client Advance", snapshot.get("advance", 0), styles["percent_value"]),
        (5, 10, 12, 13, "Client Retention", snapshot.get("retention", 0), styles["percent_value"]),
        (6, 1, 1, 2, "Retention Released at Completion", snapshot.get("release_retention_eop", 0), styles["percent_value"]),
        (6, 5, 7, 8, "Defects Liability Period", snapshot.get("dlp", 0), styles["integer_value"]),
        (6, 10, 12, 13, "Client Payment Delay", snapshot.get("duration_for_payment", 0), styles["integer_value"]),
        (7, 1, 1, 2, "Billing Deferral", snapshot.get("wieb", 0), styles["percent_value"]),
        (7, 5, 7, 8, "Financing Rate per Period", snapshot.get("interest_rate", 0), styles["percent_value"]),
        (7, 10, 12, 13, "Work Duration", summary.get("work_duration") or snapshot.get("duration") or 0, styles["integer_value"]),
        (8, 1, 1, 2, "Financial Horizon", summary.get("financial_horizon") or periods, styles["integer_value"]),
    ]:
        _label_value(sheet, styles, *item)

    _section(sheet, styles, 9, "Key Metrics")
    for item in [
        (10, 1, 1, 2, "Contract Value", "=C6", styles["kpi"]),
        (10, 5, 7, 8, "Direct Cost", 0, styles["kpi"]),
        (10, 10, 12, 13, "Financing Cost", 0, styles["kpi_out"]),
        (11, 1, 1, 2, "Total Forecast Cost", "=I11+N11", styles["kpi"]),
        (11, 5, 7, 8, "Forecast Margin Before Financing", "=C11-I11", styles["kpi"]),
        (11, 10, 12, 13, "Forecast Margin After Financing", "=C11-C12", styles["kpi"]),
        (12, 1, 1, 2, "Closing Cash Balance", 0, styles["kpi_balance"]),
        (12, 5, 7, 8, "Peak Funding Requirement", 0, styles["kpi_out"]),
        (12, 10, 12, 13, "Peak Funding Period", "-", styles["kpi_integer"]),
        (13, 1, 1, 2, "Work Duration", "=N8", styles["kpi_integer"]),
        (13, 5, 7, 8, "Financial Horizon", "=C9", styles["kpi_integer"]),
        (13, 10, 12, 13, "Cash after debt settlement", 0, styles["kpi_balance"]),
    ]:
        _label_value(sheet, styles, *item, kpi=True)
    _section(sheet, styles, 14, "Charts")


def _write_schedule(sheet, styles, snapshot, periods, total_col):
    sheet.merge_range(36, 0, 36, 1, "Cashflow Schedule", styles["section"])
    for col, title in {
        2: "Duration",
        3: "Start",
        4: "Pre Work",
        5: "Estimated Cost",
        6: "Flow",
    }.items():
        sheet.merge_range(36, col, 37, col, title, styles["table_header"])
    sheet.write(37, 0, "No.", styles["table_header"])
    sheet.write(37, 1, "Activity", styles["table_header"])
    for start in range(0, periods, 4):
        first = 7 + start
        last = min(first + 3, 7 + periods - 1)
        sheet.merge_range(
            36, first, 36, last, f"Group {start // 4 + 1}", styles["grouped_header"]
        )
    for period in range(periods):
        sheet.write(37, 7 + period, period + 1, styles["grouped_header"])
    sheet.merge_range(
        36, total_col, 37, total_col, "Total / Closing", styles["grouped_header"]
    )

    for index, activity in enumerate(snapshot.get("activities") or []):
        row = 38 + index * 2
        out = row + 1
        values = activity.get("cash_flow_json") or {}
        work = _pad(values.get("marginal_work"), periods)
        flow = _pad(values.get("marginal_out_flow"), periods)
        for col, value in [
            (0, index + 1),
            (1, activity.get("name") or ""),
            (2, activity.get("duration") or 0),
            (3, int(activity.get("start") or 0) + 1),
            (4, activity.get("mobilization_period") or 0),
        ]:
            sheet.write(row, col, value, styles["activity"])
        sheet.write(row, 5, float(activity.get("cost") or 0), styles["number_bold"])
        sheet.write(
            row,
            6,
            "Scheduled cost"
            if activity.get("activity_mode") == "scheduled_cost"
            else "Work",
            styles["activity"],
        )
        sheet.write(out, 6, "Outflow", styles["activity_secondary"])
        for period in range(periods):
            sheet.write(
                row,
                7 + period,
                work[period],
                styles["work"] if work[period] else styles["number"],
            )
            sheet.write(out, 7 + period, flow[period], styles["number_out"])
        cost = xl_rowcol_to_cell(row, 5)
        sheet.write_formula(row, total_col, f"={cost}", styles["number_bold"])
        sheet.write_formula(out, total_col, f"={cost}", styles["number_out"])


def _row_formats(workbook, background, color):
    borders = {
        "top": 1,
        "bottom": 1,
        "top_color": RULE,
        "bottom_color": RULE,
    }
    return (
        workbook.add_format(
            {
                "font_name": "Arial Narrow",
                "font_size": 9,
                "bold": True,
                "font_color": SLATE,
                "bg_color": background,
                "align": "center",
                "valign": "vcenter",
                **borders,
            }
        ),
        workbook.add_format(
            {
                "font_name": "Arial",
                "font_size": 9,
                "bold": True,
                "font_color": SLATE,
                "bg_color": background,
                "text_wrap": True,
                "valign": "vcenter",
                **borders,
            }
        ),
        workbook.add_format(
            {
                "font_name": "Arial Narrow",
                "font_size": 9,
                "bold": True,
                "font_color": color,
                "bg_color": background,
                "align": "right",
                "valign": "vcenter",
                "num_format": MONEY_FORMAT,
                **borders,
            }
        ),
    )


def _value_row(
    workbook,
    sheet,
    row,
    label,
    values,
    periods,
    *,
    item_number=None,
    color=SLATE,
    background=WARM_NEUTRAL,
    total_formula=None,
    closing=False,
    write_item=True,
):
    item, title, number = _row_formats(workbook, background, color)
    sheet.set_row(row, 25 if "\n" in label else 18)
    if write_item:
        sheet.write(row, 0, "" if item_number is None else item_number, item)
    sheet.merge_range(row, 1, row, 4, label, title)
    sheet.merge_range(row, 5, row, 6, "", number)
    for period in range(periods):
        sheet.write(row, 7 + period, values[period], number)
    if total_formula:
        sheet.write_formula(row, 5, total_formula, number)
    elif periods:
        last = xl_rowcol_to_cell(row, 7 + periods - 1)
        if closing:
            sheet.write_formula(row, 5, f"={last}", number)
        else:
            sheet.write_formula(
                row,
                5,
                f"=SUM({xl_rowcol_to_cell(row, 7)}:{last})",
                number,
            )


def _cash_header(sheet, styles, row, title, periods):
    sheet.set_row(row, 19)
    sheet.merge_range(row, 0, row, 6, title, styles["section"])
    for period in range(periods):
        sheet.write(row, 7 + period, period + 1, styles["table_header"])


def _add_formula(cells: list[str]) -> str:
    if not cells:
        return "0"
    return "+".join(cells)


def _write_cashflow(workbook, sheet, styles, snapshot, layout, periods):
    _cash_header(sheet, styles, layout.project_header_row, "PROJECT CASHFLOW", periods)
    _value_row(
        workbook,
        sheet,
        layout.project_inflow_row,
        "Project inflow\nClient PPC receipts",
        _pad(snapshot.get("inflow"), periods),
        periods,
        item_number=1,
        color=INFLOW,
        total_formula="=C6",
    )
    activities = snapshot.get("activities") or []
    cost_formula = None
    if activities:
        cost_formula = f"=SUM(F39:F{ACTIVITY_START_ROW + len(activities) * 2})"
    _value_row(
        workbook,
        sheet,
        layout.project_cost_row,
        "Project cost\nWork + scheduled costs",
        _pad(snapshot.get("outflow"), periods),
        periods,
        item_number=2,
        color=OUTFLOW,
        total_formula=cost_formula,
    )

    facilities = snapshot.get("facility_rows") or []
    if layout.facilities_header_row is not None:
        _cash_header(sheet, styles, layout.facilities_header_row, "FACILITIES", periods)
        for index, facility in enumerate(facilities):
            rows = layout.facilities[index]
            background = FACILITY_PASTELS[index % len(FACILITY_PASTELS)]
            draw = _pad(facility.get("draw"), periods)
            repayment = _pad(facility.get("repayment"), periods)
            interest = _pad(facility.get("interest"), periods)
            fees = _pad(facility.get("fees"), periods)
            _value_row(
                workbook, sheet, rows.draw_row, "Draw", draw, periods,
                color=INFLOW, background=background, write_item=False
            )
            _value_row(
                workbook, sheet, rows.repayment_row, "Repayment", repayment, periods,
                color=OUTFLOW, background=background, write_item=False
            )
            _value_row(
                workbook,
                sheet,
                rows.cost_row,
                "Interest & fees",
                [left + right for left, right in zip(interest, fees)],
                periods,
                color=OUTFLOW,
                background=background,
                write_item=False,
            )
            _value_row(
                workbook,
                sheet,
                rows.outstanding_row,
                "Outstanding balance",
                _pad(facility.get("outstanding"), periods),
                periods,
                color=BALANCE,
                background=background,
                closing=True,
                write_item=False,
            )
            name_format = workbook.add_format(
                {
                    "font_name": "Arial",
                    "font_size": 9,
                    "bold": True,
                    "font_color": SLATE,
                    "bg_color": background,
                    "align": "center",
                    "valign": "vcenter",
                    "rotation": 90,
                    "text_wrap": True,
                    "top": 1,
                    "bottom": 1,
                    "top_color": RULE,
                    "bottom_color": RULE,
                }
            )
            sheet.merge_range(
                rows.draw_row,
                0,
                rows.outstanding_row,
                0,
                facility.get("name") or f"Facility {index + 1}",
                name_format,
            )

    _cash_header(sheet, styles, layout.cash_position_header_row, "CASH POSITION", periods)
    start = 3 + len(layout.facilities)
    for row, label, number, color in [
        (layout.total_inflow_row, "Total inflow", start, INFLOW),
        (layout.total_outflow_row, "Total outflow", start + 1, OUTFLOW),
        (layout.net_row, "Net cash flow", start + 2, SLATE),
        (layout.balance_row, "Closing cash balance", start + 3, BALANCE),
    ]:
        _value_row(
            workbook,
            sheet,
            row,
            label,
            [0.0] * periods,
            periods,
            item_number=number,
            color=color,
        )

    for period in range(periods):
        column = 7 + period
        project_inflow = xl_rowcol_to_cell(layout.project_inflow_row, column)
        project_outflow = xl_rowcol_to_cell(layout.project_cost_row, column)
        draws = [xl_rowcol_to_cell(rows.draw_row, column) for rows in layout.facilities]
        outflows = [
            cell
            for rows in layout.facilities
            for cell in (
                xl_rowcol_to_cell(rows.repayment_row, column),
                xl_rowcol_to_cell(rows.cost_row, column),
            )
        ]
        total_inflow = xl_rowcol_to_cell(layout.total_inflow_row, column)
        total_outflow = xl_rowcol_to_cell(layout.total_outflow_row, column)
        net = xl_rowcol_to_cell(layout.net_row, column)
        sheet.write_formula(
            layout.total_inflow_row,
            column,
            "=" + _add_formula([project_inflow, *draws]),
            styles["summary_in"],
        )
        sheet.write_formula(
            layout.total_outflow_row,
            column,
            "=" + _add_formula([project_outflow, *outflows]),
            styles["summary_out"],
        )
        sheet.write_formula(
            layout.net_row,
            column,
            f"={total_inflow}-{total_outflow}",
            styles["summary"],
        )
        sheet.write_formula(
            layout.balance_row,
            column,
            f"={net}"
            if period == 0
            else f"={xl_rowcol_to_cell(layout.balance_row, column - 1)}+{net}",
            styles["summary_balance"],
        )

    project_inflow_total = xl_rowcol_to_cell(layout.project_inflow_row, 5)
    project_cost_total = xl_rowcol_to_cell(layout.project_cost_row, 5)
    draw_totals = [xl_rowcol_to_cell(rows.draw_row, 5) for rows in layout.facilities]
    repayment_and_cost_totals = [
        cell
        for rows in layout.facilities
        for cell in (
            xl_rowcol_to_cell(rows.repayment_row, 5),
            xl_rowcol_to_cell(rows.cost_row, 5),
        )
    ]
    sheet.write_formula(
        layout.total_inflow_row,
        5,
        "=" + _add_formula([project_inflow_total, *draw_totals]),
        styles["summary_in"],
    )
    sheet.write_formula(
        layout.total_outflow_row,
        5,
        "=" + _add_formula([project_cost_total, *repayment_and_cost_totals]),
        styles["summary_out"],
    )
    sheet.write_formula(
        layout.net_row,
        5,
        f"={xl_rowcol_to_cell(layout.total_inflow_row, 5)}-"
        f"{xl_rowcol_to_cell(layout.total_outflow_row, 5)}",
        styles["summary"],
    )
    if periods:
        sheet.write_formula(
            layout.balance_row,
            5,
            f"={xl_rowcol_to_cell(layout.balance_row, 7 + periods - 1)}",
            styles["summary_balance"],
        )


def _patch_kpis(sheet, styles, snapshot, layout):
    summary = snapshot.get("summary") or {}
    project_cost_total = xl_rowcol_to_cell(layout.project_cost_row, 5)
    closing_cash_total = xl_rowcol_to_cell(layout.balance_row, 5)
    facility_cost_totals = [
        xl_rowcol_to_cell(rows.cost_row, 5) for rows in layout.facilities
    ]
    outstanding_totals = [
        xl_rowcol_to_cell(rows.outstanding_row, 5) for rows in layout.facilities
    ]

    sheet.write_formula(10, 8, f"={project_cost_total}", styles["kpi"])
    if facility_cost_totals:
        sheet.write_formula(
            10, 13, "=" + _add_formula(facility_cost_totals), styles["kpi_out"]
        )
    else:
        sheet.write(10, 13, 0, styles["kpi_out"])
    sheet.write_formula(12, 2, f"={closing_cash_total}", styles["kpi_balance"])

    minimum = float(summary.get("minimum_pre_financing_balance") or 0.0)
    sheet.write(12, 8, minimum if minimum < 0 else 0, styles["kpi_out"])
    period = summary.get("minimum_pre_financing_period")
    if minimum < 0 and period is not None:
        sheet.write(12, 13, int(period) + 1, styles["kpi_integer"])
    else:
        sheet.write(12, 13, "-", styles["kpi_integer"])

    if outstanding_totals:
        formula = f"={closing_cash_total}-({_add_formula(outstanding_totals)})"
    else:
        formula = f"={closing_cash_total}"
    sheet.write_formula(13, 13, formula, styles["kpi_balance"])


def _write_reconciliation(sheet, styles, snapshot, layout):
    _section(sheet, styles, layout.reconciliation_header_row, "Reconciliation & Notes")
    summary = snapshot.get("summary") or {}
    fallback = _flow(snapshot.get("outflow_with_interest"))
    reference = float(summary.get("final_cash_balance") or 0.0)
    if reference == 0.0 and fallback:
        reference = fallback[-1]

    rows = [
        ("CashFlowPot Reference Closing Balance", reference, "value"),
        (
            "Workbook Closing Balance",
            f"={xl_rowcol_to_cell(layout.balance_row, 5)}",
            "formula",
        ),
        (
            "Difference",
            f"={xl_rowcol_to_cell(layout.reconciliation_header_row + 2, 4)}-"
            f"{xl_rowcol_to_cell(layout.reconciliation_header_row + 1, 4)}",
            "formula",
        ),
        (
            "Status",
            f'=IF(ABS({xl_rowcol_to_cell(layout.reconciliation_header_row + 3, 4)})<=1,"OK","CHECK")',
            "status",
        ),
    ]
    for offset, (label, value, kind) in enumerate(rows, 1):
        row = layout.reconciliation_header_row + offset
        sheet.set_row(row, 18)
        sheet.merge_range(
            row,
            1,
            row,
            3,
            label,
            styles["label_bold"] if kind == "status" else styles["label"],
        )
        if kind == "value":
            sheet.merge_range(row, 4, row, 5, value, styles["number"])
        elif kind == "status":
            sheet.merge_range(row, 4, row, 5, value, styles["label_bold"])
        else:
            sheet.merge_range(row, 4, row, 5, value, styles["number"])

    note = (
        "All monetary amounts are shown in the project's reporting currency. "
        "Timing is expressed in model periods. Facility rows use the calculated "
        "financing result; interest and fees are combined for reporting."
    )
    sheet.merge_range(
        layout.note_row,
        1,
        layout.note_row,
        LAYOUT_END_COLUMN,
        note,
        styles["subtitle"],
    )
    sheet.set_row(layout.note_row, 28)


def _add_charts(workbook, sheet, layout, periods):
    if not periods:
        return
    last = 7 + periods - 1
    movement = workbook.add_chart({"type": "column"})
    for name, row, color in [
        ("Total inflow", layout.total_inflow_row, INFLOW),
        ("Total outflow", layout.total_outflow_row, OUTFLOW),
    ]:
        movement.add_series(
            {
                "name": name,
                "categories": ["Cash Flow", 37, 7, 37, last],
                "values": ["Cash Flow", row, 7, row, last],
                "fill": {"color": color},
                "border": {"color": color},
            }
        )
    movement.set_title({"name": "Cash Movement by Period"})
    movement.set_legend({"position": "bottom"})
    movement.set_chartarea({"fill": {"color": "FBE7D6"}, "border": {"none": True}})

    liquidity = workbook.add_chart({"type": "line"})
    liquidity.add_series(
        {
            "name": "Closing cash balance",
            "categories": ["Cash Flow", 37, 7, 37, last],
            "values": ["Cash Flow", layout.balance_row, 7, layout.balance_row, last],
            "line": {"color": BALANCE, "width": 2.25},
        }
    )
    liquidity.set_title({"name": "Liquidity / Funding Profile"})
    liquidity.set_legend({"position": "bottom"})
    liquidity.set_chartarea({"fill": {"color": "FBE7D6"}, "border": {"none": True}})
    sheet.insert_chart("I16", movement)
    sheet.insert_chart("B16", liquidity)


def build_cashflow_excel(
    *,
    project_name: str,
    snapshot: Mapping[str, Any],
    logo_bytes: bytes | None = None,
) -> bytes:
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties({"title": "CashFlowPot Cash Flow", "company": "Quollnet"})
    sheet = workbook.add_worksheet("Cash Flow")
    styles = _styles(workbook)
    periods = period_count_for(snapshot)
    total_column = PERIOD_START_COLUMN + periods
    layout = layout_for(snapshot)

    _configure(sheet, total_column)
    _write_top(sheet, styles, project_name, snapshot, periods)
    _write_schedule(sheet, styles, snapshot, periods, total_column)
    _write_cashflow(workbook, sheet, styles, snapshot, layout, periods)
    _patch_kpis(sheet, styles, snapshot, layout)
    _write_reconciliation(sheet, styles, snapshot, layout)
    _add_charts(workbook, sheet, layout, periods)

    sheet.set_print_area(0, 0, layout.note_row + 1, max(total_column, LAYOUT_END_COLUMN))
    sheet.fit_to_pages(1, 0)
    workbook.close()
    return finalize_excel_ooxml(output.getvalue(), logo_bytes=logo_bytes)
