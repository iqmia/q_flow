# CashflowPot deployment

This document describes the current production layout and the supported build/deploy workflow.

## 1. Public topology

CashflowPot uses one domain with three surfaces:

```text
https://cashflowpot.com/      static public website
https://cashflowpot.com/app/  Flutter web application
https://cashflowpot.com/api/  Flask API through Passenger
```

These are deployed separately even though the public website source and backend source both live in the `q_flow` repository.

## 2. Server source layout

The backend repository is checked out at:

```text
/home/iqmieeuk/q_flow
```

Relevant source paths include:

```text
/home/iqmieeuk/q_flow/q_flow/          Flask package
/home/iqmieeuk/q_flow/site/            public-site source
/home/iqmieeuk/q_flow/site/dist/       generated public-site build
/home/iqmieeuk/q_flow/passenger_wsgi.py
```

The public web root is:

```text
~/www.cashflowpot.com
```

which resolves to the account's CashflowPot domain directory.

A representative production web-root layout is:

```text
~/www.cashflowpot.com/
    index.html
    404.html
    robots.txt
    sitemap.xml
    llms.txt
    assets/
    how-it-works/
    methodology/
    about/
    contact/
    privacy/
    terms/

    app/        Flutter web build
    api/        Passenger mount directory/configuration
```

## 3. Passenger API mount

Namecheap/CloudLinux generated the Passenger configuration under the public `/api` mount:

```apache
PassengerAppRoot "/home/iqmieeuk/q_flow"
PassengerBaseURI "/api"
PassengerPython "/home/iqmieeuk/virtualenv/q_flow/3.9/bin/python"
```

The important distinction is:

- Flask routes are defined internally without `/api`;
- Passenger exposes the Flask application publicly below `/api`.

For example, an internal Flask route `/health` is reached publicly as:

```text
https://cashflowpot.com/api/health
```

Do not add `/api` to every Flask route definition merely because production uses the Passenger base URI.

## 4. Public-site builder

The source-of-truth builder is:

```text
q_flow/site/build_site.py
```

The builder has two stages:

1. `build_site()` creates a clean static build in `site/dist/` by default.
2. `publish_site()` publishes only the static-site-owned entries to the production web root.

The build directory is intentionally deleted and recreated on each build. The production web root is **not** deleted.

### Site-owned production entries

The publisher manages only the entries derived from the current public page registry plus public assets and generated discovery files, currently including:

```text
index.html
404.html
robots.txt
sitemap.xml
llms.txt
assets/
how-it-works/
methodology/
about/
contact/
privacy/
terms/
```

Before copying a managed entry, the publisher replaces that entry only.

It does **not** remove unrelated production entries such as:

```text
app/
api/
```

This preservation is a deployment invariant. Do not change the builder to delete the entire production web root.

### Search and AI discovery files

`build_site.py` generates three root-level discovery files from the current public-site configuration:

- `robots.txt` — allows public crawling, disallows `/api/`, keeps `/app/` crawlable, explicitly permits `OAI-SearchBot`, and references the sitemap;
- `sitemap.xml` — contains only canonical indexable public pages and excludes `/app/`, `/api/`, assets, and `404.html`;
- `llms.txt` — provides a concise supplementary map of CashflowPot, its canonical explanatory pages, the application surface, and its relationship to Quollnet.

The Flutter application at `/app/` is intentionally **crawlable but non-indexable**. Its own HTML shell supplies `noindex, follow`, so `robots.txt` must not block crawlers from fetching `/app/`. The Passenger API at `/api/` is not a discovery surface and is disallowed in `robots.txt`.

## 5. Production public-site deployment

On the production server, the normal public-site update is:

```bash
cd ~/q_flow
git pull
python site/build_site.py
```

With no flags, the command:

1. builds the site into `site/dist/`;
2. verifies that the production web root already exists;
3. verifies that the generated build contains all managed entries; and
4. publishes those managed entries to `~/www.cashflowpot.com`.

If the production web root does not exist, publishing fails instead of creating an unexpected directory.

## 6. Local public-site build

For local development, use:

```bash
python site/build_site.py -l
```

or:

```bash
python site/build_site.py --local
```

Local mode builds `site/dist/` only. It does not look for or modify `~/www.cashflowpot.com`.

A simple local preview can be started with:

```bash
python -m http.server 8000 --directory site/dist
```

### App-owned icons during local preview

The public site reuses production assets such as:

```text
/app/favicon.png
/app/icons/Icon-192.png
/app/icons/quollnet_logo_transp.webp
/app/icons/facebook.png
```

A server that exposes only `site/dist/` does not have `/app/`, so those images can be missing in the simple local preview. In production, `/app/` is deployed beside the static site under the same domain and the paths resolve normally.

Do not duplicate app assets into the static-site build solely to make this limited preview mode self-contained unless the deployment architecture is deliberately changed.

## 7. Shared icons and separate manifests

CashflowPot keeps one physical web icon set, owned by the Flutter web application and deployed below:

```text
https://cashflowpot.com/app/icons/
```

The public site references those same icons rather than storing duplicate copies in `q_flow/site/static/`.

There are intentionally two manifests because the public website and Flutter application have different start URLs and responsibilities:

```text
https://cashflowpot.com/assets/manifest.json   public website manifest
https://cashflowpot.com/app/manifest.json      Flutter application manifest
```

The public website manifest source is:

```text
site/static/manifest.json
```

`build_site.py` copies the complete `site/static/` tree into `site/dist/assets/`, so the manifest is built and published automatically as `/assets/manifest.json`.

The public manifest uses `start_url` and `scope` `/` and references the existing Flutter icons through absolute `/app/icons/...` URLs. The Flutter manifest remains owned by the `iqmia/cashflowpot` repository and applies to `/app/`.

The shared public-site template also uses the Flutter-owned favicon at `/app/favicon.png` and Apple touch icon at `/app/icons/Icon-192.png`.

## 8. Flutter app deployment

The Flutter web application is produced from the separate `iqmia/cashflowpot` repository and deployed under:

```text
https://cashflowpot.com/app/
```

`site/build_site.py` does not build, delete, or publish the Flutter app.

The `/app/` directory must therefore be preserved when updating the public site. The app shell is intentionally shareable while remaining non-indexable through its `noindex, follow` metadata.

When Flutter assets change, rebuild/deploy the Flutter application using its own repository workflow.

## 9. Backend deployment

The Flask backend runs from the `q_flow` checkout referenced by `PassengerAppRoot`.

A backend update generally involves updating the repository and then ensuring Passenger is using/restarting the updated application according to the hosting workflow.

The public-site publisher does not restart Passenger and does not deploy the Flutter app.

Keep these responsibilities separate:

```text
site/build_site.py     static public website
Flutter build/deploy   /app/
Passenger/q_flow       /api/
```

## 10. Environment and secrets

Production configuration reads application secrets from the server environment/config files used by `q_flow` (currently `env.json` through the Config loader).

Secrets such as application secrets, private credentials, mail credentials, and signing material must remain outside Git.

The repository may document configuration key names, but must never contain real production secret values.

See [`reference/security.md`](reference/security.md) for the QAuth/JWT configuration contract.

## 11. Database and storage

The current backend configures its SQLite database at:

```text
<STORAGE_PATH>/q_flow.db
```

The production `STORAGE_PATH` is currently configured within the q_flow server storage area.

Treat the database and any stored project files as persistent server data. A repository pull or public-site build must not overwrite them.

## 12. Deployment checks

After a public-site deployment, check at minimum:

```text
https://cashflowpot.com/
https://cashflowpot.com/how-it-works/
https://cashflowpot.com/methodology/
https://cashflowpot.com/contact/
https://cashflowpot.com/robots.txt
https://cashflowpot.com/sitemap.xml
https://cashflowpot.com/llms.txt
https://cashflowpot.com/assets/manifest.json
https://cashflowpot.com/assets/images/cashflowpot-og.webp
https://cashflowpot.com/app/
https://cashflowpot.com/api/health
```

Also confirm that shared `/app/icons/...` images and `/app/favicon.png` resolve on public pages that use them, and that `/app/` still exposes `noindex, follow` rather than being blocked by the public robots file.

After backend changes, run the backend test suite before deployment where practical:

```bash
pytest
```

For site-only local verification:

```bash
python site/build_site.py -l
python -m unittest tests.test_site_build tests.test_public_manifest -v
```

## 13. Deployment rules

1. `site/dist/` is generated output and is not committed.
2. Normal `python site/build_site.py` means **build + production static-site publish**.
3. `-l/--local` means **build only**.
4. Never point a clean/delete operation at the entire production web root.
5. `/app/` and `/api/` are not owned by the public-site publisher.
6. Passenger owns the public `/api` prefix; Flask route definitions stay internally unprefixed.
7. The public website may reuse `/app/icons/...` and `/app/favicon.png` because `/app/` and the static site share the production domain.
8. Keep one physical icon set under `/app/`, but separate public-site and Flutter manifests because their start URLs and scopes differ.
9. `robots.txt`, `sitemap.xml`, and `llms.txt` are generated site-owned root files; `/app/` stays crawlable/non-indexable and `/api/` stays outside discovery.
10. Server secrets and persistent data are not source-controlled deployment artifacts.

Last reviewed: 7 October 2026.
