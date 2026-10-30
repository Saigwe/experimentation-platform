"""Simulate two experiments on a marketplace checkout.

- `new_checkout`: healthy 50/50 split. Treatment lifts conversion 10.0% -> 10.4% and revenue per user by ~4%;
  page load time rises slightly (a guardrail to watch, not a blocker).
- `free_shipping_banner`: the treatment arm loses ~3% of its users to a logging bug (a sample ratio mismatch),
  which also biases the result. The analysis must refuse to read it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def simulate(name: str, n: int, lift: float, srm_drop: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    variant = rng.choice(["control", "treatment"], size=n)
    # Pre-period spend: strongly predicts in-experiment spend (the CUPED covariate).
    engagement = rng.gamma(2.0, 1.0, n)
    pre_spend = np.round(engagement * 25 + rng.normal(0, 8, n).clip(-20, 20), 2).clip(0)
    base_p = (0.10 * (0.6 + 0.4 * engagement / 2)).clip(0.01, 0.6)
    p = np.where(variant == "treatment", base_p * (1 + lift), base_p)
    converted = rng.random(n) < p
    order_value = rng.gamma(4, 15, n) * (0.7 + 0.3 * engagement / 2)
    revenue = np.where(converted, order_value, 0) + 0.8 * pre_spend + rng.normal(0, 3, n)
    load_ms = rng.normal(1200, 150, n) + np.where(variant == "treatment", 15, 0)
    df = pd.DataFrame({"experiment": name, "user_id": np.arange(n), "variant": variant, "pre_spend": pre_spend,
                       "converted": converted.astype(int), "revenue": np.round(revenue.clip(0), 2),
                       "page_load_ms": np.round(load_ms)})
    if srm_drop:
        # Logging bug: treatment users with low engagement are not recorded (biased loss, not random).
        lost = (df.variant == "treatment") & (rng.random(n) < srm_drop * 2) & (engagement < np.median(engagement))
        df = df[~lost]
    return df


def generate(out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat([
        simulate("new_checkout", 80_000, lift=0.04, srm_drop=0.0, seed=11),
        simulate("free_shipping_banner", 60_000, lift=0.0, srm_drop=0.03, seed=12),
    ]).to_csv(out / "experiment_users.csv", index=False)
    return out


if __name__ == "__main__":
    print(generate("data"))
