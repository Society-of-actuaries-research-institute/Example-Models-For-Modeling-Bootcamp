# Install & Run

This page focuses on the production model. The beginner setup walkthrough in
`README.md` remains the best place to start if Python, Git, or VS Code are new.

## Requirements

| Requirement | Why it is needed |
|---|---|
| Python 3.11 or newer | Runs the production package and desktop UI. |
| Git | Downloads the project and supports version control. |
| Microsoft Excel or another `.xlsx` viewer | Opens input and output workbooks. |
| VS Code | Used in class demonstrations for editing and debugging. |
| Optional OpenAI Codex | Used in class demonstrations for agent-assisted development. |

## Terminal Names

On Windows, use **PowerShell**. On macOS, use **Terminal**.

Commands in this documentation are typed one line at a time. Do not type prompt
symbols such as `$` or `>`.

## Install The Project

Windows PowerShell:

```powershell
git clone https://github.com/<your-org>/mbc-production-model-example.git
cd mbc-production-model-example
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

macOS Terminal:

```bash
git clone https://github.com/<your-org>/mbc-production-model-example.git
cd mbc-production-model-example
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

The normal install command installs the runtime libraries used by the production
model: `numpy`, `pandas`, `openpyxl`, `matplotlib`, and `pywebview`.

To install testing, linting, type-checking, formatting, and documentation tools:

Windows PowerShell:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

macOS Terminal:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

## Run The Desktop UI

Windows PowerShell:

```powershell
.\.venv\Scripts\python -m mbc_model.ui
```

macOS Terminal:

```bash
.venv/bin/python -m mbc_model.ui
```

The desktop UI lets the user browse for an input workbook, preview inputs, edit
supported input tables, run the model, view output tables and charts, open the
generated output workbook, and review the run log.

## Run From The Command Line

Run the default sample input:

Windows PowerShell:

```powershell
.\.venv\Scripts\python -m mbc_model
```

macOS Terminal:

```bash
.venv/bin/python -m mbc_model
```

Run a specific input workbook:

Windows PowerShell:

```powershell
.\.venv\Scripts\python -m mbc_model "inputs/Input 10 pol 25 scen table.xlsx"
```

macOS Terminal:

```bash
.venv/bin/python -m mbc_model "inputs/Input 10 pol 25 scen table.xlsx"
```

The command writes an output workbook to:

```text
outputs/results_YYYYMMDD_HHMMSS.xlsx
```

## Use The Python API

The production model can also be run from Python code:

```python
from pathlib import Path

from mbc_model.runner import run

output_path = run(Path("inputs/Input 10 pol 25 scen table.xlsx"))
print(f"Results written to: {output_path}")
```

For UI workflows that need both the workbook and the in-memory results, use:

```python
from pathlib import Path

from mbc_model.runner import run_with_results

output_path, model_results = run_with_results(
    Path("inputs/Input 10 pol 25 scen table.xlsx")
)
```

## Command Reference

| Command | What it does |
|---|---|
| `python -m mbc_model.ui` | Opens the desktop UI. |
| `python -m mbc_model` | Runs the default production input workbook. |
| `python -m mbc_model "inputs/file.xlsx"` | Runs a specific input workbook. |
| `pytest` | Runs the automated test suite. |
| `pytest -m "not slow"` | Runs tests while skipping large/manual scale tests. |
| `mypy src` | Checks type hints for the production package. |
| `pylint src` | Checks code quality and common Python mistakes. |
| `black src tests` | Formats production and test code. |
| `mkdocs serve` | Starts a local documentation website. |
| `mkdocs build` | Builds the documentation site and reports broken page links. |

## Debug In VS Code

1. Open VS Code.
2. Open this project folder.
3. Select the Python interpreter inside `.venv`.
4. Open **Run and Debug**.
5. Choose a debug configuration, such as `MBC Desktop UI` or
   `MBC CLI - small table workbook`.
6. Press **F5**.

Set a breakpoint by clicking next to a line number in a Python file before
starting the debugger.
