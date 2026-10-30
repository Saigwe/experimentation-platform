import numpy as np
import pytest

from experiments.analyze import run
from experiments.generate import generate
from experiments.stats import cuped, proportion_test, sample_size_per_arm, srm_check


def test_srm_check_flags_unbalanced_split():
    assert srm_check(50_000, 50_100)[0] is True
    assert srm_check(50_000, 48_500)[0] is False


def test_proportion_test_detects_known_difference():
    rng = np.random.default_rng(0)
    c = (rng.random(200_000) < 0.10).astype(int)
    t = (rng.random(200_000) < 0.11).astype(int)
    e = proportion_test("conversion", c, t)
    assert e.significant and e.ci_low < 0.10 < e.ci_high


def test_cuped_keeps_mean_and_reduces_variance():
    rng = np.random.default_rng(1)
    x = rng.normal(50, 10, 10_000)
    y = 2 * x + rng.normal(0, 5, 10_000)
    adj = cuped(y, x)
    assert abs(adj.mean() - y.mean()) < 1e-9
    assert adj.var() < 0.1 * y.var()


def test_sample_size_matches_textbook_value():
    # 10% baseline, 10% relative lift, 80% power, alpha 0.05 -> ~14,750 per arm
    assert 14_000 < sample_size_per_arm(0.10, 0.10) < 15_500


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    base = tmp_path_factory.mktemp("exp")
    return {r["experiment"]: r for r in run(generate(base / "data"), base / "out")}, base


def test_healthy_experiment_ships_and_recovers_true_lift(results):
    res, _ = results
    r = res["new_checkout"]
    assert r["srm_ok"] and r["decision"] == "SHIP"
    assert r["conversion"].ci_low < 0.04 < r["conversion"].ci_high   # planted lift is inside the CI
    assert r["variance_reduction"] > 0.4                              # CUPED pays off


def test_broken_experiment_is_refused(results):
    res, base = results
    assert res["free_shipping_banner"]["decision"].startswith("INVALID")
    assert "sample ratio mismatch" in (base / "out" / "readout.md").read_text(encoding="utf-8")
