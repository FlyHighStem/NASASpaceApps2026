"""Regression tests for the fixes. Run: pytest -q   (all data here is SYNTHETIC)."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import counterpoint as cp  # noqa: E402

T = pd.date_range("2002-04-01", "2024-12-01", freq="MS")
YRS = (T.year + (T.month - 1) / 12).values


def ar1(rng, n, phi=0.3):
    e = rng.normal(size=n)
    y = np.empty(n)
    y[0] = e[0]
    for i in range(1, n):
        y[i] = phi * y[i - 1] + e[i]
    return y


def with_gap(v):
    v = v.copy()
    v[(YRS > cp.GAP[0]) & (YRS < cp.GAP[1])] = np.nan
    return v


def test_mann_kendall_matches_pymannkendall():
    import pymannkendall as pmk
    rng = np.random.default_rng(0)
    y = np.round(rng.normal(size=25).cumsum(), 1)  # rounded -> ties
    assert abs(cp.mk(y)[2] - pmk.original_test(y).p) < 1e-9


def test_annual_keeps_peak_season_series():
    rng = np.random.default_rng(1)
    s = pd.Series(rng.poisson(5, len(T)).astype(float), index=T)
    s[~s.index.month.isin([7, 8, 9])] = np.nan
    x, _ = cp.annual(s)
    assert len(x) >= cp.MINWIN


def test_annual_drops_partial_grace_gap_years():
    s = pd.Series(with_gap(np.random.default_rng(2).normal(size=len(T))), index=T)
    x, _ = cp.annual(s)
    assert 2017.0 not in x and 2018.0 not in x and len(x) >= cp.MINWIN


def test_noise_is_never_graded_D():
    rng = np.random.default_rng(3)
    cols = {i: with_gap(ar1(rng, len(T))) for i in range(120)}
    df = cp.analyse_all(pd.DataFrame(cols, index=T), 1, cp.GAP)
    assert not ((df.grade == "D") & (df.p >= 0.05)).any()


def test_planted_trend_is_A_and_gap_artifact_is_D():
    rng = np.random.default_rng(4)
    cols = {}
    for i in range(10):
        cols[i] = with_gap(2 * np.sin(2 * np.pi * YRS) + ar1(rng, len(T)) + 0.5 * (YRS - 2002))
    for i in range(10, 20):
        cols[i] = with_gap(2 * np.sin(2 * np.pi * YRS) + ar1(rng, len(T)) + 8 * (YRS > 2018))
    for i in range(20, 60):
        cols[i] = with_gap(ar1(rng, len(T)))
    df = cp.analyse_all(pd.DataFrame(cols, index=T), 1, cp.GAP).set_index("id")
    assert (df.loc[0:9, "grade"] == "A").mean() >= 0.8
    assert (df.loc[10:19, "grade"] == "D").mean() >= 0.8


def test_grade_frame_handles_empty_input():
    assert cp.grade_frame([]).empty


def test_benchmark_uses_project_schema_and_grade(tmp_path):
    rng = np.random.default_rng(5)
    trend = with_gap(ar1(rng, len(T)) - 0.8 * (YRS - 2002))
    table = pd.DataFrame({1: trend, 2: with_gap(ar1(rng, len(T)))}, index=T)
    coords = {1: (28.0, 75.0), 2: (24.0, 10.0)}
    cfg = {"frozen": True, "regions": [
        {"name": "decline", "tier": "resolvable", "expected": "down", "lat": [24, 32], "lon": [70, 78]},
        {"name": "wrong sign", "tier": "resolvable", "expected": "up", "lat": [24, 32], "lon": [70, 78]},
        {"name": "control", "tier": "resolvable", "expected": "none", "lat": [20, 28], "lon": [5, 15]},
        {"name": "empty", "tier": "marginal", "expected": "up", "lat": [-10, -2], "lon": [-48, -42]},
    ]}
    p = tmp_path / "b.json"
    p.write_text(json.dumps(cfg))
    B, sha, frozen = cp.benchmark(table, coords, str(p), cp.GAP)
    r = B.set_index("name").result
    assert frozen and len(sha) == 64
    assert r["decline"] == "recovered"
    assert r["wrong sign"].startswith("contradicted")
    assert r["control"] == "recovered (no clear trend)"
    assert r["empty"] == "no data in box"
