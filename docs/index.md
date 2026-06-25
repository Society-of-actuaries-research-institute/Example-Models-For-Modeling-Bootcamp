# MBC Production Model

The MBC Production Model is a "production" quality illustration for the SOA
Modeling Bootcamp. It shows how an actuarial model can be organized as
maintainable software with a desktop interface, command-line entry point,
automated tests, documentation, and Excel output.

The model projects stochastic mortality cash flows for annuity-style policies.
It reads policy records and assumptions from an Excel workbook, projects whether
each policy is alive or dead in each scenario and year, summarizes cash flows,
calculates present values, and writes output tables and charts.

## Purpose

The purpose of this project is teaching. It helps students compare three stages
of model evolution:

| Stage | File or folder | Role |
|---|---|---|
| Excel prototype | `Prototype_model.xlsm` | Spreadsheet-first exploration of the model idea. |
| Python R&D script | `RnD_model.py` | Simple Python version of the model logic. |
| Production model | `src/mbc_model/` | Structured software version with UI, tests, docs, and reusable APIs. |

The production model is not production software in the business-use sense. It is
an illustration of production-style engineering practices.

## What The Model Does

At a high level, the production model:

1. Loads an `.xlsx` input workbook.
2. Reads inforce policy records, model parameters, mortality tables, projection
   scales, random-number settings, and reporting selections.
3. Calculates cumulative survival probabilities by policy and projection year.
4. Runs stochastic cash flow projections by scenario.
5. Calculates present values and dashboard statistics when requested.
6. Writes a timestamped Excel output workbook.
7. Displays input previews, output tables, charts, and a run log in the desktop
   UI.

```text
Input Workbook -> Calculations -> Output Workbook and Desktop UI
```

## Important Limitations

This model is a classroom artifact. It may contain mistakes, and it deliberately
uses simplified calculations.

Do not use this model for real pricing, valuation, reserving, financial
reporting, regulatory filings, or business decisions.

Major limitations include:

| Area | Limitation |
|---|---|
| Actuarial scope | Mortality is the only decrement modeled. |
| Product scope | Benefits are simplified annual payments while alive. |
| Assumptions | Sample assumptions are for class use, not real experience studies. |
| Governance | The project demonstrates controls but has no real business approval process. |
| Validation | Tests support classroom confidence, not professional actuarial certification. |
| Data | Input workbooks are assumed to follow the sample layout. |

## Documentation Map

| Page | Use it for |
|---|---|
| Actuarial Calculations | Understand the formulas and variable names used in code. |
| Install & Run | Install the project and run it from the UI, command line, or Python. |
| Inputs & Outputs | Understand workbook formats, output sheets, and display limits. |
| Governance & Limitations | Understand ASOP 56-style model-risk documentation. |
| Testing & Sign-Offs | Understand test coverage, validation evidence, and sample class sign-offs. |
| License | Review project and third-party dependency licenses. |
| API Reference | Inspect the production Python modules and docstrings. |

## ASOP 56 Framing

This documentation borrows structure from
[ASOP 56, Modeling](https://www.actuarialstandardsboard.org/asops/modeling-3/):
intended purpose, intended users, model structure, data and assumptions, model
risk, testing, governance, limitations, and disclosures.

Because this project is an educational illustration, the documentation should be
read as ASOP 56-aligned teaching documentation, not as a formal actuarial report.
