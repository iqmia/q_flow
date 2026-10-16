# CashflowPot deployment

This document describes the current VPS production layout and supported build/deploy workflow.

## 1. Public topology

CashflowPot uses one domain with three surfaces:

```text
https://cashflowpot.com/      static public website
https://cashflowpot.com/app/  Flutter web application
https://cashflowpot.com/api/  Flask API through Apache reverse proxy
```

The public website source and Flask backend live in `iqmia/q_flow`. The Flutter application lives in `iqmia/cashflowpot`.

## 2. Server layout

Production runs on the iqmia VPS under the Virtualmin account `cashflowpot`.

```text
/home/cashflowpot/q_flow/              backend repository
/home/cashflowpot/q_flow/q_flow/       Flask package
/home/cashflowpot/q_flow/site/         public-site source
/home/cashflowpot/q_flow/site/dist/    generated static build
/home/cashflowpot/q_flow/main_storage/ application file storage
/home/cashflowpot/venv/                Python virtual environment
/home/cashflowpot/public_html/         Virtualmin document root
```

The web root contains the generated public website plus the separately deployed Flutter app under `/app/`.

Generated Excel reports are **not** deployment or storage artifacts. q_flow builds them in memory only when an authorized signed download URL is opened.

## 3. API runtime

Gunicorn runs the Flask application from the repository `wsgi.py` entrypoint and listens only on loopback:

```text
127.0.0.1:5002
```

The service is managed by systemd as:

```text
cashflowpot-qflow.service
```

The `cashflowpot.service` alias can also be used where it has been installed.

Representative unit settings:

```ini
[Service]
User=cashflowpot
Group=cashflowpot
WorkingDirectory=/home/cashflowpot/q_flow
Environment="PATH=/home/cashflowpot/venv/bin"
ExecStart=/home/cashflowpot/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5002 wsgi:app
Restart=always
RestartSec=5
```

Apache/Virtualmin exposes the API under `/api/` and strips that external prefix before forwarding to Flask:

```apache
ProxyPreserveHost On
ProxyPass /api/ http://127.0.0.1:5002/
ProxyPassReverse /api/ http://127.0.0.1:5002/
```

Flask routes therefore remain internally unprefixed. For example, internal `/health` is public at:

```text
https://cashflowpot.com/api/health
```

Both the HTTP and SSL VirtualHost configuration should contain equivalent API proxy behavior; public production traffic is HTTPS.

## 4. Public-site builder

The source-of-truth builder is:

```text
site/build_site.py
```

The builder has two stages:

1. `build_site()` creates a clean static build in `site/dist/` by default.
2. `publish_site()` publishes only static-site-owned entries to `/home/cashflowpot/public_html`.

The build directory is deleted and recreated on each build. The production web root itself is never deleted.

The publisher manages only generated public-site entries such as:

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

It does not own or remove `/app/`. `/api/` is provided by Apache rather than by a physical API directory.

## 5. Production public-site deployment

From the production account:

```bash
cd /home/cashflowpot/q_flow
git pull
source /home/cashflowpot/venv/bin/activate
python site/build_site.py
```

With no flags, the command builds `site/dist/`, validates the generated entries, and publishes them to:

```text
/home/cashflowpot/public_html
```

If the document root does not exist, publishing fails instead of creating an unexpected deployment directory.

For a local build without publishing:

```bash
python site/build_site.py -l
```

A local preview can be started with:

```bash
python -m http.server 8000 --directory site/dist
```

## 6. Search and AI discovery

`build_site.py` generates:

- `robots.txt` — allows public crawling, disallows `/api/`, keeps `/app/` crawlable, explicitly permits `OAI-SearchBot`, and references the sitemap;
- `sitemap.xml` — contains canonical indexable public pages only;
- `llms.txt` — provides a compact map of CashflowPot, its explanatory pages, application surface, and Quollnet relationship.

The Flutter application at `/app/` is crawlable but non-indexable through its own `noindex, follow` metadata. The API at `/api/` is not a discovery surface.

The public site also publishes Open Graph metadata, JSON-LD, and the shared social image `cashflowpot-og.webp`.

## 7. Shared app assets

The public site reuses selected Flutter-owned assets through absolute `/app/...` paths, including icons. The public site and Flutter app therefore share the production domain but remain separate deployment artifacts.

There are intentionally two manifests:

```text
https://cashflowpot.com/assets/manifest.json
https://cashflowpot.com/app/manifest.json
```

The first belongs to the public site; the second belongs to Flutter.

## 8. Flutter app deployment

The Flutter application is built from `iqmia/cashflowpot` and deployed below:

```text
/home/cashflowpot/public_html/app/
```

`site/build_site.py` does not build, delete, or publish the Flutter app. Flutter deployment is handled separately.

## 9. Backend deployment

Backend code is deployed from:

```text
/home/cashflowpot/q_flow
```

A normal backend code update is:

```bash
cd /home/cashflowpot/q_flow
git pull
source /home/cashflowpot/venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart cashflowpot
sudo systemctl status cashflowpot
```

Installing requirements is required when the backend Excel exporter is introduced because q_flow now depends on `XlsxWriter`.

The health check is:

```bash
curl https://cashflowpot.com/api/health
```

Expected response:

```json
{"service":"CashflowPot API","status":"ok"}
```

## 10. Environment and secrets

Production configuration reads `env.json` from:

```text
/home/cashflowpot/q_flow/env.json
```

It is not committed and should be readable only by the application account. Production secrets, mail credentials, QAuth secrets, database credentials, and Flask signing secrets must remain outside Git.

The main runtime database setting is:

```text
DATABASE_URL
```

The backend export feature also uses:

```text
PUBLIC_API_BASE_URL=https://cashflowpot.com/api
EXCEL_EXPORT_TOKEN_TTL_SECONDS=600
EXCEL_LOGO_PATH=/home/cashflowpot/public_html/app/assets/assets/icon/qflow_logo.png
```

`PUBLIC_API_BASE_URL` must be the externally visible API base, not Gunicorn's loopback URL, because Apache strips `/api/` before requests reach Flask. `EXCEL_EXPORT_TOKEN_TTL_SECONDS` defaults to 600 seconds when omitted.

`EXCEL_LOGO_PATH` is optional. Its default is the deployed Flutter asset path shown above, so the backend report uses the same CashflowPot logo as the application. If the file is absent, Excel generation continues without a logo rather than failing the export.

The signed Excel token uses the Flask `SECRET_KEY`; changing that key invalidates outstanding download URLs. The URL is a short-lived bearer capability, so it should not be logged or shared beyond the intended recipient.

The production database value uses PostgreSQL through psycopg. Do not print or commit the full connection URL because it includes credentials.

## 11. Stateless Excel export

The public flow is:

```text
POST https://cashflowpot.com/api/cashflow/<cashflow_id>/excel-export
  Authorization: Bearer <normal CashflowPot app/unit token>

        -> filename
        -> download_url
        -> expires_at

GET <download_url>
        -> verify signed token
        -> confirm active cashflow + exact project/unit match
        -> load current authoritative scenario
        -> load the deployed CashflowPot report logo when available
        -> generate XLSX in memory
        -> stream attachment
        -> release memory
```

The GET route intentionally does not require an Authorization header because possession of the short-lived signed URL is the download authorization. The token contains the cashflow identity, project/unit identity, project name, purpose/audience, and expiry.

No `.xlsx` file, export database row, background cleanup task, or temporary report directory is created. Reopening a valid URL can regenerate the workbook until the token expires.

## 12. Database and storage

Production uses PostgreSQL. SQLAlchemy takes the connection from `DATABASE_URL`.

The production application storage directory is:

```text
/home/cashflowpot/q_flow/main_storage
```

If `DATABASE_URL` is absent, q_flow can still fall back to SQLite for local/test-compatible operation, but production should use PostgreSQL.

Persistent database data and stored project files are not deployment artifacts and must never be overwritten by `git pull` or the public-site builder. Excel exports do not add persistent files to this directory.

## 13. Deployment verification

Before deployment, run the backend suite locally:

```bash
pytest
```

For a site-only local check:

```bash
python site/build_site.py -l
python -m unittest tests.test_site_build tests.test_public_manifest -v
```

After deploying, verify at minimum:

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

Also confirm the systemd service is running:

```bash
systemctl status cashflowpot
```

For Excel, create a signed URL through the authenticated POST route and open it before expiry. Confirm the response MIME type is XLSX, the workbook contains the CashflowPot logo when the Flutter asset is deployed, and no `.xlsx` file appears under `main_storage`.

## 14. Deployment rules

1. `site/dist/` is generated output and is not committed.
2. `python site/build_site.py` means build + publish to `/home/cashflowpot/public_html`.
3. `-l/--local` means build only.
4. Never clean/delete the entire Virtualmin document root during a site publish.
5. `/app/` is owned by the Flutter deployment and must be preserved.
6. Apache owns the public `/api/` mapping; Flask routes remain internally unprefixed.
7. Gunicorn listens on loopback only and is managed by the CashflowPot q_flow systemd service.
8. Production uses PostgreSQL via `DATABASE_URL` and file storage under `main_storage`.
9. `robots.txt`, `sitemap.xml`, and `llms.txt` are generated public-site files; `/app/` stays crawlable/non-indexable and `/api/` stays outside discovery.
10. Server secrets and persistent data are not source-controlled deployment artifacts.
11. Excel download URLs are short-lived signed capabilities; generated workbooks are in-memory only and must not be added to persistent storage.
12. `PUBLIC_API_BASE_URL` must stay aligned with the externally visible Apache `/api` URL.
13. The Excel exporter reads the existing deployed Flutter logo asset; it does not copy that image into q_flow storage.

The Activity-mode, Scheduled Cost, financing-facility, and backend Excel-report updates do not change the core CashflowPot deployment topology.

Last reviewed: 17 October 2026.
