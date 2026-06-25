# Testing & Sign-Offs

This page summarizes the testing and review evidence for the production model.
It is written in the spirit of ASOP 56 model documentation, but it is not a
formal actuarial sign-off.

## Current Test Suite

The production model includes automated tests for the main code areas.

| Area | Example test focus |
|---|---|
| Data loading | Workbook parsing, required fields, validation errors. |
| Mortality engine | Cumulative survival and mortality improvement calculations. |
| Projection engine | Scenario projection, random number handling, present values. |
| Reporting | Output workbook sheets and charts. |
| Desktop UI bridge | Browse, run status, output preview, input editing helpers. |
| Integration | End-to-end production runs and R&D parity checks. |

Common test commands:

```bash
pytest
pytest -m "not slow"
```

## Validation Matrix

| ASOP-style concern | Evidence in this project |
|---|---|
| Inputs reconcile to workbook | Loader tests check required sheets, columns, and scalar values. |
| Formula logic is implemented as intended | Engine tests check mortality, projection, and PV behavior. |
| Output workbooks are created correctly | Reporting tests inspect generated workbook sheets and charts. |
| UI does not freeze during model runs | Bridge tests use background-run behavior and status polling. |
| Graph behavior follows reporting settings | Chart tests verify requested and not-requested graph paths. |
| Small sample runs complete end to end | Integration tests run sample workbooks through the production runner. |
| R&D and production are aligned for teaching | Parity tests compare R&D-style logic with production results. |

## Manual Checks

Recommended manual checks before using the model in class:

| Check | Expected result |
|---|---|
| Launch desktop UI | `python -m mbc_model.ui` opens the app. |
| Load small workbook | `Input 10 pol 25 scen table.xlsx` previews successfully. |
| Run small workbook | Output workbook is created in `outputs/`. |
| Open output workbook | Excel opens the generated file. |
| Review charts | Charts appear when `Create graph? = Yes`. |
| Graph not requested | UI indicates that the graph was not requested. |
| Save edited input copy | UI saves a new `.xlsx` copy without overwriting the original. |

## Sample Class Sign-Offs

The following rows are illustrative examples for class discussion. They are not
real actuarial opinions and do not grant approval for real-world use.

| Review area | Sample reviewer | Sample status | Notes |
|---|---|---|---|
| Calculation walkthrough | Instructor / class reviewer | Demonstrated | Formulas reviewed against code variable names. |
| Input/output format | Instructor / class reviewer | Demonstrated | Sample workbook layout reviewed. |
| Automated tests | Developer / class reviewer | Demonstrated | Test suite run for classroom version. |
| User interface | Instructor / class reviewer | Demonstrated | Browse, run, output, and run log workflow reviewed. |
| ASOP 56 documentation | Instructor / class reviewer | Demonstrated | Documentation structure reviewed for teaching purposes. |

## Future Patch Review Register

Use this table as a template when patches materially change the production
model.

| Version or patch | Change reviewed | Tests run | Reviewer | Status | Date |
|---|---|---|---|---|---|
| Example future patch | Update calculation logic | `pytest -m "not slow"` | TBD | TBD | TBD |
| Example future patch | Update workbook format | `pytest tests/data tests/ui` | TBD | TBD | TBD |

## Known Testing Gaps

| Gap | Why it matters |
|---|---|
| No independent actuarial certification | The model is a class illustration. |
| Limited real-world assumption review | Input assumptions are sample classroom assumptions. |
| No formal performance benchmark in docs | Large inputs are available, but classroom runs should start small. |
| No regulatory review | The model is not intended for filings or financial reporting. |

## Suggested Release Checklist

Before a classroom release or patch:

1. Run `pytest -m "not slow"`.
2. Run a small desktop UI model run.
3. Open the generated output workbook.
4. Confirm documentation still matches inputs, outputs, and formulas.
5. Record any important limitations or known issues.
