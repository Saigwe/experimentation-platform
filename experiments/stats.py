"""Statistics for online experiments: SRM check, proportion and mean tests, CUPED, and sample size."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class Effect:
    metric: str
    control: float
    treatment: float
    abs_diff: float
    rel_lift: float
    ci_low: float     # relative lift CI
    ci_high: float
    p_value: float
    std_error: float  # of the absolute difference

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def srm_check(n_control: int, n_treatment: int, expected_split: float = 0.5, alpha: float = 0.001) -> tuple[bool, float]:
    """Sample ratio mismatch: is the observed split consistent with the planned one? Returns (ok, p_value)."""
    total = n_control + n_treatment
    expected = [total * expected_split, total * (1 - expected_split)]
    p = stats.chisquare([n_control, n_treatment], expected).pvalue
    return bool(p >= alpha), float(p)


def _effect(metric, mc, mt, se, z=1.96) -> Effect:
    diff = mt - mc
    p = 2 * (1 - stats.norm.cdf(abs(diff / se)))
    return Effect(metric, mc, mt, diff, diff / mc, (diff - z * se) / mc, (diff + z * se) / mc, float(p), se)


def proportion_test(metric: str, conv_c: np.ndarray, conv_t: np.ndarray) -> Effect:
    pc, pt = conv_c.mean(), conv_t.mean()
    se = np.sqrt(pc * (1 - pc) / len(conv_c) + pt * (1 - pt) / len(conv_t))
    return _effect(metric, pc, pt, se)


def mean_test(metric: str, y_c: np.ndarray, y_t: np.ndarray) -> Effect:
    """Welch-style z-test for a continuous metric (large samples)."""
    se = np.sqrt(y_c.var(ddof=1) / len(y_c) + y_t.var(ddof=1) / len(y_t))
    return _effect(metric, y_c.mean(), y_t.mean(), se)


def cuped(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """CUPED: remove the part of y explained by a pre-experiment covariate x. theta = cov(y, x) / var(x).

    Computed on pooled data, so the adjustment is identical for both arms and keeps the estimate unbiased.
    """
    theta = np.cov(y, x, ddof=1)[0, 1] / x.var(ddof=1)
    return y - theta * (x - x.mean())


def sample_size_per_arm(baseline: float, mde_rel: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Users per arm to detect a relative lift `mde_rel` on a conversion rate `baseline` (two-sided)."""
    p1, p2 = baseline, baseline * (1 + mde_rel)
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    pbar = (p1 + p2) / 2
    n = ((z_a * np.sqrt(2 * pbar * (1 - pbar)) + z_b * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) / (p2 - p1)) ** 2
    return int(np.ceil(n))
