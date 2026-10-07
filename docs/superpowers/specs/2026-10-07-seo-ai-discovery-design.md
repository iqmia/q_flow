# CashflowPot SEO and AI Discovery — Design

Date: 2026-10-07

## Goal

Make `cashflowpot.com` the authoritative public discovery surface for CashflowPot across conventional search, social sharing, and AI-assisted search/citation systems, while keeping the authenticated Flutter application under `/app/` shareable but non-indexable.

The design must preserve the existing deployment split:

```text
https://cashflowpot.com/      static public website from q_flow/site/
https://cashflowpot.com/app/  Flutter application from iqmia/cashflowpot
https://cashflowpot.com/api/  Flask API through Passenger
```

The public site remains static and is built/published by `site/build_site.py`.

## Product Positioning To Preserve

SEO, social, structured data, and AI-readable content must match the current product definition in `documentation/product.md`.

CashflowPot is a construction cash-flow simulation and forecasting product that turns execution timing, contract terms, and forecasting assumptions into time-phased inflow, outflow, net cash, cumulative cash position, and working-capital/funding exposure.

Public metadata must use current terminology, including:

- Construction cash-flow simulation and forecasting.
- Independent contract curve.
- Activity-linked inflow.
- Work in Excess of Billings (WIEB).
- Contract terms and forecasting assumptions.
- Working-capital / funding requirement.

Do not advertise future functionality as current functionality.

## Search and Indexing Architecture

### Public site

The public static site at `/` is the canonical indexable surface.

Indexable pages are:

```text
/
/how-it-works/
/methodology/
/about/
/contact/
/privacy/
/terms/
```

`404.html` is not indexable and is not included in the sitemap.

### Flutter application

`/app/` remains crawlable but is explicitly non-indexable:

```html
<meta name="robots" content="noindex, follow">
```

The app must not be blocked in `robots.txt`, because crawlers need to fetch it in order to see the `noindex` directive.

`/app/` must not appear in the public sitemap.

### API

`/api/` is not a discovery surface and should be disallowed in `robots.txt`.

## Public Page Registry

`site/build_site.py` should evolve from a simple template/destination list into a small public-page registry that can provide, at minimum:

- template name;
- output destination;
- canonical path/URL;
- whether the page is indexable;
- page schema type where needed.

The registry is the source of truth for generated crawl/discovery files such as `sitemap.xml`.

Visible title and description copy can remain in the individual Jinja templates, but canonical/indexing behavior and generated discovery files should not require separate manually maintained URL lists.

## robots.txt

`build_site.py` should generate a root-level `robots.txt`.

Required behavior:

- allow normal crawling of the public site;
- allow `/app/` to be fetched so its `noindex` can be read;
- disallow `/api/`;
- point crawlers to the public sitemap;
- explicitly allow `OAI-SearchBot` to crawl the public site.

The file should not attempt to use robots rules as a substitute for `noindex` on `/app/`.

The file should be generated into the build root and published as a site-owned root file.

## sitemap.xml

`build_site.py` should generate a root-level XML sitemap from the authoritative public-page registry.

The sitemap contains only canonical indexable public pages:

```text
https://cashflowpot.com/
https://cashflowpot.com/how-it-works/
https://cashflowpot.com/methodology/
https://cashflowpot.com/about/
https://cashflowpot.com/contact/
https://cashflowpot.com/privacy/
https://cashflowpot.com/terms/
```

Do not include:

- `/app/`;
- `/api/`;
- `404.html`;
- generated asset URLs.

Do not fabricate `lastmod` values unless the build system has a reliable source for them.

## llms.txt

Generate a root-level `llms.txt` as a concise machine-readable map of CashflowPot.

It should summarize:

- what CashflowPot is;
- the canonical homepage;
- the How it works page;
- the Methodology page;
- the About page;
- the relationship to Quollnet;
- the fact that `/app/` is the application surface.

Treat `llms.txt` as supplementary discovery/navigation information, not as a ranking or indexing control.

## Public Metadata Framework

`site/templates/base.html` should own the common metadata framework so every public page receives a consistent package.

Each indexable page should render:

- unique `<title>`;
- unique meta description;
- canonical URL;
- `robots=index, follow`;
- Open Graph site name, type, title, description, URL, image, image type, and image alt;
- Twitter summary-large-image card, title, description, and image;
- favicon, Apple touch icon, theme color, and public manifest already introduced previously.

No `meta keywords` tag is needed.

## Shared OG / Social Image

All public pages use one shared social image:

```text
site/static/images/cashflowpot-og.webp
```

Public URL:

```text
https://cashflowpot.com/assets/images/cashflowpot-og.webp
```

This same image is also used by `/app/` for Open Graph and Twitter sharing.

Public metadata should use an absolute image URL.

Suggested image alt text:

```text
CashflowPot construction cash-flow forecasting
```

## Homepage Hero Image

The homepage uses:

```text
site/static/images/home-hero.webp
```

Public URL:

```text
/assets/images/home-hero.webp
```

It should be rendered as a real `<img>` in the visible hero layout, not as a CSS background image.

The hero image needs meaningful alt text describing the construction/finance decision context without keyword stuffing.

`home-hero-2.webp` remains available but unused in this pass.

`cashflowpot-app-preview.webp` remains available for the later Quollnet app-listing update and is not required by the public-site SEO implementation.

## Structured Data

### Homepage graph

The homepage should include one JSON-LD `@graph` with stable entity identifiers.

Recommended identifiers:

```text
https://cashflowpot.com/#organization
https://cashflowpot.com/#website
https://cashflowpot.com/#software
```

The graph contains:

### Organization

Represents Quollnet / Quoll Unipessoal LDA.

Include only confirmed public identity information:

- `@type: Organization`;
- name: Quollnet;
- legal name: Quoll Unipessoal LDA;
- URL: `https://www.quollnet.com`;
- appropriate existing Quollnet public social/profile URLs in `sameAs`;
- relationship to the CashflowPot website/software through stable `@id` references.

### WebSite

Represents the public CashflowPot website.

Include:

- `@type: WebSite`;
- name: CashflowPot;
- URL: `https://cashflowpot.com/`;
- publisher reference to the Organization entity.

### SoftwareApplication

Represents the current CashflowPot web application.

Include confirmed current information only:

- `@type: SoftwareApplication`;
- name: CashflowPot;
- URL: `https://cashflowpot.com/app/`;
- application category consistent with a business/construction cash-flow application;
- operating system: Web;
- concise current product description;
- feature list limited to current capabilities such as scenario forecasting, activity-based outflow, independent/activity-linked inflow, working-capital/cash-position analysis, and Excel export;
- publisher/author relationship to the Organization entity.

Do not add an `Offer` until there is a public pricing/plan page or another authoritative public source suitable for structured pricing data.

Do not describe future AI-assisted setup as a current software feature.

## Internal Page Structured Data

Each non-home public content page should expose lightweight page-level JSON-LD and reference the same public site / organization entities.

Recommended page types:

- `/how-it-works/` → `WebPage`;
- `/methodology/` → `WebPage`;
- `/about/` → `AboutPage`;
- `/contact/` → `ContactPage`;
- `/privacy/` → `WebPage`;
- `/terms/` → `WebPage`.

Each page should use its canonical URL, visible title, and visible description.

### BreadcrumbList

Add a simple `BreadcrumbList` to internal public pages:

```text
CashflowPot → Current page
```

A visible breadcrumb component is not required in this pass.

## AI Discovery Principles

There is no separate hidden “AI SEO” content layer.

AI/search discoverability should come from the same high-quality canonical public content used by human readers:

- stable canonical URLs;
- descriptive headings;
- clear explanatory prose;
- current product terminology;
- methodology content that explains the model;
- consistent structured-data relationships;
- sitemap and robots rules;
- public crawlability;
- `llms.txt` as a supplementary content map.

Do not create invisible keyword blocks, machine-only claims, or metadata that contradicts visible content.

## Flutter `/app/` Metadata Contract

The Flutter source file `cashflowpot/web/index.html` should be reduced to application-shell metadata plus social-sharing metadata.

Required behavior:

- `robots: noindex, follow`;
- current CashflowPot title;
- concise current description;
- Open Graph metadata;
- Twitter summary-large-image metadata;
- canonical social URL `https://cashflowpot.com/app/` where relevant;
- shared social image `https://cashflowpot.com/assets/images/cashflowpot-og.webp`;
- existing app favicon/touch icons;
- existing Flutter bootstrap and loading behavior.

No JSON-LD is needed on `/app/` because the public homepage owns the canonical software structured-data representation.

The visible loading splash copy should use neutral current product wording, for example:

> Construction cash-flow forecasting for project, commercial and finance decisions.

The app shell should remain a loading/application surface, not a second SEO landing page.

## Flutter Manifest

Update `cashflowpot/web/manifest.json` to current product identity while keeping its role as the `/app/` web-app manifest.

Expected properties include:

```text
name: CashflowPot
short_name: CashflowPot
start_url: .
display: standalone
background_color: #F7F4EF
theme_color: #E89A5B
```

Description:

```text
Construction cash-flow simulation and forecasting.
```

Existing app icons remain the physical icon source.

## Two Manifests, One Icon Set

Preserve the already approved architecture:

```text
/app/icons/...                 physical Flutter-owned icon set
/app/manifest.json             Flutter app manifest
/assets/manifest.json          public website manifest
```

The public website manifest continues to reference the `/app/icons/...` files rather than duplicating them into `q_flow`.

## Build and Deployment Changes

`site/build_site.py` must publish the new root-level discovery files in addition to the existing page/asset entries.

New managed root files:

```text
robots.txt
sitemap.xml
llms.txt
```

The production publisher must continue to preserve unrelated web-root entries, especially:

```text
/app/
/api/
```

The build must not clean or replace the entire production web root.

## Documentation

Update the authoritative `documentation/` set so the SEO/discovery architecture is understandable later without reading implementation-history specs.

At minimum:

- `documentation/deployment.md` should mention the generated root discovery files and the `/app/` noindex contract;
- `documentation/ui-ux.md` or `technical.md` should document the shared public metadata/social-image behavior if appropriate;
- `documentation/future.md` does not need changes unless new future work is added.

This spec remains historical design context under `docs/superpowers/specs/`; current behavior belongs in `documentation/` after implementation.

## Testing Requirements

### q_flow

Add or extend tests to verify:

- every canonical public page has title, description, canonical, robots, OG, and Twitter metadata;
- shared OG image URL is correct;
- homepage renders `home-hero.webp`;
- homepage JSON-LD is valid JSON and contains Organization, WebSite, and SoftwareApplication entities;
- internal page JSON-LD and breadcrumb data use the correct canonical URL/page type;
- `robots.txt` is generated with the intended crawl rules and sitemap reference;
- `sitemap.xml` contains exactly the intended indexable public pages and excludes `/app/`, `/api/`, and 404;
- `llms.txt` is generated and contains the canonical public content map;
- production publishing manages the new root files without touching `/app/` or `/api/`;
- existing public-site content/terminology guardrails continue to pass.

### cashflowpot

Add or update tests, where practical in the Flutter repo, to verify the static web shell contains:

- `noindex, follow`;
- current title/description;
- OG/Twitter metadata;
- shared absolute OG image URL;
- current manifest name/description/theme values;
- current loading-splash wording.

## Out of Scope

This pass does not include:

- rewriting the Quollnet CashflowPot app-listing copy;
- changing the Quollnet app-listing image to `cashflowpot-app-preview.webp`;
- creating additional public content pages or blog/article migrations;
- adding page-specific social images;
- adding pricing pages;
- adding analytics changes;
- implementing AI-assisted project setup;
- changing backend cash-flow formulas or business logic.

## Success Criteria

The work is successful when:

1. `cashflowpot.com` is the single authoritative indexable product surface.
2. Search and AI crawlers can discover the public site, sitemap, methodology, and structured entities.
3. `/app/` remains shareable with a professional social preview but is not intended to appear as a separate search result.
4. `/api/` is excluded from crawling.
5. Every public page has consistent canonical, social, and indexing metadata.
6. Structured data describes only confirmed current product/company information.
7. `build_site.py` generates and deploys the complete discovery package safely without touching `/app/` or `/api/`.
8. The homepage visibly uses `home-hero.webp` and all public/social metadata uses `cashflowpot-og.webp`.
9. The public and Flutter manifests remain distinct while sharing one physical icon set.
