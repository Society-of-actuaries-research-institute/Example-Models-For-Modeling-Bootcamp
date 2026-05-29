# MBC Production Model Example

This repository is a class illustration for the SOA Modeling Bootcamp. It
shows how the same actuarial model can evolve from a quick prototype, to an R&D
script, to production-style software.

The model projects stochastic mortality cash flows for annuity policies, then
summarizes present values across scenarios. The point of the project is not
the actuarial math, but the engineering journey.

> This project is for teaching. It may contain bugs and deliberate simplifications.
> Do not use it for real world applications.

## Start Here

If you are new to code repositories, do not try to understand every folder at
once. Start with these files:

1. `Prototype_model.xlsm`
   The Excel prototype. This is the fastest and most familiar way to explore the
   model logic.

2. `RnD_model.py`
   The Python R&D model. This moves the same logic into a simple Python script
   while keeping the structure close to the Excel prototype. The main advantage
   of this model is execution speed.

3. `src/mbc_model/`
   The "production" model package. This is the engineered version with a desktop
   interface, command-line interface, tests, documentation, input validation, and
   Excel output generation.

The production model intentionally has more folders and files. That extra
structure is part of what makes software easier to test, maintain, document, and
share.

## The Three Model Stages

| Stage | File or folder | Purpose |
|-------|----------------|---------|
| Excel prototype | `Prototype_model.xlsm` | Explore the model logic quickly in a familiar spreadsheet environment. |
| Python R&D script | `RnD_model.py` | The simplest possible upgrade from Excel prototype in terms of speed, but a downgrade in terms of transparency for non-programmer users. |
| Production software | `src/mbc_model/` | Demonstrate a maintainable application with UI, tests, docs, and reusable APIs. |

All three models contain the same exact logic and solve the same core problem.
The difference is how much engineering structure surrounds the calculations.

## What the Other Folders Are

| Path | What it is for |
|------|----------------|
| `inputs/` | Sample Excel input workbooks for the production and R&D models. |
| `outputs/` | Generated result workbooks from production and R&D model runs. |
| `tests/` | Automated checks that protect the production model from regressions. |
| `docs/` | Source files for the documentation site. |
| `pyproject.toml` | Python project configuration and dependency list. |
| `.github/`, `.vscode/`, `.claude/` | Development, automation, and local tool configuration. |

## Requirements

- Windows 10+ or macOS 12+
- Microsoft Excel to be able to run the macro in `Prototype_model.xlsm`
- Python 3.11 or newer
- Git, so you can download the project with `git clone`
- VS Code, which is the editor used in class demos
- OpenAI Codex, optional but used in class demos
- About 300 MB of disk space for Python dependencies

## Installation

### What "Terminal" Means

A terminal is a text window where you type commands and press **Enter**.

On Windows, use **PowerShell**:

1. Click the Windows Start button.
2. Type `PowerShell`.
3. Open **Windows PowerShell**.

On macOS, use **Terminal**:

1. Press **Command + Space**.
2. Type `Terminal`.
3. Open **Terminal**.

Type commands one line at a time. Do not type the `$`, `>`, or other prompt
symbols if your terminal shows them.

### Install Required Tools

#### Windows

1. Install Python from <https://www.python.org/downloads/>.
   During installation, check **Add python.exe to PATH**.
2. Install Git from <https://git-scm.com/download/win>.
3. Install Visual Studio Code from <https://code.visualstudio.com/>.
4. Open VS Code, go to **Extensions**, and install the **Python** extension from
   Microsoft and Codex - OpenAI's coding agent extension from OpenAI.
5. Optional for class demos: install Node.js LTS from <https://nodejs.org/>, then
   install Codex CLI:

   ```powershell
   npm install -g @openai/codex
   codex --login
   ```

   If PowerShell says `codex.ps1` is not digitally signed, run `codex.cmd`
   instead of `codex`, or open **Command Prompt** for the Codex command.

Check that the tools are installed:

```powershell
python --version
git --version
code --version
npm --version
```

#### macOS

1. Install Python from <https://www.python.org/downloads/>.
2. Install Git. If `git --version` asks to install Apple Command Line Tools,
   approve the prompt. You can also start that install manually:

   ```bash
   xcode-select --install
   ```

3. Install Visual Studio Code from <https://code.visualstudio.com/>.
4. Open VS Code, go to **Extensions**, and install the **Python** extension from
   Microsoft and Codex - OpenAI's coding agent extension from OpenAI.
5. Optional for class demos: install Node.js LTS from <https://nodejs.org/>, then
   install Codex CLI:

   ```bash
   npm install -g @openai/codex
   codex --login
   ```

Check that the tools are installed:

```bash
python3 --version
git --version
code --version
npm --version
```

OpenAI's current Codex CLI setup uses `npm install -g @openai/codex` followed by
`codex --login`. Because Codex changes over time, follow the latest OpenAI setup
prompts if they differ from these notes. The OpenAI setup guide is here:
<https://help.openai.com/en/articles/11381614-api-codex-cli-and-sign-in-with-chatgpt>.

### Download and Install This Project

#### Windows

Open **PowerShell**:

```powershell
git clone https://github.com/<your-org>/mbc-production-model-example.git
cd mbc-production-model-example
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

If `python` is not recognized, try `py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

To install developer tools for tests, linting, and documentation:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

#### macOS

Open **Terminal**:

```bash
git clone https://github.com/<your-org>/mbc-production-model-example.git
cd mbc-production-model-example
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

To install developer tools:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

The normal install command, `pip install -e .`, installs the packages needed to
run the model, including `numpy`, `pandas`, `openpyxl`, `matplotlib`, and
`pywebview`. The `.[dev]` install adds tools for tests, linting, type checking,
formatting, and documentation.

### Setup Help With Codex

If you have Codex installed, you can paste this into Codex from the project
folder:

```text
I am a beginner working on this class project. Please help me set it up on my computer. Check whether Python 3.11 or newer, Git, VS Code, Node.js/npm, and Codex CLI are installed. Then help me create a virtual environment, install the project with pip install -e ., optionally install developer tools with pip install -e ".[dev]", and run the desktop app with the virtual environment Python, such as .\.venv\Scripts\python -m mbc_model.ui on Windows or .venv/bin/python -m mbc_model.ui on macOS. Explain what each command does and stop before making file changes.
```

## Example Use

### 1. Excel Prototype

1. Open `Prototype_model.xlsm` in Microsoft Excel.
2. If Excel asks, enable editing and macros.
3. Go to the **Dashboard** tab.
4. Click the **Run** button.
5. Review the results and graphs created in the workbook.

This version is easiest to inspect because formulas, inputs, and outputs are all
visible in Excel.

### 2. Python R&D Script

Run the R&D model from the terminal.

On Windows:

```powershell
.\.venv\Scripts\python RnD_model.py
```

On macOS:

```bash
.venv/bin/python RnD_model.py
```

The script prints result tables in the terminal and displays matplotlib graphs.

### 3. Production Desktop Interface

Start the production desktop app:

On Windows:

```powershell
.\.venv\Scripts\python -m mbc_model.ui
```

On macOS:

```bash
.venv/bin/python -m mbc_model.ui
```

Then:

1. Click **Browse** and select `inputs/Input 10 pol 25 scen table.xlsx`.
2. Review the **Inforce**, **Parameters**, and **Reporting** input tabs.
3. Optionally edit inputs and save a new `.xlsx` copy.
4. Click **Run Model**.
5. Review output tables and charts on the **Outputs** tab.
6. Click **Open** to open the generated Excel output workbook.
7. Use the **Run Log** tab to see previous actions and runs.

Start with the 10-policy workbook before trying the larger examples.

### Optional Production Command Line

Run the default production input:

On Windows:

```powershell
.\.venv\Scripts\python -m mbc_model
```

On macOS:

```bash
.venv/bin/python -m mbc_model
```

Run a specific input workbook:

On Windows:

```powershell
.\.venv\Scripts\python -m mbc_model "inputs/Input 50k pol 10k scen seed.xlsx"
```

On macOS:

```bash
.venv/bin/python -m mbc_model "inputs/Input 50k pol 10k scen seed.xlsx"
```

Outputs are written to:

```text
outputs/results_YYYYMMDD_HHMMSS.xlsx
```

### Optional: Python API

```python
from pathlib import Path

from mbc_model.runner import run

output_path = run(Path("inputs/Input 10 pol 25 scen table.xlsx"))
print(f"Results written to: {output_path}")
```

## Debugging in VS Code

1. Open VS Code.
2. Click **File > Open Folder** and select this project folder.
3. If VS Code asks whether you trust the folder, choose **Yes**.
4. Press **Ctrl + Shift + P** on Windows or **Command + Shift + P** on macOS.
5. Type `Python: Select Interpreter`.
6. Select the interpreter inside `.venv`.
7. Click the **Run and Debug** icon on the left side of VS Code. It looks like a
   play button with a small bug.
8. Choose one of the class debug configurations:

| Debug configuration | What it does |
|---------------------|--------------|
| `MBC Desktop UI` | Opens the production desktop application. |
| `MBC CLI - small table workbook` | Runs the production model from the small sample `.xlsx` input. |
| `MBC R&D script` | Runs `RnD_model.py`. |
| `Current Python File` | Runs whichever Python file is currently open. |

Press **F5** or the green play button to start debugging. To set a breakpoint,
click just to the left of a line number in a Python file, then run the debugger.

## Production Input Workbooks

The production model uses Excel `.xlsx` input workbooks with three sheets:

| Sheet | Contents |
|-------|----------|
| `Inforce` | One row per policy: policy number, year of birth, gender, and annual benefit. |
| `Parameters` | Valuation date, projection years, mortality rates, projection scale, and random numbers. |
| `Reporting` | Which output sheets and graphs to create, plus selected policies/scenarios. |

Sample inputs included in `inputs/`:

| File | Policies | Scenarios | Random numbers |
|------|----------|-----------|----------------|
| `Input 10 pol 25 scen table.xlsx` | 10 | 25 | Workbook table |
| `Input 10 pol 25 scen seed.xlsx` | 10 | 25 | Seeded RNG |
| `Input 50k pol 10k scen seed.xlsx` | 50,000 | 10,000 | Seeded RNG |
| `Input 100k pol 10k scen seed.xlsx` | 100,000 | 10,000 | Seeded RNG |

## Production Output

Each production run creates a timestamped Excel workbook in `outputs/`. Depending
on the `Reporting` input sheet, the output can include:

| Sheet | Contents |
|-------|----------|
| `Policy Results` | Year-by-year detail for one selected policy and scenario. |
| `Scenario Results` | Cash flows by policy for one selected scenario. |
| `Total Results` | Total cash flows by scenario. |
| `Dashboard Results` | Present value summary statistics and optional charts. |

## Development

These are additional commands that can be used with the production software:

| Command | What it does |
|---------|--------------|
| `pytest` | Runs the automated test suite. |
| `pytest -m "not slow"` | Runs tests while skipping slow large-model tests. |
| `mypy src` | Checks Python type hints in the production package. |
| `pylint src` | Checks code quality and common Python mistakes. |
| `black src tests` | Automatically formats production and test code. |
| `mkdocs serve` | Starts a local documentation website for previewing `docs/`. |

Install developer tools first with `pip install -e ".[dev]"` using the virtual
environment commands shown above.

## License

MIT License. See [LICENSE](LICENSE).
