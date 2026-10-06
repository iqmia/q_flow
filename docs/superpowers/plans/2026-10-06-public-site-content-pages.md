# CashflowPot Public Site Content Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the existing CashflowPot public pages to match the current cash-flow model and product positioning, add About/Contact/Privacy/Terms, introduce shared logo/navigation/footer treatment, and keep the site static and testable.

**Architecture:** Keep the existing Jinja-at-build-time static site under `site/`. Extend the page registry in `site/build_site.py`, keep one shared `base.html` shell and `site.css`, add four focused templates, and update the three existing product pages without changing Flask routes or the cash-flow calculation engine.

**Tech Stack:** Python 3.9, Jinja2 via Flask, unittest/flask-testing, HTML5, CSS custom properties, static PNG asset, existing `site/build_site.py` generator.

**Spec:** `docs/superpowers/specs/2026-10-06-public-site-content-pages-design.md`

## Global Constraints

- Public deployment remains `cashflowpot.com/` static site, `cashflowpot.com/app/` Flutter, and `cashflowpot.com/api/` Passenger/Flask.
- Do not change CashflowPot calculations, authenticated Flutter behavior, Flask business routes, or API interfaces.
- CashflowPot must be positioned as a purpose-built construction cash-flow simulation/decision tool, not as a lesser planning application.
- Public copy must distinguish **contract terms** from **forecasting assumptions**.
- Current inflow methods are `Independent contract curve` (default/recommended) and `Activity-linked inflow` (alternative).
- Outflow remains activity-based under both inflow methods.
- Use `Work in Excess of Billings (WIEB)`, `Payment period`, and `Defects Liability Period (DLP)` in user-facing copy.
- Do not expose backend field names or numeric skew terminology to normal users; use `Back-loaded`, `Balanced`, and `Front-loaded`.
- Keep the exact footer sentence: `CashflowPot is part of the Quollnet ecosystem for engineering and construction. Explore CashflowPot on Quollnet.`
- Stable parent-product link: `https://quollnet.com/apps/cashflowpot`.
- Do not link the four legacy Quollnet cash-flow articles in this pass.
- Contact routes through existing Quollnet channels only; do not invent a CashflowPot-specific email/contact identity.
- Privacy and Terms visibly use `Quollnet` with `Quoll Unipessoal LDA` as legal operator.
- Public site follows system light/dark preference; do not add a manual theme switcher.
- Reuse the existing approved theme tokens; do not introduce Quollnet blue.
- Use the existing CashflowPot circular logo source `iqmia/cashflowpot:assets/icon/qflow_logo_circular_256.png`, copied into `q_flow/site/static/img/cashflowpot-logo.png`.
- `site/dist/` remains generated output and must not be committed.

## Review Focus

- **Model wording:** Home/How it works/Methodology must not imply that activity cost curves always drive contract inflow; tests in Tasks 2 and 3 pin both inflow methods.
- **Product positioning:** public copy must not use the old generic `not a replacement for P6/MS Project` framing or imply CashflowPot is a simplified planning product; tests in Tasks 2 and 3 pin the new purpose distinction.
- **Legal claims:** Privacy must avoid unsupported absolutes about logging, transfer, retention periods, or security guarantees; tests in Task 5 pin identity/scope language while implementation review checks claim restraint.
- **Responsive shell:** adding the logo/footer groups must not hide the `Open app` CTA or break the existing small-screen layout; Task 1 adds CSS assertions for the responsive rules and a built-page smoke check.
- **External links:** Contact must use only the approved Quollnet destinations and the public site must not link the four legacy article slugs; Tasks 4 and 6 test both conditions.

---

### Task 1: Shared site shell, logo, page registry, and footer

**Files:**
- Modify: `tests/test_site_build.py`
- Modify: `site/build_site.py`
- Modify: `site/templates/base.html`
- Modify: `site/static/css/site.css`
- Create: `site/static/img/cashflowpot-logo.png` from `iqmia/cashflowpot:assets/icon/qflow_logo_circular_256.png`

**Interfaces:**
- Consumes: existing `build_site(output_dir: Optional[Path] = None) -> Path` and shared Jinja base template.
- Produces: build destinations for `/about/`, `/contact/`, `/privacy/`, `/terms/`; shared branded header/footer; `/assets/img/cashflowpot-logo.png`.

- [ ] **Step 1: Add failing shell/build tests**

Extend `SiteBuildTest` with tests named:

```python
def test_build_generates_all_public_pages(self): ...
def test_shared_shell_contains_logo_primary_nav_and_footer_links(self): ...
def test_build_copies_cashflowpot_logo(self): ...
def test_shared_css_supports_logo_footer_groups_and_small_screens(self): ...
```

Assertions must cover:

```text
about/index.html
contact/index.html
privacy/index.html
terms/index.html
/assets/img/cashflowpot-logo.png
href="/"
href="/how-it-works/"
href="/methodology/"
href="/about/"
href="/app/"
href="/contact/"
href="/privacy/"
href="/terms/"
https://quollnet.com/apps/cashflowpot
CashflowPot is part of the Quollnet ecosystem for engineering and construction. Explore CashflowPot on Quollnet.
```

Also assert the base template references `/assets/img/cashflowpot-logo.png`, and the CSS contains the shared brand/footer selectors plus a small-screen media rule that leaves `.button--primary` visible while normal nav links may collapse.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
python -m unittest tests.test_site_build.SiteBuildTest -v
```

Expected: failures for missing templates/page registry entries/logo/footer structure.

- [ ] **Step 3: Implement the shared shell and page registry**

Update `site/build_site.py` `PAGES` to include:

```python
('about.html', 'about/index.html')
('contact.html', 'contact/index.html')
('privacy.html', 'privacy/index.html')
('terms.html', 'terms/index.html')
```

Copy the circular 256px CashflowPot logo into `site/static/img/cashflowpot-logo.png`.

Update `base.html` so the brand link contains the logo mark plus `CashflowPot`, keeps `A Quollnet product` subordinate, keeps the approved primary navigation, and expands the footer into compact Product and Company/support groups while preserving the exact Quollnet ecosystem sentence.

Update `site.css` only as needed for:

- `.brand__logo` / brand row layout;
- grouped footer navigation;
- stacked footer behavior on narrow screens;
- a readable `.legal-content` content measure reused later;
- maintaining the visible `Open app` CTA on small screens.

Create minimal placeholder templates for the four new pages if required for this task's build test; they may contain only valid inheritance/title/canonical/H1 scaffolding because Tasks 4 and 5 own final content.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
python -m unittest tests.test_site_build.SiteBuildTest -v
```

Expected: all shell/build tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_site_build.py site/build_site.py site/templates/base.html site/templates/about.html site/templates/contact.html site/templates/privacy.html site/templates/terms.html site/static/css/site.css site/static/img/cashflowpot-logo.png
git commit -m "feat: expand CashflowPot public site shell"
```

---

### Task 2: Update Home and How it works for current product positioning

**Files:**
- Modify: `tests/test_site_build.py`
- Modify: `site/templates/index.html`
- Modify: `site/templates/how-it-works.html`

**Interfaces:**
- Consumes: shared shell from Task 1 and the product/model terminology fixed by the spec.
- Produces: current marketing and practical-workflow copy for Home and How it works.

- [ ] **Step 1: Add failing content tests for Home and How it works**

Add tests named:

```python
def test_home_positions_cashflowpot_as_cashflow_decision_tool(self): ...
def test_how_it_works_explains_both_inflow_methods_and_terms(self): ...
```

Build into a temporary directory and assert Home/How it works contain, at minimum:

```text
Independent contract curve
Activity-linked inflow
contract terms
assumptions
balanced S-curve
working capital
```

Home must also include tender/bid, financing/lender, and mid-project/reforecast use cases. How it works must include the six-step flow from the spec and explain that detailed programme data can inform execution timing without being required for every cash decision.

Assert neither page contains:

```text
CashflowPot does not replace Primavera P6
Lightweight by design
Billing Deferral
```

- [ ] **Step 2: Run the two new tests and verify RED**

Run:

```bash
python -m unittest \
  tests.test_site_build.SiteBuildTest.test_home_positions_cashflowpot_as_cashflow_decision_tool \
  tests.test_site_build.SiteBuildTest.test_how_it_works_explains_both_inflow_methods_and_terms -v
```

Expected: failures on old positioning and missing two-mode inflow copy.

- [ ] **Step 3: Rewrite Home around decision speed and commercial cash flow**

In `site/templates/index.html`:

- replace the `heavyweight setup`/`lighter product` framing with the spec's purpose distinction;
- explain that execution timing/cost and contract terms/assumptions are converted into cash received/paid and funding requirements;
- describe independent contract curve as the default and activity-linked as the alternative without technical field names;
- add or strengthen tender/bid-no-bid, portfolio capacity, financing/lender review, and mid-project reforecast examples;
- keep Excel output, peak exposure, scenario comparison, and AI-assisted setup messaging;
- replace generic `assumptions` wording where the content actually refers to contract terms.

- [ ] **Step 4: Rewrite How it works as the approved six-step workflow**

In `site/templates/how-it-works.html`, use the spec's sequence:

1. Define the project.
2. Set the inflow forecast method.
3. Build the activity forecast.
4. Apply contract terms and assumptions.
5. Review the forecast.
6. Revise scenarios and export.

Use `Payment period`, `WIEB`, and `DLP`; do not describe activity cost as an activity selling value.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the same two test methods. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_site_build.py site/templates/index.html site/templates/how-it-works.html
git commit -m "feat: update CashflowPot product pages"
```

---

### Task 3: Rewrite Methodology around execution, terms, assumptions, and the two inflow methods

**Files:**
- Modify: `tests/test_site_build.py`
- Modify: `site/templates/methodology.html`

**Interfaces:**
- Consumes: current canonical calculation behavior documented in `documentation/cashflow_model.md` plus the approved public wording in the design spec.
- Produces: canonical public model explanation at `/methodology/`.

- [ ] **Step 1: Add failing methodology contract tests**

Add tests named:

```python
def test_methodology_explains_execution_terms_and_cash_position(self): ...
def test_methodology_explains_independent_and_activity_linked_inflow(self): ...
def test_methodology_removes_obsolete_sov_roadmap_claim(self): ...
```

Assertions must pin:

```text
A forecast designed to be revised
Execution model
contract terms
forecasting assumptions
Cash position
Independent contract curve
Activity-linked inflow
Back-loaded
Balanced
Front-loaded
Work in Excess of Billings (WIEB)
Payment period
Defects Liability Period (DLP)
```

Also assert absence of the old planned feature heading/copy:

```text
Activity-specific selling value and markup allocation
planned extension
```

and absence of a generic `CashflowPot does not replace Primavera P6` disclaimer.

- [ ] **Step 2: Run methodology tests and verify RED**

Run the three new test methods with `python -m unittest ... -v`.

Expected: current page fails because it describes only activity-linked contract inflow and still contains the selling-value roadmap section.

- [ ] **Step 3: Rewrite the methodology page**

Reorganize `methodology.html` around three concepts:

1. execution model;
2. contract terms and forecasting assumptions;
3. cash position.

For main-contract inflow, provide two explicit subsections:

- `Independent contract curve — default`;
- `Activity-linked inflow — alternative`.

Preserve accurate WIEB, outflow, subcontract, net cash, financing, period convention, invariants, and advanced curve material where still valid. Remove obsolete selling-value/SOV roadmap language. Replace the old planning-software disclaimer with the purpose distinction from the spec: planning tools can provide time-phased work/cost; CashflowPot models the commercial cash consequences and can use mathematical execution profiles when detailed loading is unnecessary or stale.

Do not change formulas to invent new behavior; public formulas must remain consistent with `documentation/cashflow_model.md`.

- [ ] **Step 4: Run methodology tests and verify GREEN**

Run the same three test methods. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_site_build.py site/templates/methodology.html
git commit -m "feat: update CashflowPot methodology"
```

---

### Task 4: Implement About and Contact pages

**Files:**
- Modify: `tests/test_site_build.py`
- Modify: `site/templates/about.html`
- Modify: `site/templates/contact.html`
- Modify: `site/static/css/site.css` only if these pages need a reusable contact/brand layout class

**Interfaces:**
- Consumes: shared shell/logo from Task 1.
- Produces: `/about/` and `/contact/` with canonical metadata and approved Quollnet support routes.

- [ ] **Step 1: Add failing About/Contact tests**

Add tests named:

```python
def test_about_page_has_brand_positioning_and_canonical_url(self): ...
def test_contact_page_uses_only_approved_quollnet_channels(self): ...
```

About assertions:

```text
https://cashflowpot.com/about/
A forecast designed to be revised
https://quollnet.com/apps/cashflowpot
Tender
financing
lender
mid-project
```

Contact assertions must include all approved destinations exactly:

```text
https://www.quollnet.com
https://www.facebook.com/people/Quollnet/100086014988886/
https://www.instagram.com/quollnet/
https://twitter.com/quollnet
https://www.linkedin.com/in/quollnet/
https://www.youtube.com/@quollnet
https://wa.me/351911747738
Quoll Unipessoal LDA
```

Assert Contact does not contain `mailto:` unless a real Quollnet email is later explicitly supplied.

- [ ] **Step 2: Run tests and verify RED**

Run the two new test methods. Expected: placeholder templates fail.

- [ ] **Step 3: Implement About**

Write a concise product page using the logo prominently and covering:

- focused construction cash-flow simulation/forecasting;
- financial decisions faster than creating/rebuilding detailed loading;
- tender, financing, lender review, bid/no-bid/portfolio capacity, and mid-project reforecasting;
- different purpose from detailed planning systems;
- Quollnet parent-product link.

Do not feature the legal company name here.

- [ ] **Step 4: Implement Contact**

Explain that CashflowPot support/contact routes through Quollnet. Render the approved Quollnet channels as simple labeled links/cards without adding icon-font dependencies. Include a small `Quollnet / Quoll Unipessoal LDA` company block.

- [ ] **Step 5: Run tests and verify GREEN**

Run the two new test methods. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_site_build.py site/templates/about.html site/templates/contact.html site/static/css/site.css
git commit -m "feat: add CashflowPot about and contact pages"
```

---

### Task 5: Implement Privacy and Terms pages

**Files:**
- Modify: `tests/test_site_build.py`
- Modify: `site/templates/privacy.html`
- Modify: `site/templates/terms.html`

**Interfaces:**
- Consumes: `.legal-content` shared layout from Task 1.
- Produces: readable `/privacy/` and `/terms/` pages using Quollnet as brand and Quoll Unipessoal LDA as legal operator.

- [ ] **Step 1: Add failing legal-page tests**

Add tests named:

```python
def test_privacy_page_identifies_operator_and_expected_sections(self): ...
def test_terms_page_identifies_operator_and_forecast_disclaimer(self): ...
```

Both pages must contain:

```text
Quollnet
Quoll Unipessoal LDA
CashflowPot is a Quollnet product operated by Quoll Unipessoal LDA.
Last updated
```

Privacy must include headings/content covering scope, information provided, authentication/account data, technical/usage data, use of information, service providers, retention, security, rights/requests, contact, and changes.

Terms must include acceptance, account responsibility, acceptable use, project data/contract terms/forecasting assumptions, planning estimate/simulation disclaimer, professional/commercial/financing responsibility, service availability, ownership, limitation/disclaimer, Privacy link, contact, and changes.

Assert canonical URLs:

```text
https://cashflowpot.com/privacy/
https://cashflowpot.com/terms/
```

- [ ] **Step 2: Run tests and verify RED**

Run the two new test methods. Expected: placeholder legal pages fail.

- [ ] **Step 3: Write Privacy in restrained plain language**

Implement the approved sections without unsupported absolutes. Do not promise fixed retention periods, zero logging, zero transfer, absolute security, or specific subprocessors unless verified by current system behavior.

Use `Last updated: 6 October 2026`.

- [ ] **Step 4: Write Terms around decision-support use**

State clearly that forecasts are estimates/simulations based on user-entered project data, contract terms, and assumptions, and are not guarantees of future cash flows. Keep liability/disclaimer wording reasonable and avoid pretending this is legal advice or a banking decision.

Use `Last updated: 6 October 2026`.

- [ ] **Step 5: Run tests and verify GREEN**

Run the two new test methods. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_site_build.py site/templates/privacy.html site/templates/terms.html
git commit -m "feat: add CashflowPot privacy and terms pages"
```

---

### Task 6: Cross-page guardrails, build verification, and full regression suite

**Files:**
- Modify: `tests/test_site_build.py`
- Modify only if failures require correction: `site/templates/*.html`, `site/static/css/site.css`, `site/build_site.py`

**Interfaces:**
- Consumes: all site work from Tasks 1–5.
- Produces: final regression guardrails and a verified static build ready for deployment review.

- [ ] **Step 1: Add final cross-page guardrail test**

Add:

```python
def test_public_site_has_no_legacy_article_links_or_obsolete_product_copy(self): ...
```

Build the site and concatenate all generated `.html` files. Assert absence of:

```text
/article/construction_cashflow_prediction
/article/How_to_Create_a_Project_Cash_Flow_for_Contractors
/article/Quollnet_cashflow
/article/master_construction_project_cashflow_with_cashflowpot
Billing Deferral
Activity-specific selling value and markup allocation
CashflowPot does not replace Primavera P6
```

Assert presence somewhere in the generated product pages of:

```text
Independent contract curve
Activity-linked inflow
contract terms
forecasting assumptions
```

- [ ] **Step 2: Run the guardrail test and verify its result**

Run the single new test. If it fails, correct only the offending public-site copy/link and rerun until PASS.

- [ ] **Step 3: Run the complete site-build test module**

```bash
python -m unittest tests.test_site_build -v
```

Expected: PASS with no site-build failures.

- [ ] **Step 4: Build the static site once outside the test temp directory**

```bash
python site/build_site.py
```

Expected output includes:

```text
site/dist/index.html
site/dist/how-it-works/index.html
site/dist/methodology/index.html
site/dist/about/index.html
site/dist/contact/index.html
site/dist/privacy/index.html
site/dist/terms/index.html
site/dist/404.html
site/dist/assets/css/site.css
site/dist/assets/img/cashflowpot-logo.png
```

Do not commit `site/dist/`.

- [ ] **Step 5: Run the full backend test suite**

Run the repository's established full suite command, normally:

```bash
pytest
```

If this repository uses unittest discovery in the local environment instead, run the existing project-wide command the user already uses. Report every failure by name; do not call the branch ready unless the full suite is green or the user explicitly accepts a known unrelated failure.

- [ ] **Step 6: Review generated HTML for legal/product copy and responsive shell**

Open the generated Home, How it works, Methodology, About, Contact, Privacy, and Terms pages in a browser at desktop and narrow widths. Verify:

- logo is legible in light/dark system theme;
- `Open app` remains visible on narrow screens;
- footer groups stack cleanly;
- legal page line length is readable;
- no accidental raw template syntax appears;
- external Quollnet links are correct;
- no legacy article links appear.

- [ ] **Step 7: Commit final guardrails/corrections**

```bash
git add tests/test_site_build.py site/templates site/static/css/site.css site/build_site.py
git commit -m "test: verify CashflowPot public site content"
```

Only include files actually changed in this final commit.
