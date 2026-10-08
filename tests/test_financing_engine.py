import unittest
import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "q_flow" / "financing.py"
_SPEC = importlib.util.spec_from_file_location("financing", _MODULE_PATH)
_FINANCING = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FINANCING)
calculate_financing = _FINANCING.calculate_financing


class FinancingEngineTests(unittest.TestCase):
    def test_overdraft_draws_only_enough_to_cover_shortfall_and_respects_limit(self):
        result = calculate_financing(
            inflows=[0, 0],
            outflows=[80, 50],
            ppc_base=[0, 0],
            ppc_issued=[0, 0],
            facilities=[{
                "name": "OD",
                "type": "Overdraft",
                "draw_method": "automatic_shortfall",
                "repayment_method": "cashflow_sweep",
                "limit": 100,
                "interest_rate": 0,
                "fees": 0,
                "revolving": True,
            }, {
                "name": "Contractor contribution",
                "type": "Owner's Injection",
                "draw_method": "automatic_shortfall",
                "repayment_method": "cashflow_sweep",
                "limit": None,
                "interest_rate": 0,
                "fees": 0,
                "revolving": False,
            }],
        )

        self.assertEqual(result["facilities"][0]["draw"], [80.0, 20.0])
        self.assertEqual(result["facilities"][1]["draw"], [0.0, 30.0])
        self.assertEqual(result["unfunded_shortfall"], [0.0, 0.0])
        self.assertEqual(result["funded_cash_balance"], [0.0, 0.0])

    def test_cashflow_sweep_repayment_restores_revolving_capacity(self):
        result = calculate_financing(
            inflows=[0, 150],
            outflows=[100, 0],
            ppc_base=[0, 0],
            ppc_issued=[0, 0],
            facilities=[{
                "name": "OD",
                "type": "Overdraft",
                "draw_method": "automatic_shortfall",
                "repayment_method": "cashflow_sweep",
                "limit": 100,
                "interest_rate": 0,
                "fees": 0,
                "revolving": True,
            }],
        )

        self.assertEqual(result["facilities"][0]["draw"], [100.0, 0.0])
        self.assertEqual(result["facilities"][0]["repayment"], [0.0, 100.0])
        self.assertEqual(result["facilities"][0]["available_limit"], [0.0, 100.0])
        self.assertEqual(result["funded_cash_balance"], [0.0, 50.0])

    def test_scheduled_repayment_is_applied_even_when_it_creates_negative_cash(self):
        result = calculate_financing(
            inflows=[0],
            outflows=[10],
            ppc_base=[0],
            ppc_issued=[0],
            facilities=[{
                "name": "Contract loan",
                "type": "Working Capital",
                "draw_method": "scheduled",
                "draw_schedule": {0: 50},
                "repayment_method": "scheduled",
                "repayment_schedule": {0: 60},
                "limit": 100,
                "interest_rate": 0,
                "fees": 0,
                "revolving": False,
            }],
        )

        facility = result["facilities"][0]
        self.assertEqual(facility["draw"], [50.0])
        self.assertEqual(facility["repayment"], [50.0])
        self.assertEqual(result["funded_cash_balance"], [-10.0])

    def test_ppc_discount_draw_and_repayment_use_the_current_ppc_period(self):
        result = calculate_financing(
            inflows=[0, 0, 100],
            outflows=[0, 0, 0],
            ppc_base=[0, 0, 100],
            ppc_issued=[0, 100, 0],
            facilities=[{
                "name": "PPC Discount",
                "type": "PPC Discount",
                "draw_method": "ppc_base",
                "advance_portion": 0.8,
                "repayment_method": "percent_of_ppc",
                "repayment_percent": 0.8,
                "limit": 100,
                "interest_rate": 0,
                "fees": 0,
                "revolving": False,
            }],
        )

        facility = result["facilities"][0]
        self.assertEqual(facility["draw"], [0.0, 80.0, 0.0])
        self.assertEqual(facility["repayment"], [0.0, 0.0, 80.0])
        self.assertEqual(facility["outstanding"], [0.0, 80.0, 0.0])

    def test_sweep_priority_orders_repayment_and_interest_uses_opening_balance(self):
        result = calculate_financing(
            inflows=[0, 120],
            outflows=[200, 0],
            ppc_base=[0, 0],
            ppc_issued=[0, 0],
            facilities=[{
                "name": "Lower priority",
                "type": "Working Capital",
                "draw_method": "scheduled",
                "draw_schedule": {0: 100},
                "repayment_method": "cashflow_sweep",
                "sweep_priority": 2,
                "limit": 100,
                "interest_rate": 0.1,
                "fees": 0,
                "revolving": False,
            }, {
                "name": "First priority",
                "type": "Overdraft",
                "draw_method": "scheduled",
                "draw_schedule": {0: 50},
                "repayment_method": "cashflow_sweep",
                "sweep_priority": 1,
                "limit": 50,
                "interest_rate": 0.2,
                "fees": 0,
                "revolving": False,
            }],
        )

        self.assertEqual(result["facilities"][0]["interest"], [0.0, 10.0])
        self.assertEqual(result["facilities"][1]["interest"], [0.0, 10.0])
        self.assertEqual(result["facilities"][1]["repayment"], [0.0, 50.0])
        self.assertEqual(result["facilities"][0]["repayment"], [0.0, 0.0])

    def test_equal_installments_run_for_the_configured_number_of_periods(self):
        result = calculate_financing(
            inflows=[0],
            outflows=[0],
            ppc_base=[0],
            ppc_issued=[0],
            facilities=[{
                "name": "Contract loan",
                "type": "Working Capital",
                "draw_method": "scheduled",
                "draw_schedule": {0: 90},
                "repayment_method": "equal_installments",
                "installment_start": 1,
                "installment_interval": 1,
                "installment_count": 3,
                "limit": 100,
                "interest_rate": 0,
                "fees": 0,
                "revolving": False,
            }],
        )

        self.assertEqual(
            result["facilities"][0]["repayment"], [0.0, 30.0, 30.0, 30.0]
        )

    def test_preset_models_offer_editable_default_methods(self):
        presets = {preset["key"]: preset for preset in _FINANCING.FACILITY_PRESETS}

        self.assertEqual(presets["letter_of_credit"]["draw_method"], "scheduled")
        self.assertEqual(presets["overdraft"]["repayment_method"], "cashflow_sweep")
        self.assertEqual(presets["ppc_discount"]["draw_method"], "ppc_base")

    def test_scheduled_draw_above_non_revolving_limit_reports_undrawn_amount(self):
        result = calculate_financing(
            inflows=[0],
            outflows=[0],
            ppc_base=[0],
            ppc_issued=[0],
            facilities=[{
                "name": "LC",
                "type": "Letter of Credit",
                "draw_method": "scheduled",
                "draw_schedule": {0: 120},
                "repayment_method": "scheduled",
                "repayment_schedule": {},
                "limit": 100,
                "interest_rate": 0,
                "fees": 0,
                "revolving": False,
            }],
        )

        facility = result["facilities"][0]
        self.assertEqual(facility["draw"], [100.0])
        self.assertEqual(facility["unfunded_draw"], [20.0])
        self.assertEqual(facility["available_limit"], [0.0])

    def test_facility_fee_and_interest_are_separate_cash_outflows(self):
        result = calculate_financing(
            inflows=[0, 0],
            outflows=[0, 0],
            ppc_base=[0, 0],
            ppc_issued=[0, 0],
            facilities=[{
                "name": "Equipment loan",
                "type": "Equipment Loan",
                "draw_method": "scheduled",
                "draw_schedule": {0: 100},
                "repayment_method": "scheduled",
                "repayment_schedule": {},
                "limit": 100,
                "fees": 5,
                "interest_rate": 0.1,
                "revolving": False,
            }],
        )

        self.assertEqual(result["facility_fees"], [5.0, 0.0])
        self.assertEqual(result["facility_interest"], [0.0, 10.0])
        self.assertEqual(result["funded_cash_balance"], [95.0, 85.0])


class FinancingValidationTests(unittest.TestCase):
    def test_rejects_equal_installments_without_a_positive_count(self):
        validate = _FINANCING.validate_financing_facilities

        errors = validate([{
            "name": "Equipment Loan",
            "draw_method": "scheduled",
            "repayment_method": "equal_installments",
            "installment_start": 0,
            "installment_interval": 1,
            "installment_count": 0,
        }])

        self.assertIn("Facility 1 installment count is invalid", errors)

    def test_requires_terms_used_by_the_selected_methods(self):
        errors = _FINANCING.validate_financing_facilities([{
            "name": "PPC Discount",
            "type": "PPC Discount",
            "draw_method": "ppc_base",
            "repayment_method": "percent_of_ppc",
            "limit": 100,
        }])

        self.assertIn("Facility 1 advance portion is required for PPC-base draws", errors)
        self.assertIn("Facility 1 repayment percentage is required for PPC repayments", errors)

    def test_invalid_period_types_are_reported_without_comparison_errors(self):
        errors = _FINANCING.validate_financing_facilities([{
            "name": "OD",
            "type": "Overdraft",
            "draw_method": "automatic_shortfall",
            "repayment_method": "cashflow_sweep",
            "start": "later",
            "end": 2,
            "limit": 100,
        }])

        self.assertIn("Facility 1 start must be a non-negative period", errors)


if __name__ == "__main__":
    unittest.main()
