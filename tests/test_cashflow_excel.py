from io import BytesIO
from zipfile import ZipFile

from q_flow.reports.cashflow_excel import (
    build_cashflow_excel,
    layout_for,
    period_count_for,
)


def _snapshot(facilities=1, period_count=4):
    inflow = [30.0, 160.0, 110.0, 0.0] + [0.0] * max(0, period_count - 4)
    outflow = [40.0, 140.0, 120.0, 0.0] + [0.0] * max(0, period_count - 4)
    workflow = [33.33, 133.33, 133.33, 0.0] + [0.0] * max(0, period_count - 4)
    rows = []
    for index in range(facilities):
        draw = [50.0 if index == 0 else 10.0] + [0.0] * (period_count - 1)
        repayment = [0.0, 40.0 if index == 0 else 0.0] + [0.0] * max(0, period_count - 2)
        interest = [0.0, 5.0 if index == 0 else 0.0, 3.0 if index == 0 else 0.0] + [0.0] * max(0, period_count - 3)
        fees = [0.0, 15.0 if index == 0 else 0.0] + [0.0] * max(0, period_count - 2)
        outstanding = []
        running = 0.0
        for period in range(period_count):
            running += draw[period] - repayment[period]
            outstanding.append(running)
        rows.append({
            "id": f"facility-{index + 1}",
            "name": "LC MEP" if index == 0 else f"Facility {index + 1}",
            "type": "Working Capital",
            "draw": draw,
            "repayment": repayment,
            "interest": interest,
            "fees": fees,
            "outstanding": outstanding,
        })

    return {
        "id": "cf-1",
        "unit_id": "unit-1",
        "name": "Base Scenario",
        "description": "Tender cash-flow forecast",
        "contract_value": 300.0,
        "advance": 0.0,
        "retention": 0.0,
        "release_retention_eop": 0.5,
        "dlp": 0,
        "duration_for_payment": 1,
        "interest_rate": 0.005,
        "wieb": 0.2,
        "workflow": workflow,
        "inflow": inflow,
        "outflow": outflow,
        "netflow": [a - b for a, b in zip(inflow, outflow)],
        "outflow_with_interest": [-10.0, 20.0, -10.0, 0.0] + [0.0] * max(0, period_count - 4),
        "funded_netflow": [40.0, -40.0, -13.0, 0.0] + [0.0] * max(0, period_count - 4),
        "facility_rows": rows,
        "duration": 3,
        "activities": [
            {
                "id": "a-1",
                "name": "Excavation",
                "activity_mode": "work",
                "activity_type": "General",
                "cost": 100.0,
                "duration": 2,
                "start": 0,
                "cash_flow_json": {
                    "marginal_work": [33.33, 33.33, 33.33, 0.0] + [0.0] * max(0, period_count - 4),
                    "marginal_out_flow": [40.0, 60.0, 0.0, 0.0] + [0.0] * max(0, period_count - 4),
                },
            },
            {
                "id": "a-2",
                "name": "MEP material",
                "activity_mode": "scheduled_cost",
                "activity_type": "MEP",
                "cost": 200.0,
                "duration": 2,
                "start": 1,
                "cash_flow_json": {
                    "marginal_work": [0.0] * period_count,
                    "marginal_out_flow": [0.0, 80.0, 120.0, 0.0] + [0.0] * max(0, period_count - 4),
                },
            },
        ],
        "summary": {
            "direct_cost": 300.0,
            "financing_cost": 23.0,
            "total_cost": 323.0,
            "minimum_pre_financing_balance": -50.0,
            "minimum_pre_financing_period": 0,
            "peak_pre_financing_need": 50.0,
            "peak_facility_outstanding": 50.0,
            "final_facility_outstanding": 10.0,
            "final_cash_balance": -13.0,
            "cash_after_debt_settlement": -23.0,
            "work_duration": 3,
            "financial_horizon": period_count,
        },
    }


def _xlsx_text(data, path):
    with ZipFile(BytesIO(data)) as archive:
        return archive.read(path).decode("utf-8")


def test_layout_matches_approved_v3_report_geometry():
    snapshot = _snapshot()
    layout = layout_for(snapshot)

    assert period_count_for(snapshot) == 4
    assert layout.project_header_row == 43  # Excel row 44
    assert layout.project_inflow_row == 44
    assert layout.project_cost_row == 45
    assert layout.facilities_header_row == 47
    assert layout.facilities[0].draw_row == 48
    assert layout.facilities[0].outstanding_row == 51
    assert layout.cash_position_header_row == 53
    assert layout.total_inflow_row == 54
    assert layout.total_outflow_row == 55
    assert layout.net_row == 56
    assert layout.balance_row == 57


def test_excel_contains_approved_sections_formulas_and_print_setup():
    data = build_cashflow_excel(project_name="Harbour Tower", snapshot=_snapshot())
    assert data[:2] == b"PK"

    sheet = _xlsx_text(data, "xl/worksheets/sheet1.xml")
    workbook = _xlsx_text(data, "xl/workbook.xml")
    strings = _xlsx_text(data, "xl/sharedStrings.xml")
    chart1 = _xlsx_text(data, "xl/charts/chart1.xml")
    chart2 = _xlsx_text(data, "xl/charts/chart2.xml")
    drawing = _xlsx_text(data, "xl/drawings/drawing1.xml")

    for text in (
        "CashFlowPot",
        "Harbour Tower",
        "Base Scenario",
        "Contract &amp; Financing Assumptions",
        "Key Metrics",
        "Charts",
        "Cashflow Schedule",
        "PROJECT CASHFLOW",
        "FACILITIES",
        "CASH POSITION",
        "LC MEP",
        "Interest &amp; fees",
        "Cash after debt settlement",
    ):
        assert text in strings

    assert 'showGridLines="0"' in sheet
    assert 'orientation="landscape"' in sheet
    assert 'paperSize="9"' in sheet
    assert 'left="0.19685"' in sheet
    assert 'right="0.19685"' in sheet
    assert 'top="0.19685"' in sheet
    assert 'bottom="0.19685"' in sheet
    assert 'header="0.15"' in sheet
    assert 'footer="0.15"' in sheet
    assert 'calcMode="auto"' in workbook

    # Cash-position formulas match the approved V3 fixed-column/timeline layout.
    assert "H45+H49" in sheet
    assert "H46+H50+H51" in sheet
    assert "H55-H56" in sheet
    assert "H57" in sheet
    assert "H58+I57" in sheet

    assert "Total inflow" in chart1
    assert "Total outflow" in chart1
    assert "5F8F73" in chart1
    assert "C7775E" in chart1
    assert "4F6D86" in chart2
    assert 'cx="4680000"' in drawing
    assert 'cy="2880000"' in drawing


def test_excel_extends_horizon_for_late_facility_and_cycles_facility_fills():
    snapshot = _snapshot(facilities=5, period_count=7)
    data = build_cashflow_excel(project_name="Harbour Tower", snapshot=snapshot)
    sheet = _xlsx_text(data, "xl/worksheets/sheet1.xml")
    styles = _xlsx_text(data, "xl/styles.xml")

    assert period_count_for(snapshot) == 7
    # Group 2 and period 7 must exist beyond the four-period base group.
    strings = _xlsx_text(data, "xl/sharedStrings.xml")
    assert "Group 2" in strings
    # Facility-name rotation and all four approved pastel facility fills.
    assert 'textRotation="90"' in styles
    for color in ("FFEBDD", "EAF5EE", "EAF1FA", "F3ECF8"):
        assert color in styles
    # Fifth facility exists and reuses the first palette entry while horizon is not truncated.
    assert "Facility 5" in strings
    assert "7" in sheet
