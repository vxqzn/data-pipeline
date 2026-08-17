# Engineering Notes

<small>* Right now, treatment effect is homogeneous by construction because buyer draws don't condition on region. A future iteration could inject a per-region multiplier to simulate genuine heterogeneous treatment effects.</small>

A few insights on why this is built the way it is:

## 1. Seed Isolation

### The Problem Encountered
When generating synthetic data for standard (A/B) and null twin (A/A) configurations, using a single global state or sequentially sharing one generator creates inter-stream dependencies. Changing the sample size of variant buyers (such as from 150,000 to 100,000) changes the number of times the RNG is called. This shifts the sequence of random numbers for all subsequent draws (timestamp offset, purchase values, control multiplier), meaning the control baseline no longer matches in between runs.

### The Approach
We make use of NumPy’s `SeedSequence` to spawn nine independent, child-level random number generators off the root seed (`64`).

This way:
- Group assignment, region mapping, control/variant buyer selection, timestamps, multipliers, etc. all get their own independent stream.
- Changing the variant configuration has zero downstream impact on the control population generation or properties. The Control group remains identical across both runs.

In simulation design, this is called [common random numbers](https://en.wikipedia.org/wiki/Variance_reduction#Common_random_numbers), and is used specifically to keep paired runs comparable.

---

## 2. Simpson's Paradox & Regional Segmentation

### The Problem Encountered
Aggregating test results across heterogeneous cohorts (such as geographical regions) can lead to Simpson's Paradox. If a baseline metric (like Conversion Rate, or RPU) varies wildly between regions, and traffic allocation fluctuates or is unbalanced, the overall aggregate lift direction can contradict the real direction of lift in every single region.

### The Approach
Instead of relying solely on the global test statistic, we segment the data by `region` (`ASIA`, `EMEA`, `LATAM`, `NA`) and run independent statistical tests for each cohort:
- A distinct $X^2$ contingency table is formed per region.
- A distinct Welch's t-test is run on the regional subset of users. 

This isolates the local treatment effect from global regional mixing effects, preventing baseline differences from biasing the treatment signal. Local signals outweigh mixed global signals.

---

## 3. Independence of Observations (Pseudoreplication issue)

### The Problem Encountered
Standard statistical tests (like Welch's t-test and Chi-Square) naturally assume that all observations in the sample are independent and identically distributed. 

If hypothesis tests are run directly on the transactions table (`df_purchases`), a user making 5 purchases will contribute 5 correlated entries. This artificially inflates the sample size and produces overconfident p-values. The textbook name for this is [pseudoreplication](https://en.wikipedia.org/wiki/Pseudoreplication).

### The Approach
We perform a user-level aggregate roll-up before statistical analysis:
1. All purchases are grouped by `userid` to calculate the total spend per user.
2. The aggregated spend is left-joined back to the main `df_users` registry.
3. Non-converting users are filled with `0`.
4. Hypothesis tests are run on this combined, independent user registry where $N = 5,000,000$, ensuring each row represents exactly one independent experimental unit (5 million independent rows).
