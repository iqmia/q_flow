# q_flow

`q_flow` is the authoritative Flask backend and cash-flow calculation engine for **CashflowPot**. It also contains the source/build system for the public CashflowPot website.

CashflowPot turns construction project execution, project costs, contract terms, forecasting assumptions, and financing facilities into project inflow/outflow, funding requirements, financed cash position, and decision KPIs.

## Start here

The current product definition and technical documentation live under:

[`documentation/README.md`](documentation/README.md)

That index explains what CashflowPot is today, how the backend/client/deployment fit together, the Work/Scheduled Cost Activity model, financing facilities, UI terminology, Excel/reporting conventions, detailed formulas/security/file-format references, and approved future directions.

`docs/superpowers/specs/` and `docs/superpowers/plans/` are development/design history, not the current product definition.

## Repository role

This repository owns:

- the Flask API;
- the authoritative Cashflow/Activity calculation engine;
- Work vs Scheduled Cost Activity semantics;
- Independent and Activity-linked client inflow calculations;
- financing-facility calculation and validation;
- canonical scenario summary/KPI values;
- local Cashflow/Activity persistence;
- QAuth project/unit integration;
- portable scenario import handling;
- backend tests; and
- the static public-site source and publisher under `site/`.

The Flutter application is maintained separately in `iqmia/cashflowpot`. Flutter owns user-facing input/presentation, charts, portable export/import UX, and Excel reporting, but the backend remains authoritative for the financial model.

## Current financial model at a glance

Activities have separate category, mode, and distribution concepts:

```text
Activity mode:
  Work
  Scheduled Cost

Work distribution:
  S-curve
  Linear
  Manual
```

Work Activities contribute to physical/cost-loaded execution and Work duration. Scheduled Cost contributes to project cost/outflow and financing need but not client PPC/billed work or Work duration.

The current result presentation is:

```text
PROJECT CASHFLOW
FACILITIES
CASH POSITION
```

See the canonical references for exact formulas and facility sequencing.

## Public surfaces

```text
cashflowpot.com/      static public website generated from site/
cashflowpot.com/app/  Flutter application
cashflowpot.com/api/  q_flow Flask API through Apache + Gunicorn
```

Apache exposes the public `/api/` prefix and reverse-proxies to Gunicorn on `127.0.0.1:5002`; Flask routes remain internally unprefixed.

## Public-site commands

Production/server build + publish:

```bash
python site/build_site.py
```

Local build only:

```bash
python site/build_site.py -l
```

Generated static output is written to `site/dist/` and is not committed. Production publishing targets `/home/cashflowpot/public_html`.

See [`documentation/deployment.md`](documentation/deployment.md) for the Virtualmin/Apache/Gunicorn layout and deployment rules.

## Tests

Run the backend suite with:

```bash
pytest
```

When a change also affects Flutter behavior or shared input/output contracts, run the Flutter repository tests as well.

## Detailed references

- [`documentation/reference/cashflow_model.md`](documentation/reference/cashflow_model.md) — canonical Activity/inflow/outflow/summary calculation model.
- [`documentation/reference/financing_facilities.md`](documentation/reference/financing_facilities.md) — facility draw, repayment, capacity, interest, KPI, and presentation rules.
- [`documentation/reference/cashflow_json_format.md`](documentation/reference/cashflow_json_format.md) — portable scenario format.
- [`documentation/reference/security.md`](documentation/reference/security.md) — QAuth/JWT and Unit authorization.
