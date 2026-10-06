# CashflowPot Public Site Content Pages — Design

Date: 2026-10-06

## Goal

Bring the CashflowPot public website in line with the current product model, add the missing permanent pages, and establish a stable information architecture that can support product discovery, legal pages, support/contact, and future educational links without making the site feel like a content portal.

The public site remains a lightweight static site generated from `q_flow/site/`. CashflowPot remains the dominant product brand; Quollnet remains the parent brand. The app continues to live at `/app/` and the Flask API at `/api/`.

## Product Positioning To Preserve

CashflowPot is a lightweight construction cash-flow forecasting application for contractors, commercial/project teams, finance teams, lenders and investors.

It is designed for tender forecasts, feasibility studies, working-capital planning, annual budgeting, project reforecasting, recovery planning and financing discussions.

It is not a replacement for Primavera P6, MS Project, ERP/accounting, or a full project cost-control system.

The key product philosophy is:

> A forecast designed to be revised.

The public site must explain that the model can be updated quickly as assumptions change rather than present CashflowPot as a one-time deterministic prediction engine.

## Current Product Model That Public Content Must Reflect

The current public pages still describe the original activity-linked inflow calculation as though it were the only method. That is now outdated.

CashflowPot supports two project inflow methods:

### Independent contract curve — default and recommended

New scenarios default to an independent contract-value curve.

- The project duration is still derived from the activity schedule.
- Contract value is distributed over that duration using either an S-curve or a linear distribution.
- The S-curve can be back-loaded, balanced or front-loaded.
- New fast scenarios default to a balanced S-curve.
- Client-side commercial assumptions are applied after the underlying contract-value distribution is generated.

The UI does not expose backend field names such as `use_independent_inflow_curve` or `inflow_curve_skew`.

### Activity-linked inflow — alternative

The existing method remains available.

- Activity work/cost distributions are combined.
- The combined profile is scaled proportionally to the contract value.
- Main-contract commercial assumptions are then applied.

This method should be described as an alternative for users who want contract inflow to follow the activity execution profile.

### Outflow behavior

Outflow remains activity-based under both inflow methods.

Activities define execution cost, timing and project duration. Each activity can be linear or curved and can be split between direct/self-performed and subcontracted work. Subcontracted work follows its own commercial assumptions.

### Terminology

Public site wording must match the current app:

- `Work in Excess of Billings (WIEB)` — not Billing Deferral.
- `Payment period` — not Payment Delay or Time for Payment in UI-oriented descriptions.
- `Defects Liability Period (DLP)`.
- `Independent contract curve` and `Activity-linked inflow` for the two inflow methods.
- Use `Back-loaded`, `Balanced`, and `Front-loaded` rather than exposing the numeric skew parameter to normal users.

## Information Architecture

### Primary header navigation

Keep the header short and product-focused:

- CashflowPot logo/name → `/`
- How it works → `/how-it-works/`
- Methodology → `/methodology/`
- About → `/about/`
- Open app → `/app/`

Contact, Privacy and Terms do not belong in the primary navigation.

The current `A Quollnet product` parent-brand attribution remains subordinate to CashflowPot.

### Footer navigation

Expand the footer into compact grouped navigation while preserving the existing Quollnet attribution sentence.

Product:

- How it works
- Methodology
- About
- Open app

Company / support:

- Contact
- Privacy
- Terms
- CashflowPot on Quollnet

The footer must preserve this product attribution wording:

> CashflowPot is part of the Quollnet ecosystem for engineering and construction. Explore CashflowPot on Quollnet.

The `Explore CashflowPot on Quollnet` link remains `https://quollnet.com/apps/cashflowpot`.

## Branding and Logo

The public site should stop relying on text-only product branding in the header.

Reuse the existing CashflowPot logo from the Flutter/web assets, preferably one of:

- `cashflowpot/assets/icon/qflow_logo.png`
- `cashflowpot/web/icons/Icon-192.png`

The selected source image will be copied into `q_flow/site/static/` as a normal public-site asset rather than referenced across repositories at runtime.

Header treatment:

- small logo mark;
- `CashflowPot` product name;
- smaller `A Quollnet product` line/link.

The logo must work on both light and dark theme backgrounds. If the current icon is not suitable on both themes, use the circular white-background variant rather than adding theme-specific complexity in this pass.

## Page Design

### Home (`/`)

The current overall homepage direction remains valid, but outdated model wording must be corrected.

Primary message:

- construction cash-flow forecasting without heavyweight setup;
- usable for tendering, feasibility, budgeting, execution reforecasting and financing discussions;
- activities define execution timing/cost while contract inflow can be modeled independently or linked to execution.

The homepage should not become a technical methodology page.

Required corrections:

- remove wording that implies activities always drive contract value/earned value;
- describe the independent contract curve as the normal/default method;
- mention that a new scenario can be created quickly using sensible defaults, including a balanced S-curve;
- keep Excel export, funding requirement, peak negative cash, scenario comparison and lifecycle use cases prominent;
- retain the statement that AI-assisted project setup is in development and that the backend calculation engine remains authoritative.

### How it works (`/how-it-works/`)

This page is the practical product walkthrough.

Recommended structure:

1. **Define the project**
   - project name/description;
   - contract value;
   - main commercial assumptions.

2. **Set the inflow forecast method**
   - Independent contract curve — recommended/default;
   - Activity-linked inflow — alternative;
   - fast setup uses a balanced S-curve without requiring the user to configure everything manually.

3. **Build the activity forecast**
   - activity timing;
   - estimated cost;
   - direct/subcontracted split;
   - linear or S-curve work timing.

4. **Apply commercial terms**
   - client advance;
   - WIEB;
   - retention;
   - payment period;
   - DLP;
   - subcontract-specific terms.

5. **Review the forecast**
   - inflow;
   - outflow;
   - net cash;
   - cumulative balance;
   - peak negative cash / working-capital requirement.

6. **Revise scenarios and export**
   - tender/base/current/recovery scenarios;
   - professional Excel output.

The page should stay practical and avoid detailed formulas.

### Methodology (`/methodology/`)

This page becomes the canonical public explanation of the model.

The opening philosophy remains:

> A forecast designed to be revised.

The existing methodology should be reorganized around the separation between execution and cash timing.

#### Main-contract inflow section

Explain the two supported methods explicitly.

**Independent contract curve — default**

- determine scenario duration from the activity schedule;
- distribute contract value across that duration using an S-curve or linear distribution;
- allow timing to be back-loaded, balanced or front-loaded for the S-curve;
- apply client-side commercial assumptions after the contract-value distribution.

**Activity-linked inflow — alternative**

- combine activity work distributions;
- scale the combined profile to contract value;
- apply the same client commercial assumptions afterward.

The public page should explain the concept first; advanced formulas/details can remain under expandable sections where appropriate.

#### Client commercial terms

Keep and update explanations for:

- advance payment and recovery;
- WIEB;
- retention;
- payment period;
- release at completion;
- DLP release.

#### Execution/outflow section

Keep activity-based logic:

- activity work distribution;
- direct/self-performed share;
- subcontracted share;
- subcontract commercial assumptions;
- direct cost has no WIEB transformation;
- subcontract WIEB represents performed work not yet billable to the contractor by the subcontractor relationship.

#### Net cash and financing

Retain the clear distinction between inflow, outflow, net cash, cumulative/pre-finance balance and financing charge on negative balances.

#### Remove obsolete roadmap claim

Remove the current public section describing activity-specific selling value / markup allocation as a planned extension. Per-activity selling price / Schedule-of-Values allocation is not a core CashflowPot roadmap item and should not be advertised publicly.

### About (`/about/`)

Purpose: explain what CashflowPot is and why it exists without duplicating the homepage.

Content:

- larger CashflowPot logo/brand treatment;
- short description of CashflowPot as focused construction cash-flow forecasting software;
- why it exists: cash decisions often need a credible forecast faster than rebuilding a detailed cost-loaded programme;
- target users and decisions;
- `A forecast designed to be revised` philosophy;
- lightweight-by-design boundaries;
- CashflowPot is a Quollnet product;
- link to `https://quollnet.com/apps/cashflowpot`.

Do not use the legal company name prominently on this marketing/product page.

### Contact (`/contact/`)

CashflowPot has no separate product contact identity. Contact/support routes through Quollnet.

Page opening should make that explicit:

> CashflowPot is a Quollnet product. For product questions, feedback or support, contact us through Quollnet.

Use the existing Quollnet contact/social destinations already used by the CashflowPot client:

- Quollnet website: `https://www.quollnet.com`
- Facebook: `https://www.facebook.com/people/Quollnet/100086014988886/`
- Instagram: `https://www.instagram.com/quollnet/`
- X: `https://twitter.com/quollnet`
- LinkedIn: `https://www.linkedin.com/in/quollnet/`
- YouTube: `https://www.youtube.com/@quollnet`
- WhatsApp: `https://wa.me/351911747738`

Use simple labeled links/cards. The static site does not need Font Awesome or a new icon-font dependency in this pass; text labels are sufficient and more robust.

A small company-information block may identify:

> Quollnet  
> Quoll Unipessoal LDA

Do not invent a separate CashflowPot email address.

### Privacy (`/privacy/`)

Visible brand/legal heading:

> Quollnet  
> Quoll Unipessoal LDA

Opening identity:

> CashflowPot is a Quollnet product operated by Quoll Unipessoal LDA.

This page should be readable, plain-language and specific to the product rather than a generic legal template.

Sections should cover:

- scope of the privacy notice;
- information users provide, including account/profile data and project/scenario information;
- authentication/account information;
- technical/usage information reasonably necessary to operate and secure the service;
- how information is used to provide, maintain and improve the service;
- service providers/infrastructure where applicable, without making unsupported claims about specific subprocessors;
- retention principles;
- security practices stated cautiously rather than as absolute guarantees;
- user rights and requests, subject to applicable law;
- contact via Quollnet;
- changes to the notice.

The implementation must avoid claims not supported by the current system, such as absolute promises that data is never logged, never transferred, or retained for a fixed period unless that behavior is confirmed.

The page should include a `Last updated` date.

### Terms (`/terms/`)

Visible brand/legal heading:

> Quollnet  
> Quoll Unipessoal LDA

Opening identity:

> CashflowPot is a Quollnet product operated by Quoll Unipessoal LDA.

Sections should cover:

- acceptance of terms;
- account responsibility;
- permitted/acceptable use;
- user responsibility for project assumptions and entered data;
- forecasts are planning estimates, not guarantees of actual future cash flows;
- users remain responsible for professional/commercial decisions;
- service availability and the ability to change/improve the service;
- ownership of the CashflowPot service and user ownership/responsibility for their own project content;
- reasonable limitation-of-liability/disclaimer language without overreaching wording;
- privacy notice cross-reference;
- contact through Quollnet;
- changes to terms.

The page should include a `Last updated` date.

## Quollnet Article Linking Strategy

The four existing English Quollnet articles were reviewed and all require major updates:

- `construction_cashflow_prediction`
- `How_to_Create_a_Project_Cash_Flow_for_Contractors`
- `Quollnet_cashflow`
- `master_construction_project_cashflow_with_cashflowpot`

They currently contain outdated terminology, old UI instructions, obsolete model assumptions, or references to the previous Quollnet cash-flow tool.

### Decision for this site pass

Do **not** link these four legacy article URLs from the CashflowPot public site yet.

Reasons:

- their content is currently outdated;
- several slugs use legacy capitalization/underscores and may be changed;
- linking before slug/content decisions would create unnecessary redirect or maintenance obligations;
- the CashflowPot public site should be the canonical product/methodology source.

Continue linking the stable Quollnet CashflowPot app page now:

`https://quollnet.com/apps/cashflowpot`

### Future article role

After the Quollnet articles are rewritten, add a small `Construction cash-flow guides on Quollnet` section near the bottom of Methodology or About, with only the strongest two or three educational articles.

Possible future clean slugs, to be decided during article rewrite rather than this site pass:

- `construction-project-cash-flow-forecasting`
- `how-to-create-a-construction-project-cash-flow`
- `cashflowpot-construction-cash-flow-tutorial`

The old `Quollnet_cashflow` article should be evaluated for retirement/redirect because its subject is the superseded Quollnet cash-flow tool rather than the current CashflowPot product.

## SEO and Metadata

Every new permanent page gets:

- unique `<title>`;
- unique meta description;
- canonical URL on `https://cashflowpot.com/.../`;
- semantic H1/H2 hierarchy;
- internal links back to relevant product pages;
- system light/dark theme via the existing shared CSS.

Privacy and Terms should be indexable unless there is a specific later SEO reason not to index them. The 404 remains `noindex`.

Do not add article schema or blog infrastructure in this pass.

## Static Build Changes

`site/build_site.py` must generate:

- `/index.html`
- `/how-it-works/index.html`
- `/methodology/index.html`
- `/about/index.html`
- `/contact/index.html`
- `/privacy/index.html`
- `/terms/index.html`
- `/404.html`

Templates remain Jinja-based static source files under `site/templates/`.

Shared styling remains in `site/static/css/site.css`.

The logo will be added to `site/static/` and therefore copied into `/assets/` by the existing builder.

No dynamic Flask route is required for these pages.

## Responsive Behavior

The existing responsive site shell remains the basis.

The header must continue to work on narrow screens after adding the logo. If necessary, the brand block and navigation may wrap naturally, but the `Open app` CTA should remain visible.

Footer groups should stack on small screens.

Legal pages should use a narrower readable content measure rather than full-width marketing grids.

## Testing Strategy

Use TDD for implementation.

Extend `tests/test_site_build.py` first so the test suite verifies:

- all seven permanent pages plus 404 are generated;
- shared navigation contains Home/How it works/Methodology/About/Open app as designed;
- footer contains Contact/Privacy/Terms and the stable Quollnet CashflowPot link;
- the exact existing Quollnet ecosystem attribution remains present;
- logo asset is copied into the built site and referenced from the base template;
- About, Contact, Privacy and Terms have canonical URLs and expected headings;
- Privacy and Terms contain `Quollnet` and `Quoll Unipessoal LDA`;
- Contact contains the approved Quollnet contact destinations;
- Home/How it works/Methodology contain the updated independent-vs-linked inflow terminology;
- obsolete public wording such as `Billing Deferral` and the planned activity-specific selling-value roadmap section does not remain in current generated pages.

Run focused site-build tests first, then the full backend suite before completion.

## Non-Goals

This pass does not:

- rewrite or edit the four Quollnet articles;
- choose/finalize their replacement slugs;
- add a blog/resources section to CashflowPot;
- add pricing pages;
- add a contact form or support ticket system;
- change authentication or Flutter app behavior;
- change calculation logic;
- add per-activity selling values/SOV modeling;
- add a manual public-site theme switcher;
- replace the existing static-site build architecture.

## Acceptance Criteria

The pass is complete when:

1. Home, How it works and Methodology accurately describe the current two-mode inflow model, with independent balanced S-curve as the new-scenario default.
2. About, Contact, Privacy and Terms are generated as permanent static pages with consistent CashflowPot branding.
3. Privacy and Terms visibly use `Quollnet` with `Quoll Unipessoal LDA` as the legal operator.
4. Contact uses the existing Quollnet channels and does not invent a CashflowPot-specific contact identity.
5. The header remains product-focused; legal/support links live in the footer.
6. The existing Quollnet ecosystem attribution and stable Quollnet CashflowPot app link remain present.
7. The CashflowPot logo is reused from the existing product assets and served locally by the static site.
8. No legacy Quollnet article URL is linked from the CashflowPot site until the article/slug rewrite is complete.
9. Static-site tests and the full backend test suite are green before merge.
