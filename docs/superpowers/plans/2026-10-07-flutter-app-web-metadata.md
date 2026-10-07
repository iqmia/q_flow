# CashflowPot Flutter App Web Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep `https://cashflowpot.com/app/` shareable with current CashflowPot social metadata while explicitly preventing it from competing with the public site as an indexable search result.

**Architecture:** Treat `web/index.html` as a Flutter application shell, not a second SEO landing page. Keep only app/browser metadata plus OG/Twitter sharing and the existing boot/splash behavior; use the public site's absolute social image. Keep the Flutter manifest app-scoped and reuse the existing icon set.

**Tech Stack:** Flutter/Dart, static web HTML/JSON, `flutter_test` with `dart:io` for source-file contract tests.

**Spec:** `iqmia/q_flow:docs/superpowers/specs/2026-10-07-seo-ai-discovery-design.md`

## Global Constraints

- Work directly on `iqmia/cashflowpot` branch `main`.
- `/app/` must render `<meta name="robots" content="noindex, follow">`.
- Do not block `/app/` through app code; the public `robots.txt` remains owned by `q_flow`.
- App social URL is `https://cashflowpot.com/app/`.
- Shared social image is `https://cashflowpot.com/assets/images/cashflowpot-og.webp`.
- Title is `CashflowPot | Construction Cash-Flow Forecasting`.
- Description is `Open CashflowPot to build and review construction project cash-flow forecasts from execution timing, contract terms and forecasting assumptions.`
- Social description is `Build and review construction project cash-flow forecasts from execution timing, contract terms and forecasting assumptions.`
- No JSON-LD is needed in `/app/`; the public homepage owns the canonical software structured-data representation.
- Keep existing Flutter bootstrap, analytics behavior, loading-progress behavior, favicon/touch icons, and application functionality intact.
- Flutter manifest keeps `start_url: "."`, `display: "standalone"`, `orientation: "portrait-primary"`, `prefer_related_applications: false`, and the existing icon entries.
- Manifest colors: background `#F7F4EF`, theme `#E89A5B`.

## Review Focus

- **Indexing conflict:** the app shell must contain exactly the intended `noindex, follow` signal and no canonical public-page SEO behavior that suggests `/app/` should rank independently. Task 1 pins this.
- **Share previews:** OG and Twitter URLs/images must be absolute so sharing `/app/` works independently of the Flutter `<base>` path. Task 1 pins this.
- **Flutter boot integrity:** metadata cleanup must not remove `$FLUTTER_BASE_HREF`, `flutter_bootstrap.js`, analytics loading, or `flutter-first-frame` splash removal. Task 1 pins these sentinels.
- **Manifest scope:** `start_url` must remain `.` so installation opens `/app/` rather than the public homepage. Task 2 pins this.
- **Icon reuse:** existing normal and maskable icon paths must remain unchanged; no second icon set is introduced. Task 2 pins this.

---

### Task 1: Make the Flutter Web Shell Noindex but Shareable

**Files:**
- Create: `test/web_metadata_test.dart`
- Modify: `web/index.html`

**Interfaces:**
- Produces a source-level contract test reading `web/index.html` with `dart:io`.
- Produces the app-shell metadata contract consumed by social platforms/crawlers while leaving Flutter bootstrap unchanged.

- [ ] **Step 1: Write the failing source-contract test**

Create `test/web_metadata_test.dart` and assert the HTML contains:

```text
<meta name="robots" content="noindex, follow">
<title>CashflowPot | Construction Cash-Flow Forecasting</title>
https://cashflowpot.com/app/
https://cashflowpot.com/assets/images/cashflowpot-og.webp
og:site_name = CashflowPot
og:type = website
twitter:card = summary_large_image
Construction cash-flow forecasting for project, commercial and finance decisions.
```

Also assert there is no `<script type="application/ld+json">` and no `meta name="keywords"`.

Add preservation assertions for `$FLUTTER_BASE_HREF`, `flutter_bootstrap.js`, `flutter-first-frame`, the Google Analytics ID/script path already used by the file, and existing icon/manifest links.

- [ ] **Step 2: Run the focused test and confirm failure**

```bash
flutter test test/web_metadata_test.dart
```

Expected: FAIL on the new metadata contract.

- [ ] **Step 3: Replace only the app-shell metadata in `web/index.html`**

Set the exact title/description/robots values from Global Constraints. Add OG site name/type/title/description/url/image and Twitter card/title/description/image using absolute URLs. Keep the current viewport/PWA icons/manifest/bootstrap/analytics behavior.

- [ ] **Step 4: Simplify the visible loading-splash description**

Use exactly:

```text
Construction cash-flow forecasting for project, commercial and finance decisions.
```

Do not turn the splash into a marketing page; retain the current CashflowPot logo/title, Quollnet attribution, loading bar, and first-frame removal behavior.

- [ ] **Step 5: Run the focused test**

```bash
flutter test test/web_metadata_test.dart
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/index.html test/web_metadata_test.dart
git commit -m "feat: make app shell shareable and noindex"
```

---

### Task 2: Align the Flutter Web Manifest with Current CashflowPot Identity

**Files:**
- Modify: `web/manifest.json`
- Modify: `test/web_metadata_test.dart`

**Interfaces:**
- Consumes existing icon paths in `web/icons/`.
- Produces manifest fields: `name="CashflowPot"`, `short_name="CashflowPot"`, `description="Construction cash-flow simulation and forecasting."`, `start_url="."`, `display="standalone"`, `background_color="#F7F4EF"`, `theme_color="#E89A5B"`.

- [ ] **Step 1: Add failing manifest assertions**

In `web_metadata_test.dart`, parse `web/manifest.json` with `jsonDecode`. Assert the exact values above and assert `orientation == "portrait-primary"` and `prefer_related_applications == false`. Assert the icon-source set remains:

```text
icons/Icon-192.png
icons/Icon-512.png
icons/Icon-maskable-192.png
icons/Icon-maskable-512.png
```

Assert the two maskable entries still use `purpose: maskable`.

- [ ] **Step 2: Run the focused test and confirm failure**

```bash
flutter test test/web_metadata_test.dart
```

Expected: FAIL on current manifest identity/colors/description.

- [ ] **Step 3: Update `web/manifest.json`**

Change only the approved `name`, `short_name`, `description`, `background_color`, and `theme_color` values. Preserve `start_url`, `display`, `orientation`, `prefer_related_applications`, and all existing icon definitions unchanged.

- [ ] **Step 4: Run the focused test**

```bash
flutter test test/web_metadata_test.dart
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/manifest.json test/web_metadata_test.dart
git commit -m "chore: align CashflowPot web manifest"
```

---

### Task 3: Verify the Flutter Web Build Contract

**Files:**
- No planned product-code changes unless verification exposes a regression.

**Interfaces:**
- Consumes Tasks 1–2.
- Produces verified source and build output for the `/app/` deployment.

- [ ] **Step 1: Run the focused metadata test**

```bash
flutter test test/web_metadata_test.dart
```

Expected: PASS.

- [ ] **Step 2: Run the Flutter test suite**

```bash
flutter test
```

Expected: PASS. If a pre-existing unrelated failure appears, record it explicitly rather than claiming the suite passed.

- [ ] **Step 3: Build the web application for its production `/app/` mount**

```bash
flutter build web --base-href /app/
```

After build, inspect `build/web/index.html` and `build/web/manifest.json` to confirm the noindex/social metadata, `$FLUTTER_BASE_HREF` replacement with `/app/`, and current manifest identity survived the Flutter build step.

- [ ] **Step 4: Commit only if verification required a corrective source change**

If no correction was needed, do not create an empty commit.
