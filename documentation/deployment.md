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

## 3. API runtime

Gunicorn runs the Flask application from the repository `wsgi.py` entrypoint and listens only on loopback:

```text
127.0.0.1:5002
```

The service is managed by systemd as:

```text
cashflowpot-qflow.service
```

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

The public site reuses selected Flutter-owned assets through absolute `/app/...` paths, including the favicon and icons. The public site and Flutter app therefore share the production domain but remain separate deployment artifacts.

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
systemctl restart cashflowpot-qflow
systemctl status cashflowpot-qflow
```

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

It is not committed and should be readable only by the application account. Production secrets, mail credentials, QAuth secrets, and database credentials must remain outside Git.

The main runtime database setting is:

```text
DATABASE_URL
```

The production value uses PostgreSQL through psycopg. Do not print or commit the full connection URL because it includes credentials.

## 11. Database and storage

Production uses PostgreSQL. SQLAlchemy takes the connection from `DATABASE_URL`.

The production application storage directory is:

```text
/home/cashflowpot/q_flow/main_storage
```

If `DATABASE_URL` is absent, q_flow can still fall back to SQLite for local/test-compatible operation, but production should use PostgreSQL.

Persistent database data and stored project files are not deployment artifacts and must never be overwritten by `git pull` or the public-site builder.

## 12. Deployment verification

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
systemctl status cashflowpot-qflow
```

## 13. Deployment rules

1. `site/dist/` is generated output and is not committed.
2. `python site/build_site.py` means build + publish to `/home/cashflowpot/public_html`.
3. `-l/--local` means build only.
4. Never clean/delete the entire Virtualmin document root during a site publish.
5. `/app/` is owned by the Flutter deployment and must be preserved.
6. Apache owns the public `/api/` mapping; Flask routes remain internally unprefixed.
7. Gunicorn listens on loopback only and is managed by `cashflowpot-qflow.service`.
8. Production uses PostgreSQL via `DATABASE_URL` and file storage under `main_storage`.
9. `robots.txt`, `sitemap.xml`, and `llms.txt` are generated public-site files; `/app/` stays crawlable/non-indexable and `/api/` stays outside discovery.
10. Server secrets and persistent data are not source-controlled deployment artifacts.

The Activity-mode, Scheduled Cost, financing-facility, and Excel-report updates do not change this deployment topology.

Last reviewed: 14 October 2026.
