# Monte Carlo Tuning

This document defines the tuning contract for `MonteCarloValidator`.

## Parameters

| Parameter | Default | Meaning | Tuning guidance |
| --- | ---: | --- | --- |
| `random_walk_std` | `1.0` | Gaussian shock size for a one-metric random-walk null model. | Lower for stable metrics; raise when historical spread is under-fitted. |
| `baseline_floor` | `1.0` | Minimum scale used when the baseline is near zero. | Keep above zero to avoid falsely narrow null distributions. |
| `baseline_relative_noise` | `0.1` | Relative jitter applied when generating baseline samples for batch validation. | Increase when historical market metrics show larger natural volatility. |
| `n_simulations` | `1000` | Number of Monte Carlo draws. | Use at least 1000 for report gating and 5000 for calibration studies. |
| `alpha` | `0.05` | Significance threshold for the empirical decision. | Keep at 0.05 unless a study protocol requires a stricter gate. |

## 参数敏感性

Run sensitivity analysis by sweeping `random_walk_std` over `0.25`, `0.5`,
`1.0`, and `1.5`, then compare p-value stability. A robust conclusion should
not flip significance for small changes around the chosen default. If a finding
only passes at one very narrow parameter value, mark it as method-sensitive in
the report.

## Calibration against platform data

Compare null distributions with 真实社交平台传播数据 where available:

- Xiaohongshu save/comment/share rate deltas for concept posts.
- Weibo repost and comment velocity for short copy variants.
- Douyin completion, like, and share proxy metrics.
- Zhihu long-form comment depth and disagreement markers.

The recommended workflow is to fit the null model on historical platform data,
then lock `random_walk_std` and `baseline_relative_noise` for the benchmark
suite before testing new concepts.

## 统计功效

For exploratory runs, 30-100 agents and 1000 Monte Carlo draws are enough to
flag obvious directionality. For launch-facing studies, prefer 100+ agents,
multiple seeds, and 5000 draws. When expected effect sizes are small, require
larger sample sizes or label the output as low-power rather than overstating the
result.

## Reporting rule

Reports should include the parameter values used for validation whenever a
finding depends on Monte Carlo significance.
