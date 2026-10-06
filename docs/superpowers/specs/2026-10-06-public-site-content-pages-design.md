# CashflowPot Public Site Content Pages — Design

Date: 2026-10-06

## Goal

Bring the CashflowPot public website in line with the current product model, add the missing permanent pages, and establish a stable information architecture for product discovery, methodology, support/contact, legal pages, and future educational links.

The public site remains a static site generated from `q_flow/site/`. CashflowPot remains the dominant product brand; Quollnet remains the parent brand. The app continues to live at `/app/` and the Flask API at `/api/`.

## Product Positioning To Preserve

CashflowPot is a focused construction cash-flow simulation and forecasting application for contractors, commercial/project teams, finance teams, lenders and investors.

It is designed to answer financial and commercial questions quickly using a mathematical model of project execution, contract terms and forecasting assumptions. It does not require the user to first create or fully update a detailed resource-loaded programme merely to obtain a cash-flow view.

This must not be positioned as a lesser or simplified version of Primavera P6, MS Project, ERP/accounting, or cost-control software. Those systems solve different problems.

Detailed planning systems primarily describe how work is planned and can provide planned work/cost values by period. CashflowPot focuses on the next commercial layer: how execution, contract terms and forecasting assumptions translate into cash received, cash paid, net cash and funding requirements.

A useful public distinction is:

> Planning software can show when work and cost are expected to occur. CashflowPot models how that execution, together with contract terms and assumptions, is expected to turn into cash.

CashflowPot's value is strongest when the financial decision cannot or should not wait for a detailed planning update.

Important use cases include:

- **Tender / bid stage** — estimate the cash exposure of a prospective project without first creating a detailed resource-loaded tender programme.
- **Bid / no-bid and portfolio capacity** — produce comparable forecasts for several opportunities to understand whether the contractor has sufficient financial capacity to pursue them together.
- **Contractor financing** — prepare a credible project funding requirement and test the effect of contract terms before or during discussions with lenders.
- **Bank / lender review** — reproduce or challenge a contractor's cash-flow assumptions and understand why the lender's forecast differs from the contractor's.
- **Mid-project reforecasting** — create a current cash position when the programme has changed repeatedly and historical activity/resource loading no longer represents the remaining commercial reality well enough for a cash decision.
- **Management what-if analysis** — test the financial effect of payment timing, retention, subcontracting, execution timing and other changes without rebuilding the full programme.
- **Feasibility, budgeting and recovery planning** — obtain the forecast needed for a financial decision from the information currently available.

The key product philosophy remains:

> A forecast designed to be revised.

Supporting message:

> Build the cash-flow view needed for the decision now, then revise it as the project changes.

The public site must distinguish **contract terms** from **forecasting assumptions**. They are not interchangeable concepts.

Examples of contract terms include payment period, retention, advance payment/recovery and Defects Liability Period (DLP). Examples of assumptions include WIEB percentage, execution curve/timing shape, subcontracted share where not already contractually fixed, and other forecast inputs used to simulate expected behavior.

Public wording should therefore prefer phrases such as **contract terms and assumptions**, **commercial terms and assumptions**, or **execution assumptions and contract terms**, depending on context. Avoid describing all model inputs as assumptions.

## Current Product Model That Public Content Must Reflect

The current public pages still describe the original activity-linked inflow calculation as though it were the only method. That is now outdated.

CashflowPot supports two project inflow methods.

### Independent contract curve — default and recommended

New scenarios default to an independent contract-value curve.

- Project duration is derived from the activity schedule.
- Contract value is distributed over that duration using either an S-curve or a linear distribution.
- The S-curve can be back-loaded, balanced or front-loaded.
- New fast scenarios default to a balanced S-curve.
- Client-side contract terms and forecasting assumptions are applied after the underlying contract-value distribution is generated.

The UI and public site must not expose backend field names such as `use_independent_inflow_curve` or `inflow_curve_skew`.

### Activity-linked inflow — alternative

The existing method remains available.

- Activity work/cost distributions are combined.
- The combined profile is scaled proportionally to the contract value.
- Main-contract terms and assumptions are then applied.

This method should be described as an alternative for users who want contract inflow to follow the activity execution profile.

### Outflow behavior

Outflow remains activity-based under both inflow methods.

Activities define execution cost, timing and project duration. Each activity can be linear or curved and can be split between direct/self-performed and subcontracted work. Subcontracted work follows its own contract/commercial terms and forecast assumptions.

### Terminology

Public site wording must match the current app:

- `Work in Excess of Billings (WIEB)` — not Billing Deferral.
- `Payment period` — not Payment Delay or Time for Payment in UI-oriented descriptions.
- `Defects Liability Period (DLP)`.
- `Independent contract curve` and `Activity-linked inflow` for the two inflow methods.
- Use `Back-loaded`, `Balanced`, and `Front-loaded` rather than exposing the numeric skew parameter to normal users.
- Distinguish `contract terms` from `assumptions` rather than grouping all model inputs under one label.

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

The homepage should present CashflowPot as a purpose-built construction cash-flow decision tool, not as a smaller planning package.

Primary messages:

- simulate construction cash flow from execution assumptions, contract terms and commercial assumptions;
- answer funding and cash-position questions quickly without waiting for a detailed programme creation or update;
- useful for tendering, feasibility, bid/no-bid, portfolio capacity, budgeting, financing, lender review and execution reforecasting;
- activities define execution timing/cost while contract inflow can be modeled independently or linked to execution.

The homepage should not become a technical methodology page.

Required corrections:

- remove wording that implies activities always drive contract value/earned value;
- describe the independent contract curve as the normal/default method;
- mention that a new scenario can be created quickly using sensible defaults, including a balanced S-curve;
- make the distinction between planned work/cost and commercial cash flow clear without attacking or diminishing planning applications;
- keep Excel export, funding requirement, peak negative cash, scenario comparison and lifecycle use cases prominent;
- retain the statement that AI-assisted project setup is in development and that the CashflowPot calculation engine remains responsible for the forecast.

A useful homepage message is:

> Turn project execution, contract terms and assumptions into a cash-flow forecast — without waiting for a detailed programme update.

### How it works (`/how-it-works/`)

This page is the practical product walkthrough.

Recommended structure:

1. **Define the project**
   - project name/description;
   - contract value;
   - known main-contract terms;
   - forecasting assumptions where needed.

2. **Set the inflow forecast method**
   - Independent contract curve — recommended/default;
   - Activity-linked inflow — alternative;
   - fast setup uses a balanced S-curve without requiring the user to configure everything manually.

3. **Build the activity forecast**
   - activity timing;
   - estimated cost;
   - direct/subcontracted split;
   - linear or S-curve work timing.

4. **Apply contract terms and assumptions**
   - client advance and recovery;
   - WIEB;
   - retention;
   - payment period;
   - DLP;
   - subcontract-specific commercial terms and assumptions.

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

It should also explain that CashflowPot is useful even when a detailed programme exists: the programme can inform execution timing, while CashflowPot provides a focused commercial simulation layer for current cash decisions.

### Methodology (`/methodology/`)

This page becomes the canonical public explanation of the model.

The opening philosophy remains:

> A forecast designed to be revised.

The methodology should explain that the engine separates three concepts:

1. **Execution model** — when cost/work is expected to occur.
2. **Contract terms and forecasting assumptions** — how execution is converted into billings, receipts and payments.
3. **Cash position** — inflow, outflow, net cash, cumulative balance and financing requirement.

This is the central distinction between a time-phased cost/work view and a commercial cash-flow forecast.

#### Main-contract inflow section

Explain the two supported methods explicitly.

**Independent contract curve — default**

- determine scenario duration from the activity schedule;
- distribute contract value across that duration using an S-curve or linear distribution;
- allow timing to be back-loaded, balanced or front-loaded for the S-curve;
- apply client-side contract terms and assumptions after the contract-value distribution.

**Activity-linked inflow — alternative**

- combine activity work distributions;
- scale the combined profile to contract value;
- apply the same client contract terms and assumptions afterward.

The public page should explain the concept first; advanced formulas/details can remain under expandable sections where appropriate.

#### Client contract terms and assumptions

Keep and update explanations for:

- advance payment and recovery;
- WIEB;
- retention;
- payment period;
- release at completion;
- DLP release.

Where relevant, identify whether an input normally represents a contract term or a forecasting assumption rather than presenting the entire group as assumptions.

#### Execution/outflow section

Keep activity-based logic:

- activity work distribution;
- direct/self-performed share;
- subcontracted share;
- subcontract contract/commercial terms and assumptions;
- direct cost has no WIEB transformation;
- subcontract WIEB represents performed work not yet billable within the subcontract relationship.

#### Net cash and financing

Retain the clear distinction between inflow, outflow, net cash, cumulative/pre-finance balance and financing charge on negative balances.

#### Position relative to scheduling systems

Do not use a generic `CashflowPot is not a replacement for P6` disclaimer.

Instead explain the difference in purpose:

- scheduling/planning systems can provide a detailed programme and time-phased work/cost information;
- CashflowPot is designed to simulate the commercial cash consequences from execution timing, contract terms and assumptions;
- the tools can complement one another, but CashflowPot does not require a detailed resource-loaded programme when the decision does not justify that effort;
- during tendering or mid-project reforecasting, a mathematical execution profile can provide the right level of input for a financial decision faster than rebuilding detailed loading.

#### Remove obsolete roadmap claim

Remove the current public section describing activity-specific selling value / markup allocation as a planned extension. Per-activity selling price / Schedule-of-Values allocation is not a core CashflowPot roadmap item and should not be advertised publicly.

### About (`/about/`)

Purpose: explain what CashflowPot is and why it exists without duplicating the homepage.

Content:

- larger CashflowPot logo/brand treatment;
- description of CashflowPot as a focused construction cash-flow simulation and forecasting product;
- why it exists: financial decisions often need a credible current forecast faster than creating or rebuilding a detailed cost/resource-loaded programme;
- target users and decision contexts;
- examples such as tendering, financing, lender review, bid/no-bid, portfolio capacity and mid-project reforecasting;
- `A forecast designed to be revised` philosophy;
- explain that detailed planning and CashflowPot solve different questions rather than describing CashflowPot as a lighter substitute;
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
- user responsibility for project data, contract terms and forecasting assumptions entered into the model;
- forecasts are planning estimates/simulations, not guarantees of actual future cash flows;
- users remain responsible for professional, commercial and financing decisions;
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
- public content distinguishes contract terms from forecasting assumptions;
- public positioning describes CashflowPot as a different-purpose commercial cash-flow tool rather than a lesser planning product;
- obsolete wording such as `Billing Deferral` and the planned activity-specific selling-value roadmap section does not remain in current generated pages.

Run focused site-build tests first, then the full backend suite before completion.

## Non-Goals

This pass does not:

- rewrite or edit the four Quollnet articles;
- choose/finalize their replacement slugs;
- add a blog/resources section to CashflowPot;
- add pricing pages;
- add a contact form or support ticket system;
- add a manual public-site theme switcher;
- change the CashflowPot calculation engine;
- change authenticated Flutter UI behavior;
- attempt to replicate detailed planning/scheduling functionality.

## Acceptance Criteria

The work is complete when:

1. Home, How it works and Methodology accurately describe the current two-mode inflow model and the execution/outflow model.
2. The site positions CashflowPot as a purpose-built construction cash-flow simulation/decision tool rather than a lesser alternative to planning software.
3. Public copy consistently distinguishes contract terms from forecasting assumptions.
4. About, Contact, Privacy and Terms are generated and reachable at stable trailing-slash URLs.
5. Privacy and Terms visibly identify `Quollnet` with `Quoll Unipessoal LDA` as the legal operator.
6. The header uses the CashflowPot logo and keeps primary navigation concise.
7. The footer provides Product and Company/support navigation and preserves the existing Quollnet ecosystem attribution.
8. Contact uses the existing Quollnet contact channels and does not invent CashflowPot-specific contact details.
9. The four outdated Quollnet articles are not linked from the CashflowPot site in this pass.
10. The old activity-specific selling-value roadmap claim is removed from Methodology.
11. Focused site tests and the full backend test suite pass before the branch is considered ready for merge.
