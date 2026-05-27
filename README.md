# MBC "Production" Model Example

A stochastic mortality and cash-flow projection model for the SOA Modeling Bootcamp 2026,
built to illustrate what production-grade actuarial software looks like in practice.

> **Note:** This project may contain bugs and deliberate simplifications. The goal is to
> demonstrate the technologies and engineering patterns used in production software — not
> to deliver a perfectly polished, bug-free system.

---

## What This Project Is

This is the third model in a three-part series for the SOA Modeling Bootcamp 2026. All
three models solve the same actuarial problem — computing the stochastic present value of
cash flows for a portfolio of annuities under mortality uncertainty — but each represents a
different level of engineering sophistication:

1. **Excel Prototype** — [link placeholder] — the fastest way to explore the math; familiar
   to all actuaries; limited in scale and shareability.
2. **Python R&D Script** — [link placeholder] — procedural Python code that validates the
   math and could be used to price a first deal; developer-friendly, minimal tooling.
3. **This project (Production Software)** — a software engineering demonstration: designed
   UI, automated testing, type safety, CI/CD, and documentation.

The model uses Monte Carlo simulation to project mortality outcomes and benefit payments
across thousands of policies and scenarios, then computes present values and summary
statistics.

---

## Features

- **Two projection modes** — pre-loaded random numbers (fully reproducible results) or
  seeded RNG (scalable to any portfolio size)
- **Vectorised NumPy engine** — processes entire policy portfolios in batch; no Python
  loops over individual policies
- **Desktop GUI** — native window with file browsing, inline workbook editing, live run
  progress, embedded result previews, and a persistent run log
- **CLI** — one command to run the model from a terminal; suitable for scripting and
  automation
- **Programmatic API** — import and call `run()` directly from other Python code
- **Excel output** — up to four result sheets (Policy, Scenario, Total, Dashboard) with
  embedded charts
- **Engineering rigour** — `mypy --strict` type checking, `black` formatting, `pylint`
  linting, `pytest` with ≥90% coverage, GitHub Actions CI/CD

---

## Requirements

- Python 3.11 or newer
- Windows 10+ or macOS 12+
- ~300 MB disk space for Python dependencies

---

## Installation

### Windows

Open **Command Prompt** or **PowerShell** and run:

```cmd
git clone https://github.com/<your-org>/mbc-production-model-example.git
cd mbc-production-model-example
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

To also install development tools (tests, type checking, documentation):

```cmd
pip install -e ".[dev]"
```

> **Tip:** If `python` is not recognised, try `py` instead. You can check your Python
> version with `python --version` — it must be 3.11 or newer.

### macOS

Open **Terminal** and run:

```bash
git clone https://github.com/<your-org>/mbc-production-model-example.git
cd mbc-production-model-example
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

To also install development tools:

```bash
pip install -e ".[dev]"
```

> **Note:** The desktop GUI uses WebKit, which is built into macOS — no extra system
> packages are required. On older macOS versions, you may need to install Xcode Command
> Line Tools (`xcode-select --install`) before running `pip install`.

---

## Usage

### A. Desktop GUI (recommended for interactive use)

The desktop GUI is the easiest way to load a workbook, configure a run, view results, and
keep a log of past runs.

```bash
python -m mbc_model.ui
```

**Step-by-step walkthrough:**

1. Click **Browse** to open a file picker and select one of the sample workbooks from the
   `inputs/` folder (start with `Input 10 pol 25 scen table.xlsx`).
2. The **Preview** panel shows the loaded policies, parameters, and random numbers.
3. Optionally edit any field inline and click **Save As** to save a modified workbook.
4. Click **Run Model** — elapsed time is shown live while the model runs in the background.
5. When the run finishes, click **View Results** to preview output sheets, or **Open File**
   to open the Excel workbook in your default application.
6. The **Run Log** tab keeps a record of every run with date, time, and runtime.

![Desktop GUI](docs/images/gui-screenshot.png)
*Screenshot placeholder — add `docs/images/gui-screenshot.png` to display a screenshot here.*

### B. Command-line interface

Useful for scripting, batch processing, or when you want to run the model without opening
a window.

```bash
# Run using the default input workbook (10 policies, 25 scenarios)
python -m mbc_model

# Run with a specific input file
python -m mbc_model "inputs/Input 50k pol 10k scen seed.xlsx"
```

The output is written to `outputs/results_YYYYMMDD_HHMMSS.xlsx` and the path is printed
when the run completes.

### C. Programmatic API

You can call the model directly from your own Python code:

```python
from pathlib import Path
from mbc_model.runner import run

output_path = run(Path("inputs/Input 10 pol 25 scen table.xlsx"))
print(f"Results written to: {output_path}")
```

---

## Input Format

Inputs are Excel (`.xlsx`) workbooks with three sheets:

| Sheet | Contents |
|-------|----------|
| **Inforce** | One row per policy: Policy #, Year of Birth, Gender (M/F), Annual Benefit |
| **Parameters** | Valuation date, last projection year, mortality rates by age and gender, mortality improvement scales, and random number source (`Table` or `Seed`) |
| **Reporting** | Flags for which output sheets to create, discount rate, and the specific policy/scenario IDs to detail |

### Sample workbooks

Four sample workbooks are included in the `inputs/` folder:

| File | Policies | Scenarios | Random numbers | Approx. runtime |
|------|----------|-----------|----------------|-----------------|
| `Input 10 pol 25 scen table.xlsx` | 10 | 25 | Pre-loaded table | ~4 s |
| `Input 10 pol 25 scen seed.xlsx` | 10 | 25 | Seeded RNG | ~4 s |
| `Input 50k pol 10k scen seed.xlsx` | 50,000 | 10,000 | Seeded RNG | ~3 min |
| `Input 100k pol 10k scen seed.xlsx` | 100,000 | 10,000 | Seeded RNG | ~8 min |

Start with the 10-policy workbook to verify your installation is working correctly.

---

## Output Format

Each run produces a timestamped Excel workbook in the `outputs/` folder. The workbook
contains up to four sheets, controlled by the **Reporting** sheet in the input:

| Sheet | Contents |
|-------|----------|
| **Policy Results** | Year-by-year mortality and cash-flow detail for one selected (policy, scenario) pair |
| **Scenario Results** | Annual cash flows for every policy in one selected scenario, with an optional chart |
| **Total Results** | Annual cash flows summed across all policies, one column per scenario |
| **Dashboard Results** | Present value summary statistics (mean, median, std dev, percentiles) with an optional line chart |

![Sample dashboard output](docs/images/dashboard-screenshot.png)
*Screenshot placeholder — add `docs/images/dashboard-screenshot.png` to display a chart here.*

---

## Project Structure

```
src/mbc_model/
  runner.py          # Orchestrator: load → mortality → projection → write
  data/              # Typed data models (PolicyRecord, MortalityTable, etc.) & Excel loader
  engine/            # MortalityEngine (builds tPx matrix) & ProjectionEngine (stochastic + PV)
  reporting/         # ReportWriter (Excel output) & chart generators (matplotlib)
  ui/                # Desktop GUI — pywebview launcher, Python↔JS bridge, preview & editor
inputs/              # Sample input workbooks (included; safe to modify)
outputs/             # Generated result workbooks (created automatically on first run)
tests/               # Unit tests + integration tests (≥90% coverage)
docs/                # MkDocs documentation site source
```

---

## Development

With `pip install -e ".[dev]"` installed:

```bash
# Run the test suite
pytest

# Run tests, skipping the slow 100k-policy scale test
pytest -m "not slow"

# Type checking (strict)
mypy src

# Lint
pylint src

# Format code
black src tests

# Build and serve the documentation site locally
mkdocs serve
```

---

## Three-Model Comparison

| Feature | Excel Prototype | Python R&D Script | Production Software |
|---------|----------------|-------------------|---------------------|
| Calculations | ✓ | ✓ | ✓ |
| Performance | Slow | Fast | Fastest |
| User Interface | Spreadsheet | Command line | Designed UI |
| Version control | None | Git | DevOps |
| Testing | None | Against Excel | Automated test bank |
| Documentation | Comments in cells | Comments in code | Website and comments in code |
| Governance | None | Version control | Version control and audit trail |
| Build time | Very fast | Moderate | Significant investment |
| Shareability | Anyone | Developers | Anyone |
| AI support | Some | Good | Excellent |

- Excel Prototype: [link placeholder]
- Python R&D Script: [link placeholder]

---

## License

MIT — see [LICENSE](LICENSE).
