# CashflowPot Public SEO and AI Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `cashflowpot.com` the authoritative indexable CashflowPot surface with consistent metadata, structured data, crawl/discovery files, and the approved homepage hero while preserving `/app/` and `/api/` deployment boundaries.

**Architecture:** Evolve `site/build_site.py` into the source of truth for public-page identity and discovery output. Render page metadata and JSON-LD from one `PublicPage` registry into the shared Jinja shell, generate `robots.txt`, `sitemap.xml`, and `llms.txt` at the build root, and keep publishing limited to site-owned paths. The Flutter `/app/` shell is handled in the companion plan `2026-10-07-flutter-app-web-metadata.md`.

**Tech Stack:** Python 3.9, Jinja2, static HTML/CSS, `unittest`/pytest-compatible tests.

**Spec:** `docs/superpowers/specs/2026-10-07-seo-ai-discovery-design.md`

## Global Constraints

- Work directly on `iqmia/q_flow` branch `master`.
- The canonical public origin is `https://cashflowpot.com`.
- Indexable paths are `/`, `/how-it-works/`, `/methodology/`, `/about/`, `/contact/`, `/privacy/`, `/terms/`.
- `404.html`, `/app/`, and `/api/` must not appear in the sitemap.
- `/api/` is disallowed in `robots.txt`; `/app/` must remain crawlable so its `noindex` directive can be read.
- Explicitly allow `OAI-SearchBot` while preserving the `/api/` exclusion.
- Shared social image: `https://cashflowpot.com/assets/images/cashflowpot-og.webp`.
- Homepage hero: `/assets/images/home-hero.webp`.
- Do not add future functionality as current structured-data features.
- Do not add pricing/Offer structured data in this pass.
- Preserve one physical icon set under `/app/icons/...` and the existing public manifest at `/assets/manifest.json`.
- `site/build_site.py` must never delete the full production web root; `/app/`, `/api/`, and unrelated entries remain untouched.
- Keep implementation syntax compatible with production Python 3.9; use `Optional[...]` rather than PEP 604 `X | None` annotations.

## Review Focus

- **404 indexing:** a non-indexable page must render `noindex` and must not accidentally receive canonical/social/JSON-LD signals intended for normal public pages. Task 1 pins this.
- **Canonical path normalization:** every indexable page must keep its approved trailing-slash canonical URL and the same URL in OG/JSON-LD/sitemap. Tasks 1–3 pin this.
- **Discovery leakage:** `/app/`, `/api/`, assets, and `404.html` must never enter `sitemap.xml`, while `/app/` must not be blocked by robots. Task 3 pins this.
- **JSON serialization:** titles/descriptions containing punctuation/apostrophes must remain valid JSON-LD rather than hand-built JSON strings. Task 2 pins this with `json.loads`.
- **Deployment safety:** adding root discovery files must not cause the publisher to replace `/app/`, `/api/`, or unrelated files. Task 3 pins this in the deployment test.

---

### Task 1: Centralize Public Page Metadata and Shared Social Head

**Files:**
- Modify: `site/build_site.py`
- Modify: `site/templates/base.html`
- Modify metadata headers in: `site/templates/index.html`, `how-it-works.html`, `methodology.html`, `about.html`, `contact.html`, `privacy.html`, `terms.html`, `404.html`
- Modify: `tests/test_site_build.py`
- Modify: `tests/test_public_manifest.py`

**Interfaces:**
- Produces dataclass `PublicPage(template_name: str, destination: str, canonical_path: str, title: str, description: str, schema_type: str = "WebPage", indexable: bool = True)`.
- Produces `PublicPage.canonical_url -> str`, formed from `SITE_ORIGIN = "https://cashflowpot.com"` plus `canonical_path`.
- Produces `PAGES: tuple[PublicPage, ...]` as the authoritative public-page registry.
- `build_site()` renders each template with `page=<PublicPage>` and later `structured_data=<Optional[dict[str, object]]>` from Task 2.

- [ ] **Step 1: Write failing metadata-registry tests**

Add tests that build every page and assert the seven indexable pages have their exact title/description, `<link rel="canonical">`, `<meta name="robots" content="index, follow">`, `og:site_name`, `og:type=website`, matching OG title/description/url, shared absolute OG image/type/alt, and Twitter `summary_large_image` title/description/image. Assert `404.html` contains `noindex` and does not contain a canonical link or JSON-LD.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
pytest tests/test_site_build.py tests/test_public_manifest.py -q
```

Expected: new metadata assertions fail because the registry/shared social head do not exist yet.

- [ ] **Step 3: Implement `PublicPage` and replace tuple page entries**

In `site/build_site.py`, add `SITE_ORIGIN`, `SOCIAL_IMAGE_URL`, the frozen `PublicPage` dataclass, and registry entries with the existing page titles/descriptions and exact canonical paths. Use `schema_type="AboutPage"` for `/about/`, `"ContactPage"` for `/contact/`, and `indexable=False` for `404.html`.

- [ ] **Step 4: Render registry metadata through `base.html`**

Make `base.html` read `page.title`, `page.description`, `page.canonical_url`, and `page.indexable`. For indexable pages emit the complete canonical/robots/OG/Twitter package. For non-indexable pages emit only the page title/description plus `noindex`. Keep favicon, Apple touch icon, public manifest, theme color, styles, navigation, and footer unchanged.

- [ ] **Step 5: Remove superseded per-template metadata blocks**

Leave each content template responsible for visible page content only; remove its `title`, `description`, `canonical_url`, and 404 `head_extra` metadata blocks now supplied by the registry/base shell.

- [ ] **Step 6: Run focused tests**

```bash
pytest tests/test_site_build.py tests/test_public_manifest.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add site/build_site.py site/templates tests/test_site_build.py tests/test_public_manifest.py
git commit -m "feat: add shared public SEO metadata"
```

---

### Task 2: Add Structured Data from the Page Registry

**Files:**
- Modify: `site/build_site.py`
- Modify: `site/templates/base.html`
- Modify: `tests/test_site_build.py`

**Interfaces:**
- Consumes: `PublicPage` and `SITE_ORIGIN` from Task 1.
- Produces: `_structured_data_for(page: PublicPage) -> Optional[dict[str, object]]`.
- `build_site()` passes that dictionary as `structured_data`; `base.html` emits it using Jinja `tojson`, not manually concatenated JSON.

- [ ] **Step 1: Write failing JSON-LD tests**

Add a helper that extracts the `application/ld+json` script and parses it with `json.loads`. Assert homepage `@graph` contains `Organization`, `WebSite`, and `SoftwareApplication` with IDs `#organization`, `#website`, and `#software`; Quollnet/Quoll Unipessoal LDA identity; app URL `https://cashflowpot.com/app/`; `applicationCategory="BusinessApplication"`; `operatingSystem="Web"`; and current feature text covering scenario forecasting, activity-based outflow, independent/activity-linked inflow, cash/working-capital analysis, and Excel export. Assert it contains no `Offer`.

For internal pages assert page type, canonical URL, `isPartOf` website reference, and a two-item `BreadcrumbList` (`CashflowPot` → current page). Assert 404 has no JSON-LD.

- [ ] **Step 2: Run the JSON-LD tests and confirm failure**

```bash
pytest tests/test_site_build.py -q
```

Expected: structured-data assertions fail.

- [ ] **Step 3: Implement `_structured_data_for(page)`**

Return one homepage `@graph` for `/`; for indexable internal pages return `@graph` with page entity plus `BreadcrumbList`; for non-indexable pages return `None`. Reuse `page.title`, `page.description`, and `page.canonical_url` rather than duplicating them. Use only confirmed Quollnet social URLs already present on the Contact page for `sameAs`.

- [ ] **Step 4: Render JSON-LD safely in the shared head**

In `base.html`, conditionally emit one `<script type="application/ld+json">{{ structured_data | tojson }}</script>` when `structured_data` is present.

- [ ] **Step 5: Run focused tests**

```bash
pytest tests/test_site_build.py -q
```

Expected: PASS, including `json.loads` parsing.

- [ ] **Step 6: Commit**

```bash
git add site/build_site.py site/templates/base.html tests/test_site_build.py
git commit -m "feat: add CashflowPot structured data"
```

---

### Task 3: Generate and Safely Publish robots.txt, sitemap.xml, and llms.txt

**Files:**
- Modify: `site/build_site.py`
- Modify: `tests/test_site_build.py`
- Modify: `tests/test_site_deployment.py`

**Interfaces:**
- Consumes: `PAGES`, `PublicPage.indexable`, and `PublicPage.canonical_url`.
- Produces: `ROOT_DISCOVERY_FILES = ("robots.txt", "sitemap.xml", "llms.txt")`.
- Produces functions `_render_robots_txt() -> str`, `_render_sitemap_xml() -> str`, `_render_llms_txt() -> str`.
- `_managed_publish_entries()` includes all three generated root files while preserving existing page roots and `assets`.

- [ ] **Step 1: Write failing discovery-file tests**

Assert a build creates all three root files. `robots.txt` must contain a wildcard group allowing the public site, `Disallow: /api/`, no `Disallow: /app/`, an `OAI-SearchBot` group that also excludes `/api/`, and `Sitemap: https://cashflowpot.com/sitemap.xml`.

Parse `sitemap.xml` with `xml.etree.ElementTree`; assert its `<loc>` set equals exactly the seven approved canonical page URLs and contains no `/app/`, `/api/`, `404`, or asset URLs and no fabricated `<lastmod>`.

Assert `llms.txt` identifies CashflowPot as construction cash-flow simulation/forecasting and links the homepage, How it works, Methodology, About, `/app/`, and Quollnet relationship.

- [ ] **Step 2: Extend deployment tests before implementation**

Update `test_publish_replaces_only_site_owned_paths` so stale production copies of `robots.txt`, `sitemap.xml`, and `llms.txt` are replaced by built versions, while sentinel files under `/app/`, `/api/`, and an unrelated root file remain unchanged.

- [ ] **Step 3: Run focused tests and confirm failure**

```bash
pytest tests/test_site_build.py tests/test_site_deployment.py -q
```

Expected: failures because root discovery files are absent/unmanaged.

- [ ] **Step 4: Implement discovery renderers and build output**

Generate `robots.txt` and `llms.txt` as UTF-8 text and `sitemap.xml` as valid XML derived from `PAGES`. Write them directly under the build root after page rendering.

- [ ] **Step 5: Extend managed publishing**

Add `ROOT_DISCOVERY_FILES` to `_managed_publish_entries()` without changing the selective replacement algorithm.

- [ ] **Step 6: Run build/deployment tests**

```bash
pytest tests/test_site_build.py tests/test_site_deployment.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add site/build_site.py tests/test_site_build.py tests/test_site_deployment.py
git commit -m "feat: generate search discovery files"
```

---

### Task 4: Put the Approved Hero Image on the Homepage

**Files:**
- Modify: `site/templates/index.html`
- Modify: `site/static/css/site.css`
- Modify: `tests/test_site_build.py`

**Interfaces:**
- Consumes existing asset `site/static/images/home-hero.webp`.
- Produces visible `<img class="hero__image" src="/assets/images/home-hero.webp" ...>` with meaningful alt text and responsive styling.

- [ ] **Step 1: Write the failing hero test**

Assert generated `index.html` contains `/assets/images/home-hero.webp`, a non-empty descriptive alt such as `Engineer and finance professional reviewing a construction cash-flow forecast`, and `fetchpriority="high"`; assert no other generated page references `home-hero.webp`.

- [ ] **Step 2: Run the test and confirm failure**

```bash
pytest tests/test_site_build.py -q
```

Expected: FAIL because the homepage does not yet render the hero image.

- [ ] **Step 3: Replace the current right-side hero card with the approved image**

Keep the existing homepage headline, lead/support copy, and CTAs. Render the image as a normal `<img>` in the existing two-column hero composition; do not use a CSS background.

- [ ] **Step 4: Add responsive image styling**

Style `.hero__image` to fill its column cleanly with rounded corners/object-fit behavior, remain readable in light/dark themes, and collapse naturally with the existing mobile grid breakpoint.

- [ ] **Step 5: Run focused tests**

```bash
pytest tests/test_site_build.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add site/templates/index.html site/static/css/site.css tests/test_site_build.py
git commit -m "feat: add CashflowPot homepage hero"
```

---

### Task 5: Document the Discovery Architecture and Run Final Verification

**Files:**
- Modify: `documentation/deployment.md`
- Modify: `documentation/technical.md`
- Modify: `documentation/ui-ux.md`
- Modify: `tests/test_documentation.py`

**Interfaces:**
- Consumes completed implementation from Tasks 1–4.
- Produces authoritative current-product documentation for public discovery, metadata/social image, root files, and `/app/` noindex boundary.

- [ ] **Step 1: Add documentation contract tests**

Require the authoritative docs to mention `robots.txt`, `sitemap.xml`, `llms.txt`, `cashflowpot-og.webp`, the public-site/app split, `/app/` remaining crawlable but non-indexable, and the rule that `/api/` is not a discovery surface.

- [ ] **Step 2: Run documentation tests and confirm failure**

```bash
pytest tests/test_documentation.py -q
```

Expected: FAIL for the new documentation requirements.

- [ ] **Step 3: Update current-product documentation**

In `deployment.md`, add the three root files to the production layout/managed entries and post-deploy checks; document that the public builder does not own `/app/` or `/api/` and that `/app/` is intentionally crawlable for its noindex contract. In `technical.md`, document the page registry, JSON-LD/social metadata, and generated discovery files. In `ui-ux.md`, add the shared OG image and rule that social/metadata copy must match current visible product positioning.

- [ ] **Step 4: Run all public-site/documentation tests**

```bash
pytest tests/test_site_build.py tests/test_site_deployment.py tests/test_public_manifest.py tests/test_documentation.py -q
```

Expected: PASS.

- [ ] **Step 5: Build locally and inspect generated artifacts**

```bash
python site/build_site.py -l
```

Verify `site/dist/robots.txt`, `sitemap.xml`, `llms.txt`, homepage metadata/JSON-LD/hero, and one internal page. Confirm no command attempts to publish because `-l` is used.

- [ ] **Step 6: Run the full q_flow test suite**

```bash
pytest
```

Expected: PASS. If an unrelated pre-existing failure appears, record it explicitly rather than claiming the suite passed.

- [ ] **Step 7: Commit**

```bash
git add documentation tests/test_documentation.py
git commit -m "docs: document public search discovery"
```
