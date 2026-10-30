"""Analyse every experiment and write a ship / don't-ship memo: python -m experiments.analyze"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .generate import generate  # noqa: E402
from .stats import Effect, cuped, mean_test, proportion_test, sample_size_per_arm, srm_check  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GUARDRAIL_MAX_REGRESSION = 0.02   # page load may not get more than 2% slower


def analyse(df: pd.DataFrame) -> dict:
    c, t = df[df.variant == "control"], df[df.variant == "treatment"]
    ok, srm_p = srm_check(len(c), len(t))
    result = {"experiment": df.experiment.iloc[0], "n_control": len(c), "n_treatment": len(t), "srm_ok": ok,
              "srm_p": srm_p}
    if not ok:
        result["decision"] = "INVALID: do not read results"
        return result

    conversion = proportion_test("conversion", c.converted.to_numpy(), t.converted.to_numpy())
    revenue_raw = mean_test("revenue per user", c.revenue.to_numpy(), t.revenue.to_numpy())
    adjusted = cuped(df.revenue.to_numpy(), df.pre_spend.to_numpy())
    mask_t = (df.variant == "treatment").to_numpy()
    revenue_cuped = mean_test("revenue per user (CUPED)", adjusted[~mask_t], adjusted[mask_t])
    guardrail = mean_test("page load ms", c.page_load_ms.to_numpy(), t.page_load_ms.to_numpy())
    variance_reduction = 1 - (revenue_cuped.std_error / revenue_raw.std_error) ** 2

    guardrail_ok = guardrail.ci_high < GUARDRAIL_MAX_REGRESSION
    if conversion.significant and conversion.abs_diff > 0 and revenue_cuped.ci_low > 0 and guardrail_ok:
        decision = "SHIP"
    elif conversion.significant and conversion.abs_diff < 0:
        decision = "DO NOT SHIP"
    else:
        decision = "KEEP RUNNING / NO CLEAR WIN"
    result.update(conversion=conversion, revenue_raw=revenue_raw, revenue_cuped=revenue_cuped, guardrail=guardrail,
                  variance_reduction=variance_reduction, guardrail_ok=guardrail_ok, decision=decision)
    return result


def fmt(e: Effect) -> str:
    return (f"{e.rel_lift:+.1%} (95% CI {e.ci_low:+.1%} to {e.ci_high:+.1%}, p={e.p_value:.3f})")


def chart(r: dict, out: Path) -> None:
    effects = [r["conversion"], r["revenue_raw"], r["revenue_cuped"], r["guardrail"]]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for i, e in enumerate(effects):
        color = "#2E7D32" if e.ci_low > 0 and e.metric != "page load ms" else "#5B6770"
        if e.metric == "page load ms":
            color = "#E46C0A" if e.ci_high > 0 else "#5B6770"
        ax.errorbar(e.rel_lift * 100, i, xerr=[[(e.rel_lift - e.ci_low) * 100], [(e.ci_high - e.rel_lift) * 100]],
                    fmt="o", color=color, capsize=4, lw=2)
    ax.axvline(0, color="grey", lw=1)
    ax.set_yticks(range(len(effects)), [e.metric for e in effects])
    ax.invert_yaxis()
    ax.set_xlabel("Relative change vs control (%), 95% CI")
    ax.set_title(f"{r['experiment']}: decision = {r['decision']}")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def memo(results: list[dict], baseline: float) -> str:
    parts = ["# Experiment readout\n"]
    for r in results:
        if not r["srm_ok"]:
            parts.append(f"""## {r['experiment']}: {r['decision']}

The split is **{r['n_control']:,} control vs {r['n_treatment']:,} treatment** against a planned 50/50
(sample ratio mismatch, p = {r['srm_p']:.1e}). Users are missing from one arm, most likely a logging or
assignment bug, so any lift measured here is biased. **Action:** fix tracking, then rerun. No result is reported.
""")
            continue
        conv, rev, g = r["conversion"], r["revenue_cuped"], r["guardrail"]
        annual = rev.abs_diff * 2_000_000  # illustrative: 2M checkout users a year
        parts.append(f"""## {r['experiment']}: {r['decision']}

- **Conversion:** {conv.control:.2%} → {conv.treatment:.2%}, {fmt(conv)}
- **Revenue per user (CUPED-adjusted):** {fmt(rev)}, about **${annual:,.0f} a year** at 2M checkout users
- **Guardrail, page load:** {fmt(g)}; limit is +{GUARDRAIL_MAX_REGRESSION:.0%}, so {"within limit" if r['guardrail_ok'] else "BREACHED"}
- **Sample:** {r['n_control']:,} vs {r['n_treatment']:,} users, split check passed (p = {r['srm_p']:.2f})
- **Method note:** adjusting for pre-experiment spend (CUPED) cut revenue variance by **{r['variance_reduction']:.0%}**,
  the equivalent of running the test with that much more traffic.

![{r['experiment']}]({r['experiment']}.png)
""")
    n = sample_size_per_arm(baseline, 0.03)
    parts.append(f"## Planning the next test\n\nTo detect a 3% relative lift on a {baseline:.1%} conversion rate "
                 f"(80% power, 5% significance) we need **{n:,} users per arm**.\n")
    return "\n".join(parts)


def run(data_dir: Path = ROOT / "data", out_dir: Path = ROOT / "output") -> list[dict]:
    if not (data_dir / "experiment_users.csv").exists():
        generate(data_dir)
    df = pd.read_csv(data_dir / "experiment_users.csv")
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [analyse(g) for _, g in df.groupby("experiment", sort=False)]
    for r in results:
        if r["srm_ok"]:
            chart(r, out_dir / f"{r['experiment']}.png")
    baseline = df[df.variant == "control"].converted.mean()
    (out_dir / "readout.md").write_text(memo(results, baseline), encoding="utf-8")
    return results


if __name__ == "__main__":
    for r in run():
        line = f"{r['experiment']}: {r['decision']}"
        if r["srm_ok"]:
            line += f" | conversion {fmt(r['conversion'])} | CUPED variance cut {r['variance_reduction']:.0%}"
        print(line)
