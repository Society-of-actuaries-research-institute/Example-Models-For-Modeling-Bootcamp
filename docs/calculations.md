# Actuarial Calculations

This page describes the calculations in the production model using the same
variable names used in the code. The goal is to make it easy to move between
the documentation, the Excel workbooks, and the Python files in `src/mbc_model`.

The model is intentionally simple. It projects mortality cash flows for
annuity-style policies, then summarizes present values across scenarios.

## Calculation Flow

```text
Input Workbook
  -> ExcelLoader
  -> MortalityEngine
  -> ProjectionEngine
  -> ReportWriter
  -> Output Workbook and Desktop UI
```

| Code variable | Meaning |
|---|---|
| `policy` | One `PolicyRecord` from the `Inforce` sheet. |
| `policy.yob` | Year of birth for the insured. |
| `policy.gender` | `M` or `F`, used to select mortality and projection scale columns. |
| `policy.annual_benefit` | Annual benefit paid when the policy is alive. |
| `projection_years` | Calendar years from the year after valuation through `last_projection_year`. |
| `attained_ages` | Age of the insured in each projection year. |
| `base_qx` | Base mortality rate for the attained age and gender. |
| `projection_scale` | Mortality improvement scale for the attained age and gender. |
| `improvement_factor` | Mortality improvement multiplier applied to `base_qx`. |
| `improved_qx` | Mortality rate after improvement. |
| `px` | One-year survival probability. |
| `cumulative_probability_of_survival_tPx` | Cumulative survival probability through each projection year. |
| `cumulative_probability_of_death_1_minus_tPx` | Cumulative death probability through each projection year. |
| `random_number` | Scenario/policy random number used for the survival test. |
| `survive_1_dead_0` | Survival indicator: 1 if alive, 0 if dead. |
| `total_cash_flow` | Policy cash flow by year. |
| `scenario_cash_flows` | Total cash flows by scenario and year. |
| `present_value_by_scenario` | Present value of cash flows for each scenario. |

## Projection Years

The valuation year is taken from `model_parameters.valuation_date.year`.
Projection begins in the following calendar year.

```text
projection_years = valuation_year + 1, ..., last_projection_year
```

For one `policy` and one `projection_year`:

```text
attained_ages = projection_years - policy.yob
```

## Mortality Rates

The `MortalityTable.BASE_YEAR` is 2012. For each projection year, the model
selects the age and gender-specific `base_qx` and `projection_scale`.

```text
improvement_factor = (1 - projection_scale) ** (projection_year - 2012)
```

```text
improved_qx = base_qx * improvement_factor
```

```text
px = 1 - improved_qx
```

If the attained age is beyond the end of the mortality table, the model treats
the policy as certain to die by setting the effective survival probability to
zero.

## Cumulative Survival

For each policy, cumulative survival is the running product of one-year
survival probabilities:

```text
cumulative_probability_of_survival_tPx[year_index]
    = px[0] * px[1] * ... * px[year_index]
```

The cumulative death probability is:

```text
cumulative_probability_of_death_1_minus_tPx
    = 1 - cumulative_probability_of_survival_tPx
```

In actuarial notation, `cumulative_probability_of_survival_tPx` corresponds to
`tPx`, the probability of survival from the valuation date through the selected
projection year.

## Random Numbers

The model supports two random-number modes.

| Mode | Code behavior |
|---|---|
| Table | `random_number_table[scenario_index, policy_index]` is read from the workbook. |
| Seed | Each policy uses `np.random.default_rng(random_seed + policy_index)` and draws one random number per scenario. |

The seed approach is reproducible because policy 1 uses `random_seed + 0`,
policy 2 uses `random_seed + 1`, and so on.

## Survival Indicator

For a selected `random_number`, the policy is alive in a projection year if the
random number is greater than the cumulative death probability.

```text
survive_1_dead_0 = 1 if random_number > cumulative_probability_of_death_1_minus_tPx else 0
```

Otherwise:

```text
survive_1_dead_0 = 0
```

This is a simplified annual survival model. It uses one random number per
policy/scenario and compares it to each projection year's cumulative death
probability.

## Policy Cash Flow

The annual benefit is paid when the policy is alive:

```text
total_cash_flow = policy.annual_benefit * survive_1_dead_0
```

`Policy Results` shows this calculation in detail for one selected policy and
scenario.

## Scenario Cash Flows

For each scenario and year, the model sums policy cash flows:

```text
scenario_cash_flows[scenario_index, year_index]
    = sum(total_cash_flow for all policies)
```

`Scenario Results` shows the cash flow by policy for one selected scenario.
`Total Results` shows total cash flows by scenario.

## Present Value

The model uses end-of-year discounting. The discount exponent is based on the
number of years from the valuation year to each projection year:

```text
time_periods_from_valuation = projection_years - valuation_year
```

```text
discount_factors_by_year = 1 / (1 + discount_rate) ** time_periods_from_valuation
```

The present value for each scenario is the dot product of that scenario's cash
flows and the discount factors:

```text
present_value_by_scenario = scenario_cash_flows @ discount_factors_by_year
```

## Dashboard Statistics

The `Dashboard Results` sheet summarizes `present_value_by_scenario` using:

| Statistic | Code behavior |
|---|---|
| Mean | `np.mean(present_values_subset)` |
| Median | `np.median(present_values_subset)` |
| Std Dev | `np.std(present_values_subset)` |
| Min | `np.min(present_values_subset)` |
| Max | `np.max(present_values_subset)` |

The dashboard may use a subset of scenarios based on the `Scenarios` value in
the `Reporting` sheet.

## Charts

When `Create graph?` is set to `Yes`, the model creates:

| Output area | Chart |
|---|---|
| `Scenario Results` | `Scenario X Cash Flows by Policy` |
| `Dashboard Results` | `Cash Flow Projection by Scenario` |

For large scenario counts, the dashboard chart selects representative scenarios
by present value percentile rather than plotting every scenario line.
