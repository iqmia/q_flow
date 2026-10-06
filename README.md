# q_flow

`q_flow` is the authoritative backend and calculation engine for CashFlowPot, and it also contains the source/build foundation for the public CashflowPot website.

CashFlowPot is a lightweight construction project cash-flow forecasting application. It estimates project cash inflow, outflow, net cash flow, and funding position from project and activity assumptions without attempting to reproduce a fully resource- or quantity-loaded programme.

## Public deployment

CashflowPot is split into three public surfaces:

```text
cashflowpot.com/      static public website generated from site/
cashflowpot.com/app/  Flutter application from iqmia/cashflowpot
cashflowpot.com/api/  this Flask application mounted by Passenger
```

Passenger mounts the Flask app at `/api`, while Flask routes remain rooted internally at `/`. For example, the internal health route `/health` is deployed as:

```text
GET https://cashflowpot.com/api/health
```

The internal repository and Python package remain named `q_flow`.

## Public website source

The public website is authored under `site/` with shared Jinja templates and CSS, then generated as static files for deployment. Flask does not render ordinary public pages at request time.

Build the static site with:

```bash
python site/build_site.py
```

The default output is `site/dist/`. Generated output is ignored by Git and should not be committed.

Individual public pages are added to the static builder only after their content and layout are reviewed.

## Project model

A project is identified by a QAuth Unit. Each QAuth Unit can own multiple independent local cash-flow scenarios, such as a base forecast, tender forecast, current forecast, or recovery scenario.

Each cash-flow scenario owns its activities and commercial assumptions. The backend recalculates the project snapshot from active activities and is authoritative for the financial calculation.

## Calculation documentation

The canonical reference for terminology, formulas, timing conventions, assumptions, validation rules, and test invariants is:

[`documentation/cashflow_model.md`](documentation/cashflow_model.md)

Code, clients, exports, and future AI-assisted project setup should follow that document rather than duplicating calculation assumptions independently.

## Other documentation

- [`documentation/security.md`](documentation/security.md) — security notes.
- `docs/superpowers/specs/` — implementation/design specifications. These describe development decisions and are not the authoritative cash-flow formula reference.
