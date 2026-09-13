# q_flow

`q_flow` is the authoritative backend and calculation engine for CashFlowPot.

CashFlowPot is a lightweight construction project cash-flow forecasting application. It estimates project cash inflow, outflow, net cash flow, and funding position from project and activity assumptions without attempting to reproduce a fully resource- or quantity-loaded programme.

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
