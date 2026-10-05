# CashflowPot Site and API Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare `iqmia/q_flow` to own the CashflowPot Flask API and the source/build foundation for the static public CashflowPot website without creating the actual public content pages yet.

**Architecture:** Passenger mounts the existing Flask app externally at `https://cashflowpot.com/api`, while internal Flask routes stay rooted at `/`. A new `site/` source tree uses Jinja only at build time to generate static deployable files; ordinary public pages are served directly by LiteSpeed and remain independent of Flask availability.

**Tech Stack:** Python 3.9, Flask 3.0.3, Jinja2 via Flask, unittest/flask-testing, HTML5, CSS custom properties and `prefers-color-scheme`.

**Spec:** `docs/superpowers/specs/2026-10-06-cashflowpot-site-api-foundation-design.md`

## Global Constraints

- Public deployment remains `cashflowpot.com/` static site, `cashflowpot.com/app/` Flutter, and `cashflowpot.com/api/` Passenger/Flask.
- Keep the repository and Python package named `q_flow`; do not rename imports or business API routes.
- Public-site theme follows the operating-system/browser theme automatically; no manual public-site theme switcher.
- Use the approved CashflowPot theme tokens exactly: `#E89A5B`, `#F7F4EF`, `#FFFDFC`, `#30322F`, `#E5DED4`, `#181A18`, `#20221F`, `#272A26`, `#454943`, `#79A58D`, `#C9796F`, `#7F9FB2`, balance `#8D7047` light and `#CDB58A` dark.
- CashflowPot is the dominant product brand; Quollnet attribution is restrained as `A Quollnet product` plus fuller footer attribution without introducing a competing color system.
- `site/dist/` is generated output and must not be committed.
- Do not build Home, How It Works, Methodology, About, Contact, Privacy, or Terms in this foundation task.

## Review Focus

- Passenger mount prefix: Flask must define `/health`, not `/api/health`, so external mounting produces exactly `/api/health` rather than `/api/api/health`.
- Duplicate legacy welcome routes: internal `/api` must disappear after this change so the external mount does not expose `/api/api`.
- Re-running the static builder: an existing output directory must be cleaned so stale files cannot survive into a deployment.
- System dark mode: the shared CSS must contain a `prefers-color-scheme: dark` override using the exact approved dark tokens.
- Repository cleanliness: generated `site/dist/` content must be ignored while source templates/CSS remain tracked.

---

### Task 1: CashflowPot API identity and health endpoint

**Files:**
- Create: `q_flow/routes/system.py`
- Modify: `q_flow/__init__.py`
- Modify: `q_flow/routes/users.py`
- Modify: `q_flow/routes/projects.py`
- Create: `tests/test_system_routes.py`

**Interfaces:**
- Consumes: existing `create_app(TestConfig)` test application and Flask blueprint registration pattern.
- Produces: blueprint `system` with `GET /health` returning JSON `{\"status\": \"ok\", \"service\": \"CashflowPot API\"}` and HTTP 200.

- [ ] **Step 1: Write the failing API identity tests**

Create `tests/test_system_routes.py` using `tests.base.Base` with assertions that:

```python
response = self.client.get('/health')
self.assertEqual(response.status_code, 200)
self.assertEqual(response.json, {
    'status': 'ok',
    'service': 'CashflowPot API',
})

legacy = self.client.get('/api')
self.assertEqual(legacy.status_code, 404)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
python -m unittest tests.test_system_routes -v
```

Expected: `/health` is 404 and/or `/api` is still 200.

- [ ] **Step 3: Add the system blueprint**

Create `q_flow/routes/system.py` defining:

```python
system = Blueprint('system', __name__)
```

and a `health()` view on `GET /health` returning the exact JSON and status from the test.

- [ ] **Step 4: Register `system` and remove duplicate legacy `/api` views**

Modify `q_flow/__init__.py` to import/register `system`. Remove only the obsolete `/api` welcome functions from `q_flow/routes/users.py` and `q_flow/routes/projects.py`; do not rename or otherwise alter existing business routes.

- [ ] **Step 5: Run the focused test and verify it passes**

Run:

```bash
python -m unittest tests.test_system_routes -v
```

Expected: PASS.

- [ ] **Step 6: Run the complete backend test suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit the API foundation**

```bash
git add q_flow/routes/system.py q_flow/__init__.py q_flow/routes/users.py q_flow/routes/projects.py tests/test_system_routes.py
git commit -m "feat: add CashflowPot API health endpoint"
```

### Task 2: Static-site build foundation and shared UI rules

**Files:**
- Create: `site/build_site.py`
- Create: `site/templates/base.html`
- Create: `site/static/css/site.css`
- Create: `tests/test_site_build.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Jinja2 installed through Flask and the approved design tokens from the spec.
- Produces: CLI `python site/build_site.py [--output PATH]`; function `build_site(output_dir: pathlib.Path | None = None) -> pathlib.Path`; generated `assets/css/site.css`; reusable Jinja `base.html`; clean output directory.

- [ ] **Step 1: Write failing build-foundation tests**

Create `tests/test_site_build.py` with isolated temporary-directory tests that load `site/build_site.py` by file path and assert:

```python
output = module.build_site(temp_output)
self.assertEqual(output, temp_output)
self.assertTrue((output / 'assets/css/site.css').is_file())
```

Create a stale file before a second build and assert it no longer exists afterward. Read the generated CSS and assert it contains all approved core tokens plus:

```css
@media (prefers-color-scheme: dark)
```

Read `site/templates/base.html` and assert it contains Jinja blocks for `title`, `description`, `canonical_url`, `content`, a link to `/assets/css/site.css`, `A Quollnet product`, and a footer Quollnet attribution.

Also assert `.gitignore` contains `/site/dist/`.

- [ ] **Step 2: Run the site-foundation tests and verify they fail**

Run:

```bash
python -m unittest tests.test_site_build -v
```

Expected: FAIL because the `site/` foundation does not yet exist.

- [ ] **Step 3: Implement `site/build_site.py`**

Implement:

```python
def build_site(output_dir: Path | None = None) -> Path:
    ...

def main() -> int:
    ...
```

The builder must resolve paths relative to the script, delete an existing output directory before rebuilding, recreate it, copy `site/static/` to `<output>/assets/`, initialize a Jinja environment rooted at `site/templates/`, and keep the page registry empty for this foundation task. `--output PATH` overrides the default `site/dist/` for testing/deployment tooling.

- [ ] **Step 4: Implement the reusable `base.html` shell**

Create semantic HTML5 with metadata blocks, canonical URL block, responsive viewport, stylesheet link, accessible header/main/footer landmarks, CashflowPot brand, restrained `A Quollnet product` attribution, an `Open app` link to `/app/`, and a `{% block content %}`. Do not add page-specific marketing copy.

- [ ] **Step 5: Implement the shared CashflowPot CSS tokens and components**

Define CSS custom properties for every approved light token at `:root`, override the dark tokens under `@media (prefers-color-scheme: dark)`, use system font stacks, 12–14 px radii, restrained borders/shadows, visible keyboard focus, approximately 48 px primary controls, responsive content width, and shared header/footer/button/card primitives. Do not add Quollnet blue as a second palette.

- [ ] **Step 6: Ignore generated site output**

Append exactly:

```text
/site/dist/
```

to `.gitignore`.

- [ ] **Step 7: Run the site-foundation tests and verify they pass**

Run:

```bash
python -m unittest tests.test_site_build -v
```

Expected: PASS.

- [ ] **Step 8: Exercise the default build command**

Run:

```bash
python site/build_site.py
```

Expected: exit code 0; `site/dist/assets/css/site.css` exists; no content pages are generated yet.

- [ ] **Step 9: Run the complete repository test suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 10: Commit the site foundation**

```bash
git add .gitignore site/build_site.py site/templates/base.html site/static/css/site.css tests/test_site_build.py
git commit -m "feat: add CashflowPot static site foundation"
```

### Task 3: Repository-facing documentation and final verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: completed API health endpoint and static build foundation.
- Produces: concise developer/deployment documentation describing the repo's two responsibilities and commands without changing runtime behavior.

- [ ] **Step 1: Update README architecture and commands**

Add concise sections documenting:

```text
cashflowpot.com/      static site generated from site/
cashflowpot.com/app/  Flutter app from iqmia/cashflowpot
cashflowpot.com/api/  this Flask app via Passenger
```

Document `python site/build_site.py` and `GET /api/health` as the deployed health check. State that the internal package remains `q_flow` and that generated `site/dist/` is not committed.

- [ ] **Step 2: Run final targeted verification**

Run:

```bash
python -m unittest tests.test_system_routes tests.test_site_build -v
```

Expected: PASS.

- [ ] **Step 3: Run final full verification**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 4: Confirm generated output is ignored**

Run:

```bash
git status --short --ignored site/dist
```

Expected: `site/dist/` is shown as ignored and contains no tracked files.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md
git commit -m "docs: document CashflowPot site and API layout"
```

## Final Branch Review

After all tasks, review the branch diff against the approved spec and verify:

- no public content pages were added prematurely;
- no existing business API route names changed;
- no Python package/repository rename occurred;
- `/health` is the only new public API identity endpoint and legacy internal `/api` welcome routes are gone;
- the static site foundation carries the exact Flutter-derived theme tokens and system dark-mode behavior;
- Quollnet appears only as restrained parent-product attribution;
- generated output is excluded from version control.
