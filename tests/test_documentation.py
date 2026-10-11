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
            "outflow remains activity-based",
            "forecast, not a guarantee",
            "do not use `billing deferral`",
        ):
            self.assertIn(required, folded)
        for forbidden in (
            "lightweight by design",
            "does not replace primavera p6",
            "activity-specific selling value and markup allocation",
        ):
            self.assertNotIn(forbidden, folded)

    def test_reference_documents_match_current_model_and_auth_language(self):
        model = (DOCS / "reference" / "cashflow_model.md").read_text(encoding="utf-8")
        portable = (DOCS / "reference" / "cashflow_json_format.md").read_text(encoding="utf-8")
        security = (DOCS / "reference" / "security.md").read_text(encoding="utf-8")

        for text in (model, portable):
            self.assertIn("Work in Excess of Billings (WIEB)", text)
            self.assertNotIn("Work in Excess of Billing (WIEB)", text)

        self.assertIn("use_independent_inflow_curve is True", model)
        self.assertIn("inflow_curve_type is not NULL", model)
        self.assertIn("cashflowpot.cashflow", portable)
        self.assertIn("version", portable)

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
