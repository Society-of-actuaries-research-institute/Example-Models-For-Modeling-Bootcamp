# MBC Production Model

Production-quality stochastic mortality cash flow model built for the SOA Modeling Bootcamp 2026.

## What this is

A side-by-side contrast with `RnD_Model_example.py`:

| | RnD model | Production model |
|---|---|---|
| Purpose | Explore and validate the math | Demonstrate engineering rigor |
| Structure | Single script, procedural | Typed package, OOP, `src/` layout |
| Scale | 10 policies × 25 scenarios | 100k policies × 10k scenarios |
| Testing | None | pytest ≥90% coverage |
| Type safety | None | mypy --strict |
| CI/CD | None | GitHub Actions |

## Quick start

```bash
git clone https://github.com/<user>/mbc-production-model
cd mbc-production-model
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m mbc_model "inputs/Input 10 pol 25 scen table.xlsx"
```

Output: `outputs/results_<timestamp>.xlsx`

## Architecture

```
src/mbc_model/
├── data/
│   ├── models.py       # Typed dataclasses: PolicyRecord, MortalityTable, etc.
│   └── loader.py       # Excel → Python objects with full validation
├── engine/
│   ├── mortality.py    # Deterministic: cumulative survival matrix
│   └── projection.py  # Stochastic: batch NumPy projection + PV
├── reporting/
│   └── writer.py       # Excel output writer (openpyxl, scale-aware)
└── runner.py           # Orchestrator: reads config, dispatches, times run
```
