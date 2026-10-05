# CashflowPot Site and API Foundation Design

Date: 2026-10-06

## Goal

Make `iqmia/q_flow` the home of both the CashflowPot backend API and the source for the public CashflowPot website, while keeping the deployed public website static and fast.

The deployed public surface is:

- `https://cashflowpot.com/` — static public website
- `https://cashflowpot.com/app/` — Flutter application
- `https://cashflowpot.com/api/` — Passenger/Flask backend

The internal Python package may remain named `q_flow`; this work does not rename the package or repository.

## Deployment Model

### Public website

The website is authored with Jinja templates and shared CSS, but generated into static HTML before deployment. LiteSpeed serves the generated files directly; Flask does not render ordinary public pages at request time.

Source lives under `site/` and generated output lives under `site/dist/`. `site/dist/` is not committed.

Proposed source structure:

```text
site/
├── build_site.py
├── templates/
│   └── base.html
├── static/
│   └── css/
│       └── site.css
└── dist/               # generated, gitignored
```

Individual public pages will be added and reviewed one by one after the foundation is in place.

### Flask API

Passenger mounts the existing Flask application at `cashflowpot.com/api`. Flask routes therefore remain rooted internally at `/`; for example an internal `/health` route is publicly available as `/api/health`.

The backend gains one lightweight unauthenticated `GET /health` endpoint returning HTTP 200 and a small JSON payload identifying the service as the CashflowPot API.

Existing business routes are not renamed as part of this foundation work.

The two existing internal `/api` welcome routes in `users.py` and `projects.py` are removed. They are obsolete under the new Passenger mount because they would otherwise appear publicly as `/api/api`.

## Public Site Design System

The public site should look like the same product as the Flutter application, not a separate marketing theme.

### Theme behavior

The public site follows the visitor's operating-system/browser preference through `prefers-color-scheme`. There is no manual theme switcher in the public site initially.

### Core colors

Light:

- Brand orange: `#E89A5B`
- Canvas: `#F7F4EF`
- Surface: `#FFFDFC`
- Primary text / charcoal: `#30322F`
- Border: `#E5DED4`

Dark:

- Canvas: `#181A18`
- Surface: `#20221F`
- Elevated/form surface: `#272A26`
- Border: `#454943`

Semantic colors shared with the Flutter app:

- Inflow / positive: `#79A58D`
- Outflow / negative: `#C9796F`
- Cost: `#7F9FB2`
- Balance, light: `#8D7047`
- Balance, dark: `#CDB58A`

### UI language

- Warm off-white rather than pure white in light mode.
- Restrained borders and shadows.
- Corner radii generally 12–14 px.
- Primary controls approximately 48 px high.
- Bold headings with slightly negative tracking.
- Comfortable reading widths; content should not stretch across very wide displays.
- Mobile-first responsive behavior.
- Use semantic HTML and preserve accessibility contrast/focus states.

### Quollnet relationship

CashflowPot remains the dominant product brand.

Quollnet is shown as the parent ecosystem using restrained attribution such as `A Quollnet product` in shared site chrome and a fuller Quollnet ecosystem reference in the footer/About page. Quollnet branding should not introduce a competing color system into CashflowPot pages.

## Shared Base Template

`site/templates/base.html` will provide the reusable page shell for future pages:

- standard metadata hooks
- responsive viewport
- canonical URL hook
- page title and description blocks
- shared stylesheet
- header/navigation shell
- CashflowPot/Quollnet attribution
- main content block
- footer shell

The foundation should avoid page-specific marketing content. Each page is added later as a separate reviewed step.

## Build Process

`site/build_site.py` will:

1. create/clean `site/dist/`;
2. copy static assets into the output;
3. render only page templates explicitly configured in the build script as pages are added;
4. preserve directory-style URLs by writing pages as `<slug>/index.html`;
5. support root-level special files such as `404.html`, `robots.txt`, and `sitemap.xml` when those pages/files are introduced.

For the initial foundation, the configured page list is empty. Running the build therefore produces a clean `site/dist/` containing the shared static assets but no public content pages. This allows the site shell and build pipeline to be established before page content is reviewed.

## Error and Failure Boundaries

The public static website must continue to serve even if Passenger/Flask, the database, QAuth, or another backend dependency is unavailable.

The Flutter app remains separately deployed under `/app/`.

Dynamic public features added later may call `/api/...`; authenticated dynamic features may be implemented as Flask endpoints such as `/api/ai/...` without changing the static-site model.

## Testing

Foundation verification should cover:

- existing backend test suite remains green;
- `/health` returns HTTP 200 and the expected CashflowPot API identity;
- the old duplicate `/api` welcome endpoints are no longer registered;
- the site build script produces a clean output directory and copies shared static assets;
- `site/static/css/site.css` contains the documented light/dark tokens and a `prefers-color-scheme: dark` rule;
- `site/dist/` is ignored by Git.

## Out of Scope

- Renaming the `q_flow` repository or Python package.
- Changing business API route names.
- Building the Home, How It Works, Methodology, About, Contact, Privacy, or Terms pages in this foundation task.
- Changing the Flutter application, which is handled in the CashflowPot repo.
- Moving QAuth; it remains the Quollnet identity service used by CashflowPot.