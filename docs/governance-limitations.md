# Governance & Limitations

This page frames the production model using documentation concepts from
[ASOP 56, Modeling](https://www.actuarialstandardsboard.org/asops/modeling-3/).
It is ASOP 56-aligned classroom documentation, not a formal actuarial report.

## Intended Purpose

The intended purpose of this model is to illustrate how an actuarial model can
evolve from a prototype to an R&D script and then to production-style software.

The production model demonstrates:

- structured input loading,
- typed model objects,
- vectorized calculation engines,
- Excel output generation,
- a desktop user interface,
- automated tests,
- documentation,
- and version-control-friendly organization.

## Intended Users

| User | Intended use |
|---|---|
| SOA Modeling Bootcamp students | Learn how a model can be engineered into production-style software. |
| Instructors | Demonstrate model structure, testing, documentation, and UI workflows. |
| Developers working on the class project | Extend or maintain the example code. |

No real business user should rely on this model for actuarial decisions.

## Model Structure

The model has three components consistent with ASOP 56 concepts:

| Component | Production implementation |
|---|---|
| Input component | `ExcelLoader` reads `Inforce`, `Parameters`, and `Reporting`. |
| Processing component | `MortalityEngine` and `ProjectionEngine` calculate survival, cash flows, and present values. |
| Results component | `ReportWriter` and the desktop UI present output tables and charts. |

## Assumptions And Simplifications

| Area | Simplification |
|---|---|
| Mortality | Mortality is based on workbook tables and a simple improvement formula. |
| Decrements | Mortality is the only decrement modeled. |
| Benefits | Benefits are annual payments while alive. |
| Timing | Present values use end-of-year discounting. |
| Policy features | No lapses, expenses, taxes, reserves, options, riders, underwriting, or premium flows. |
| Scenario design | Scenarios are random survival outcomes, not a full economic scenario generator. |
| Dependencies | Policy outcomes are driven by separate policy/scenario random numbers; no explicit dependency model is included. |

## Reliance On Data And Assumptions

The model relies entirely on the input workbook. The user is responsible for
the appropriateness of:

- inforce records,
- mortality rates,
- projection scales,
- valuation date,
- last projection year,
- random number mode and seed,
- reporting selections,
- and discount rate.

The production code validates basic input shape and reasonableness, but it does
not certify that assumptions are actuarially appropriate.

## Model Risk

ASOP 56 describes model risk as the risk of adverse consequences from relying on
a model that does not adequately represent that which is being modeled, or from
misuse or misinterpretation. For this project, major model risks include:

| Risk | Example |
|---|---|
| Oversimplified actuarial design | Real annuity or life product behavior is not fully represented. |
| Input misuse | Users may load data that fits the workbook shape but is not appropriate. |
| Misinterpretation | Students may mistake an engineering illustration for a real valuation tool. |
| Implementation defects | The project may contain bugs because it is a teaching artifact. |
| Scale assumptions | Large seeded runs are supported, but the UI is not a full data warehouse. |

## Controls

Current controls include:

| Control | Purpose |
|---|---|
| Version control | Tracks source and documentation changes. |
| Automated tests | Protect core production behavior from regressions. |
| Type checking | Helps catch inconsistent Python interfaces. |
| Linting and formatting | Improves maintainability and readability. |
| Input validation | Catches common workbook shape and value problems. |
| Run log | Preserves a simple history of desktop actions and runs. |
| Timestamped outputs | Avoids overwriting prior output workbooks. |

## Not Appropriate For

This model should not be used for:

| Use | Reason |
|---|---|
| Pricing | Product features and assumptions are too simplified. |
| Valuation | It does not implement real valuation standards or controls. |
| Reserving | It does not model reserves, margins, or reporting requirements. |
| Financial reporting | It lacks formal governance, controls, and sign-off. |
| Regulatory filings | It is not designed or reviewed for regulatory use. |
| Management decisions | Output may be incomplete, simplified, or wrong. |

## ASOP 56 Documentation Checklist

| ASOP 56 theme | Where addressed |
|---|---|
| Intended purpose and users | This page and Home. |
| Model structure | This page and Actuarial Calculations. |
| Input data and assumptions | Inputs & Outputs. |
| Understanding important operations | Actuarial Calculations and API Reference. |
| Known limitations and weaknesses | Home and this page. |
| Model risk mitigation | This page and Testing & Sign-Offs. |
| Testing and output validation | Testing & Sign-Offs. |
| Communications and disclosures | Home, Governance & Limitations, and Testing & Sign-Offs. |

## Change Management

Future patches should update documentation when they change:

- workbook format,
- calculation logic,
- output workbook layout,
- UI behavior,
- tests,
- dependencies,
- or model limitations.
