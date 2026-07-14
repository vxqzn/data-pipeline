# data-pipeline

A/B testing simulation and statistical analysis pipeline.

## Project Purpose
This pipeline simulates large-scale user transactional data under controlled* A/B testing conditions. It executes statistical hypothesis tests to detect treatment effects and outputs clean datasets, providing a structured, verifiable data source for downstream feeding into Power BI dashboards.

## Methodology & Architecture

The pipeline runs two parallel simulation flows: a standard configuration (incorporating a simulated treatment effect) and a null twin configuration (A/A test) to validate statistical precision.

```text
                  ┌──► Standard Sim (μ=0.15) ──► df_users/purchases ──┐
                  │                                                   │
[SeedSequence] ───┼                                                   ├──► [python/analysis.py] ──┬──► Welch's t-test (RPU) ──┬──► CSV Exports ────► [Power BI]
(Seed: 64)        │                                                   │                           │                           │    (data/*.csv)      (Pending)
                  └──► Null Twin Sim (μ=0.0)  ──► df_users/purchases ──┘                           └──► Chi-Square (CR) ───────┘
```

### 1. Data Simulation (`python/simulation.py`)
This module generates the synthetic user base and transactional history. To ensure the simulated data remains reproducible and mathematically decoupled across experimental groups, the random streams are isolated using independent sub-seeds. This prevents modifications in one stream from altering the properties of another:

*   **RNG isolation**: A single root `SeedSequence(seed=64)` spawns 9 independent child generators to prevent cross-stream contamination:
    1. Group selection RNG
    2. Region selection RNG
    3. Control buyer draw RNG
    4. Variant buyer draw RNG
    5. Purchase user ID RNG
    6. Timestamp offset RNG
    7. Control multiplier RNG
    8. Variant multiplier RNG
    9. Purchase baseline value RNG

    *Note: By doing this, changing the sample size or properties of the Variant group has zero downstream impact on the Control group. It remains identical across both Standard and Null runs.*
*   **User Population ($N = 5,000,000$)**:
    *   `userid`: Continuous sequence `[0, 4,999,999]`.
    *   `group`: Assigned via binomial choice (50% Control, 50% Variant).
    *   `region`: Assigned via multinomial choice (25% ASIA, 25% EMEA, 25% LATAM, 25% NA).
*   **Conversion (Buyer Draw)**:
    *   Control active buyer pool: 100,000 unique users drawn without replacement from the Control population.
    *   Variant active buyer pool:
        *   *Standard run*: 150,000 unique users drawn without replacement (simulates conversion lift).
        *   *Null Twin run*: 100,000 unique users drawn without replacement (simulates A/A baseline).
*   **Transactions ($T = 500,000$)**:
    *   `userid`: Sampled with replacement from the active buyer pool.
    *   `timestamp`: Offsets `2026-07-01` by random seconds in range `[1, 2,678,400]` (~31 days).
    *   `value`: Base value $V_{base} \sim \text{DiscreteUniform}(10, 25)$. Multiplied by a user-specific value factor and offset by a fractional charge:
        $$V_{final} = \text{round}(V_{base} \times M_{user}) + 0.99$$
        *   $M_{user} \sim LN(\mu=0.0, \sigma=0.5)$ for Control.
        *   $M_{user} \sim LN(\mu=0.15, \sigma=0.5)$ for standard Variant (simulates average order value lift).
        *   $M_{user} \sim LN(\mu=0.0, \sigma=0.5)$ for null Variant.

### 2. Statistical Analysis (`python/analysis.py`)
This module aggregates the simulated user and transaction tables to compute treatment effects and evaluate statistical significance. By grouping events before analysis, it ensures that statistical assumptions are met and lifts are measured accurately:

*   **User-Level Roll-up**:
    *   Transactions are grouped by `userid` to calculate total spend per user.
    *   This is left-joined back to the user registry, and non-buyers are filled with 0.
    *   *Why this matters*: Running statistical tests directly on event-level transactions would violate the independence assumption (i.i.d.) due to repeated purchases by the same user, resulting in false confidence (inflated Type I error rates).
*   **Hypothesis Testing**:
    *   **Conversion Rate Significance**: Pearson's Chi-Square Test ($X^2$) of independence is run on a $2 \times 2$ contingency table of conversion counts:
        $$\begin{pmatrix} \text{Control Buyers} & \text{Control Non-Buyers} \\ \text{Variant Buyers} & \text{Variant Non-Buyers} \end{pmatrix}$$
    *   **Revenue Per User (RPU) Significance**: Welch's t-test (two-sample independent, unequal variances) is run directly on user-level spend arrays:
        $$t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\frac{s_1^2}{N_1} + \frac{s_2^2}{N_2}}}$$
        *   *Why Welch's formulation is chosen*: It does not assume equal variances between the Control and Variant groups, which is critical since the Variant group's lognormal multiplier introduces higher variance.
*   **Regional Segmentation**:
    *   To guard against Simpson's Paradox, the script loops through regions (EMEA, NA, ASIA, LATAM) to run localized significance tests. Simpson's Paradox can occur if baseline conversion rates differ by region and traffic allocation is uneven, causing aggregate results to contradict regional trends.
    *   Segmented p-values and percentage lifts are computed for Conversion Rate (CR), Average Order Value (AOV), and Revenue Per User (RPU) as:
        $$\text{Lift} = \frac{\text{Variant} - \text{Control}}{\text{Control}}$$

---

## Comparative Validation (Standard vs. Null Twin)

To verify that the statistical tests behave correctly under null conditions and do not generate false positives (Type I errors), the pipeline runs a Parallel A/A "Null Twin" simulation side-by-side with the standard A/B test. The comparison below demonstrates how the statistical indicators react when no treatment effect is present:

| Metric / Dimension | Standard Run (A/B Test) | Null Twin (A/A Test) | Expectation / Validation |
| :--- | :--- | :--- | :--- |
| **Conversion, global p-value** | 0.0000 | 0.7636 | Reject Null vs. Accept Null |
| **Global Revenue (RPU), global p-value** | 0.0000 | 0.9018 | Reject Null vs. Accept Null |
| **Conversion lift, by region** | +48.12% to +52.29% | -0.82% to +1.19% | Positive Lift vs. Statistical Noise |
| **RPU lift, by region** | +71.77% to +75.33% | -1.25% to +1.42% | Positive Lift vs. Statistical Noise |
| **Regions significant** | $p < 0.001$ (All Regions) | $p \ge 0.197$ (None) | Significant vs. Non-Significant |

---

## Local Execution Guide

To get the pipeline up and running and generate the metrics files on your local machine:

1. **Clone the repository** (requires [Git](https://git-scm.com/)):
   ```bash
   git clone https://github.com/vxqzn/data-pipeline.git
   ```
   ```bash
   cd data-pipeline
   ```
2. **Set up the virtual environment**:
   ```bash
   python -m venv .venv
   ```
3. **Activate the environment**:
   - Windows PowerShell:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Execute the analysis**:
   ```bash
   python python/analysis.py
   ```
   This runs both simulation configurations and outputs the resulting CSV aggregates directly to the `data/` folder.

---

## Repository Map

Directory structure separating code, data, and presentation layers:

*   **[python/simulation.py](python/simulation.py)**: Python generator module implementing lognormal multipliers and seeded sub-stream data generation.
*   **[python/analysis.py](python/analysis.py)**: Metrics aggregation logic executing Welch's t-test and Chi-square calculations globally and per-region.
*   **[data/std_metrics_results.csv](data/std_metrics_results.csv)**: Regional aggregated metrics and statistical tests output for the standard test configuration.
*   **[data/null_metrics_results.csv](data/null_metrics_results.csv)**: Regional aggregated metrics and statistical tests output for the null (A/A) twin configuration.
*   **[powerbi/ab_testing_dashboard.pbix](powerbi/ab_testing_dashboard.pbix)**: Power BI report visualising aggregate conversion, AOV, RPU, and region-level treatment significance.
*   **[requirements.txt](requirements.txt)**: Core dependencies (`pandas`, `numpy`, `scipy`).

## Project Status

- [x] Data Simulation (`python/simulation.py`)
- [x] Statistical Analysis (`python/analysis.py`)
- [x] Data Export (`data/std_metrics_results.csv`, `data/null_metrics_results.csv`)
- [ ] Power BI Dashboard (Pending onboarding of the generated CSV exports)

## Notes
See **[NOTES.md](NOTES.md)** more depth.
