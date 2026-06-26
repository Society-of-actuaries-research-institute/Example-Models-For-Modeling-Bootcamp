# SOA Modeling Bootcamp example models

This repository is a class illustration for the SOA Modeling Bootcamp. It shows
how the same actuarial model can evolve from a quick spreadsheet prototype, to a
simple Python R&D script, to production-style Python software.

The model projects stochastic mortality cash flows for annuity policies, then
summarizes present values across scenarios. The point of the project is not the
actuarial math itself, but the engineering journey: how model structure,
testing, documentation, user interfaces, and repeatable runs change as a model
moves toward production quality.

| Stage | File or folder | What to focus on |
|-------|----------------|------------------|
| Excel prototype | `Prototype_model.xlsm` | The easiest place to inspect the model logic in a familiar spreadsheet. |
| Python R&D script | `RnD_model.py` | A simple Python version that stays close to the spreadsheet logic. |
| Production software | `src/mbc_model/` | The engineered version with a desktop UI, command-line interface, tests, documentation, input validation, and Excel output generation. |

If you are new to programming, do not try to understand every folder at once.
Use the Excel prototype first, then run the R&D script, then use the production
desktop interface.

> This project is for teaching. It may contain bugs and deliberate
> simplifications. Do not use it for real world applications.

## Installation

The intended setup path for this class is to use VS Code with OpenAI Codex.
Codex can help install Python, Git, dependencies, and the project itself.

### Step 1: Install VS Code

Install Visual Studio Code from:

<https://code.visualstudio.com/>

Open VS Code after it is installed.

### Step 2: Install OpenAI Codex In VS Code

In VS Code:

1. Open **Extensions**.
2. Search for **Codex - OpenAI's coding agent**.
3. Install **Codex - OpenAI's coding agent** from OpenAI.
4. Sign in when prompted.

### Step 3: Ask Codex To Install The Project

Open Codex in VS Code and paste the following prompt exactly as written:

```text
Please install and verify the SOA Modeling Bootcamp example models project on this computer. Detect whether this is Windows or macOS and use the correct commands for that operating system.

The GitHub repository is:
https://github.com/Society-of-actuaries-research-institute/Example-Models-For-Modeling-Bootcamp

Please complete the following setup:

1. Check whether Python 3.11 or newer is installed. If it is missing, give me the installation link and pause until I confirm it is installed.
2. Check whether Git is installed. If it is missing, give me the installation link and pause until I confirm it is installed.
3. Clone the GitHub repository if it is not already on this computer.
4. Open or confirm the repository folder in VS Code.
5. Create a virtual environment named .venv inside the repository folder.
6. Install the project with developer tools using pip install -e ".[dev]".
7. Build the documentation with mkdocs build.
8. Select the .venv Python interpreter in VS Code.
9. Verify the VS Code Run and Debug configurations are available.
10. Verify the VS Code Testing panel can discover the tests.
11. Run black --check src tests.
12. Run mypy src.
13. Run pytest tests -m "not slow" --cov=mbc_model --cov-fail-under=90.
14. Confirm that the R&D script can be run with the MBC R&D script debug configuration.
15. Confirm that the production desktop UI can be launched with the MBC Desktop UI debug configuration.

Please explain any required manual steps clearly and keep all commands scoped to the project folder and its .venv virtual environment.
```

A virtual environment is a project-specific Python setup that keeps this
project's packages separate from the rest of the computer. For this project, the
virtual environment is the `.venv` folder inside the repository.

To use it in VS Code:

1. Press **Ctrl + Shift + P** on Windows or **Command + Shift + P** on macOS.
2. Type `Python: Select Interpreter`.
3. Select the interpreter inside `.venv`.

This matters. A common beginner mistake is opening a separate Command Prompt or
Terminal and running `python` without the virtual environment. If the virtual
environment is active in a terminal, the prompt often starts with `(.venv)`.

When in doubt, use the VS Code **Run and Debug** panel instead of typing a
command manually.

## Example Use

### 1. Excel Prototype

1. Open `Prototype_model.xlsm` in Microsoft Excel.
2. If Excel asks, enable editing and macros.
3. Go to the **Dashboard** tab.
4. Click the **Run** button.
5. Review the results and graphs created in the workbook.

This version is easiest to inspect because formulas, inputs, and outputs are all
visible in Excel.

### 2. Set Up VS Code Debug

After Codex finishes installation:

1. Open VS Code.
2. Click **File > Open Folder** and select the project folder.
3. If VS Code asks whether you trust the folder, choose **Yes**.
4. Press **Ctrl + Shift + P** on Windows or **Command + Shift + P** on macOS.
5. Type `Python: Select Interpreter`.
6. Select the interpreter inside `.venv`.
7. Click the **Run and Debug** icon on the left side of VS Code. It looks like a
   play button with a small bug.

The project includes these debug configurations:

| Debug configuration | What it does |
|---------------------|--------------|
| `MBC Desktop UI` | Opens the production desktop application. |
| `MBC CLI - small table workbook` | Runs the production model from the small sample `.xlsx` input. |
| `MBC R&D script` | Runs `RnD_model.py` using the small sample `.xlsx` input. |
| `Current Python File` | Runs whichever Python file is currently open. |

Press **F5** or the green play button to start the selected configuration.

### 3. Python R&D Script

Recommended beginner path:

1. Open the **Run and Debug** panel in VS Code.
2. Select **MBC R&D script**.
3. Press **F5** or the green play button.

The script reads `inputs/Input 10 pol 25 scen table.xlsx` and writes a
timestamped output workbook to:

```text
outputs/rnd_results_YYYYMMDD_HHMMSS.xlsx
```

Optional command-line path:

On Windows, use the VS Code integrated PowerShell terminal from the project
folder:

```powershell
.\.venv\Scripts\python RnD_model.py "inputs/Input 10 pol 25 scen table.xlsx"
```

On macOS, use the VS Code integrated Terminal from the project folder:

```bash
.venv/bin/python RnD_model.py "inputs/Input 10 pol 25 scen table.xlsx"
```

Do not open a random Command Prompt and type only `python RnD_model.py`. That
often uses the wrong Python environment.

### 4. Production Desktop Interface

Recommended beginner path:

1. Open the **Run and Debug** panel in VS Code.
2. Select **MBC Desktop UI**.
3. Press **F5** or the green play button.

Then, in the desktop app:

1. Click **Browse** and select `inputs/Input 10 pol 25 scen table.xlsx`.
2. Review the **Inforce**, **Parameters**, and **Reporting** input tabs.
3. Optionally edit supported inputs and save a new `.xlsx` copy.
4. Click **Run Model**.
5. Review output tables and charts on the **Outputs** tab.
6. Click **Open** to open the generated Excel output workbook.
7. Use the **Run Log** tab to see previous actions and runs.

The project includes sample input workbooks in `inputs/`. Start with the
10-policy workbook before trying the larger examples.

Each production run creates a timestamped output workbook in `outputs/`, named
similar to:

```text
outputs/results_YYYYMMDD_HHMMSS.xlsx
```

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

### Optional Python API

```python
from pathlib import Path

from mbc_model.runner import run

output_path = run(Path("inputs/Input 10 pol 25 scen table.xlsx"))
print(f"Results written to: {output_path}")
```

## Development Commands

These commands are mainly for development and troubleshooting after Codex has
installed the project:

| Command | What it does |
|---------|--------------|
| `pytest tests -m "not slow"` | Runs tests while skipping slow large-model tests. |
| `mypy src` | Checks Python type hints in the production package. |
| `pylint src --fail-under=9.0` | Checks code quality and common Python mistakes. |
| `black --check src tests` | Checks whether production and test code are formatted. |
| `mkdocs serve` | Starts a local documentation website for previewing `docs/`. |
| `mkdocs build` | Builds the documentation site used by the desktop UI. |

Run these from the project folder with the `.venv` environment selected in VS
Code.

## License

MIT License. See [LICENSE](LICENSE).
