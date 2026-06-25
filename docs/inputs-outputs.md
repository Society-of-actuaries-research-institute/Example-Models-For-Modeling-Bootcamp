# Inputs & Outputs

The production model reads `.xlsx` input workbooks and writes timestamped `.xlsx`
output workbooks. Input workbooks are expected to follow the sample workbook
structure in `inputs/`.

## Input Workbook

The required input sheets are:

| Sheet | Purpose |
|---|---|
| `Inforce` | Policy records to project. |
| `Parameters` | Valuation date, projection period, mortality assumptions, projection scale, and random number settings. |
| `Reporting` | Output sheet and graph selections. |

The workbook format is intentionally narrow. The model expects the sample
workbook layout and is not a general Excel parser.

## Inforce Sheet

| Column | Required | Description | Limitation |
|---|---:|---|---|
| `Policy #` | Yes | Unique policy identifier. | Used as the displayed policy ID. |
| `YOB` | Yes | Year of birth. | Must be greater than 1800. |
| `Gender` | Yes | `M` or `F`. | Other values are not accepted. |
| `Annual Benefit` | Yes | Annual benefit paid if alive. | Must be positive. |

Each row represents one policy.

## Parameters Sheet

The `Parameters` sheet is read by scanning column A for table markers.

| Marker | Value location | Description |
|---|---|---|
| `Valuation Date` | Column C | Valuation date. Projection starts in the next calendar year. |
| `Last Projection Year` | Column C | Final projection year, inclusive. |
| `Which Random Numbers?` | Column C | `Table` or `Seed`. |
| `Random Numbers Seed` | Column C | Base seed used when random-number mode is `Seed`. |
| `Mortality Rates` | Table rows | Age-indexed male and female base mortality rates. |
| `Projection Scale` | Table rows | Age-indexed male and female mortality improvement scales. |
| `Random Numbers` | Table rows | Scenario by policy random number matrix when mode is `Table`. |

## Reporting Sheet

The `Reporting` sheet controls which outputs are produced.

| Section | Field | Description |
|---|---|---|
| `Policy Results` | `Create?` | Whether to create `Policy Results`. |
| `Policy Results` | `Policy` | Selected policy ID for detailed output. |
| `Policy Results` | `Scenario` | Selected scenario for detailed output. |
| `Scenario Results` | `Create?` | Whether to create `Scenario Results`. |
| `Scenario Results` | `Scenario` | Selected scenario for policy-by-policy cash flows. |
| `Scenario Results` | `Create graph?` | Whether to create the scenario chart. |
| `Total Results` | `Create?` | Whether to create `Total Results`. |
| `Dashboard Results` | `Create?` | Whether to create `Dashboard Results`. |
| `Dashboard Results` | `Scenarios` | Number of scenarios used for dashboard results in seed mode and dashboard summaries. |
| `Dashboard Results` | `Policies` | Number of policies displayed in dashboard-oriented views. |
| `Dashboard Results` | `Discount Rate` | Annual discount rate used for present value. |
| `Dashboard Results` | `Create graph?` | Whether to create the dashboard chart. |

Boolean fields are interpreted as `Yes` or `No`.

## Random Number Modes

| Mode | Workbook setting | Behavior |
|---|---|---|
| Table | `Which Random Numbers? = Table` | Uses the `Random Numbers` table from the workbook. |
| Seed | `Which Random Numbers? = Seed` | Generates reproducible random numbers from `Random Numbers Seed`. |

In seed mode, each policy gets its own random number stream:

```text
np.random.default_rng(random_seed + policy_index)
```

## Output Workbook

Each production run creates:

```text
outputs/results_YYYYMMDD_HHMMSS.xlsx
```

The exact output sheets depend on the `Reporting` sheet.

| Sheet | Contents |
|---|---|
| `Policy Results` | Detailed year-by-year calculation for one policy and one scenario. |
| `Scenario Results` | Cash flows by policy for one selected scenario. |
| `Total Results` | Present value row and, for small scenario counts, total cash flows by scenario. |
| `Dashboard Results` | Present value statistics and optional dashboard chart. |

## Desktop UI Display Limits

The desktop UI is designed for classroom inspection, not full large-workbook
data browsing.

| Area | Display behavior |
|---|---|
| Input previews | Shows a capped preview for large tables and indicates when more data exists. |
| Inforce editing | Disabled for large inforce files; enabled only for small files. |
| Parameters and Reporting editing | Available through the desktop UI save-copy workflow. |
| Output table previews | Shows bounded previews and directs users to the output workbook for full results. |
| Large total cash flow tables | May be omitted from the UI or workbook when scenario counts are large. |

The output workbook is the authoritative place to inspect full model output.

## Input And Output Limitations

| Area | Limitation |
|---|---|
| File type | Production inputs use `.xlsx`, not `.xlsm`. |
| Sheet names | Expected sheet names must be present. |
| Layout | The parser assumes the sample workbook layout. |
| Gender | Only `M` and `F` are supported. |
| Product design | The modeled benefit is a simple annual payment while alive. |
| Randomness | Seed mode is reproducible but not a complete stochastic assumption framework. |
| Output graphs | Graphs appear only when `Create graph?` is set to `Yes`. |
