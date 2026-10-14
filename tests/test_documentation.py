from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "documentation"


class DocumentationTest(TestCase):
    def test_authoritative_documentation_structure_exists(self):
        for relative in (
            "README.md",
            "product.md",
            "technical.md",
            "ui-ux.md",
            "deployment.md",
            "future.md",
            "reference/cashflow_model.md",
            "reference/financing_facilities.md",
            "reference/cashflow_json_format.md",
            "reference/security.md",
        ):
            self.assertTrue((DOCS / relative).is_file(), relative)

    def test_legacy_reference_locations_are_removed(self):
        for relative in (
            "cashflow_model.md",
            "cashflow_json_format.md",
            "security.md",
        ):
            self.assertFalse((DOCS / relative).exists(), relative)

    def test_documentation_index_explains_current_future_and_history_boundaries(self):
        text = (DOCS / "README.md").read_text(encoding="utf-8")
        self.assertIn("current product", text.casefold())
        self.assertIn("docs/superpowers/specs", text)
        self.assertIn("docs/superpowers/plans", text)
        for link in (
            "product.md",
            "technical.md",
            "ui-ux.md",
            "deployment.md",
            "future.md",
            "reference/cashflow_model.md",
            "reference/financing_facilities.md",
            "reference/cashflow_json_format.md",
            "reference/security.md",
        ):
            self.assertIn(link, text)

    def test_product_document_uses_current_positioning_and_rules(self):
        text = (DOCS / "product.md").read_text(encoding="utf-8")
        folded = text.casefold()
        for required in (
            "construction cash-flow",
            "independent contract curve",
            "activity-linked inflow",
            "contract terms",
            "forecasting assumptions",
            "work in excess of billings (wieb)",
            "scheduled cost",
            "financing facilities",
            "project outflow is the sum",
            "cash position",
            "cash after debt settlement",
            "forecast, not a guarantee",
            "do not use `billing deferral`",
        ):
            self.assertIn(required, folded)
        for forbidden in (
            "lightweight by design",
            "activity-specific selling value and markup allocation",
            "overall cash position",
        ):
            self.assertNotIn(forbidden, folded)

    def test_reference_documents_match_current_model_financing_and_auth_language(self):
        model = (DOCS / "reference" / "cashflow_model.md").read_text(encoding="utf-8")
        facilities = (DOCS / "reference" / "financing_facilities.md").read_text(encoding="utf-8")
        portable = (DOCS / "reference" / "cashflow_json_format.md").read_text(encoding="utf-8")
        security = (DOCS / "reference" / "security.md").read_text(encoding="utf-8")

        for text in (model, portable):
            self.assertIn("Work in Excess of Billings (WIEB)", text)
            self.assertNotIn("Work in Excess of Billing (WIEB)", text)

        self.assertIn("use_independent_inflow_curve is True", model)
        self.assertIn("inflow_curve_type is not NULL", model)
        self.assertIn("scheduled_cost", model)
        self.assertIn("funded_netflow", model)
        self.assertIn("cash_after_debt_settlement", model)

        for required in (
            "PPC issued",
            "PPC receipts",
            "Revolving",
            "Non-revolving",
            "CASH POSITION",
            "Cash after debt settlement",
        ):
            self.assertIn(required, facilities)
        self.assertNotIn("OVERALL CASH POSITION", facilities)

        self.assertIn("cashflowpot.cashflow", portable)
        self.assertIn("version", portable)
        self.assertIn("financing_facilities", portable)
        self.assertIn("scheduled_cost", portable)

        for required in (
            "Authorization: Bearer",
            "client-app-id",
            "audience",
            "APP_ID",
            "PUBLIC_KEY",
            "APP_SECRET",
            "unit_permissions",
            "view:cashflow",
            "edit:cashflow",
        ):
            self.assertIn(required, security)

    def test_ui_ux_documents_current_result_and_excel_contract(self):
        text = (DOCS / "ui-ux.md").read_text(encoding="utf-8")
        for required in (
            "Scheduled Cost",
            "user-facing periods are **1-based**",
            "PROJECT CASHFLOW",
            "FACILITIES",
            "CASH POSITION",
            "Cash after debt settlement",
            "one decimal place",
            "authoritative",
            "pastel",
        ):
            self.assertIn(required, text)
        self.assertNotIn("OVERALL CASH POSITION", text)

    def test_future_document_does_not_describe_current_financing_as_future(self):
        text = (DOCS / "future.md").read_text(encoding="utf-8")
        folded = text.casefold()
        self.assertIn("financing facilities are **current product behavior**", folded)
        self.assertIn("full scenario report", folded)
        self.assertIn("ai-assisted project and scenario setup", folded)
        self.assertNotIn("## 5. project financing facilities", folded)
        self.assertNotIn("add a financing layer", folded)

    def test_deployment_document_matches_current_vps_contract(self):
        text = (DOCS / "deployment.md").read_text(encoding="utf-8")
        for required in (
            "cashflowpot.com/",
            "cashflowpot.com/app/",
            "cashflowpot.com/api/",
            "/home/cashflowpot/public_html",
            "/home/cashflowpot/q_flow",
            "python site/build_site.py",
            "python site/build_site.py -l",
            "site/dist/",
            "127.0.0.1:5002",
            "cashflowpot-qflow.service",
            "ProxyPass /api/ http://127.0.0.1:5002/",
            "PostgreSQL",
            "DATABASE_URL",
        ):
            self.assertIn(required, text)
        for forbidden in (
            "/home/iqmieeuk",
            "~/www.cashflowpot.com",
            "PassengerBaseURI",
            "PassengerAppRoot",
            "Namecheap",
        ):
            self.assertNotIn(forbidden, text)

    def test_current_docs_do_not_describe_passenger_as_production_runtime(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        technical = (DOCS / "technical.md").read_text(encoding="utf-8")
        index = (DOCS / "README.md").read_text(encoding="utf-8")
        combined = "\n".join((readme, technical, index))
        self.assertNotIn("mounted by Passenger", combined)
        self.assertNotIn("Passenger provides", combined)
        self.assertNotIn("Passenger API", combined)
        self.assertIn("Gunicorn", combined)
        self.assertIn("Apache", combined)

    def test_search_discovery_architecture_is_documented(self):
        deployment = (DOCS / "deployment.md").read_text(encoding="utf-8")
        technical = (DOCS / "technical.md").read_text(encoding="utf-8")
        combined = deployment + "\n" + technical
        for required in (
            "robots.txt",
            "sitemap.xml",
            "llms.txt",
            "cashflowpot-og.webp",
            "noindex, follow",
            "crawlable",
            "/api/",
            "PublicPage",
            "JSON-LD",
        ):
            self.assertIn(required, combined)
        self.assertIn("not a discovery surface", technical)
