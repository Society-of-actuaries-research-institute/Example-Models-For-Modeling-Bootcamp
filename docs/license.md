# License

This project is licensed under the MIT License. See the repository `LICENSE`
file for the full project license text.

This page summarizes direct third-party dependencies used by the production
model and development workflow. It is a practical classroom inventory, not
legal advice and not a full transitive dependency audit.

## Runtime Dependencies

These packages are installed by:

```bash
pip install -e .
```

| Package | Used for | License noted from installed package metadata |
|---|---|---|
| `numpy` | Array calculations, random numbers, matrix operations. | BSD-style license; installed metadata also notes bundled numerical libraries. |
| `pandas` | Reading tabular workbook data. | BSD 3-Clause License. |
| `openpyxl` | Reading and writing Excel workbooks. | MIT License. |
| `matplotlib` | Creating output charts for Excel and the desktop UI. | Matplotlib license, PSF-style metadata; package includes additional bundled component licenses. |
| `pywebview` | Desktop application shell. | BSD 3-Clause License. |

## Development And Documentation Dependencies

These packages are installed by:

```bash
pip install -e ".[dev]"
```

| Package | Used for | License noted from installed package metadata |
|---|---|---|
| `pytest` | Automated tests. | MIT License. |
| `pytest-cov` | Test coverage reporting. | MIT License. |
| `mypy` | Static type checking. | MIT License. |
| `black` | Code formatting. | MIT License. |
| `pylint` | Linting and code quality checks. | GPL-2.0-or-later. |
| `types-openpyxl` | Type stubs for `openpyxl`. | Apache-2.0. |
| `pandas-stubs` | Type stubs for `pandas`. | BSD-3-Clause. |
| `mkdocs` | Documentation site generator. | BSD-2-Clause. |
| `mkdocs-material` | Documentation site theme. | MIT License. |
| `mkdocstrings` | API reference generation from Python docstrings. | ISC License. |

## Notes For Students

- Open-source packages can have different licenses.
- Some packages bundle additional third-party components.
- A real company release would usually include a more formal license review.
- This project lists direct dependencies because that is enough for the class
  illustration.
