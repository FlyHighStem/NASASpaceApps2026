"""Independent region-level trend check for one benchmark box.

Purpose: a small, readable cross-check of the main pipeline. Compare its
numbers with Giovanni, KNMI Climate Explorer, and `counterpoint run` output.
It is NOT the Evidence Grade engine: no mascon grouping, no FDR, no steps.

What it does for one box:
  area-weighted regional mean -> monthly deseasonalised series -> annual means
  (years with >= 10 months) -> Mann-Kendall (pymannkendall) + Theil-Sen slope
  with 95% interval (scipy) -> record gaps -> share of start/end windows
  (>= 10 years) whose slope has the same sign as the full record.
Optional: the same for a driver file (e.g. precipitation) and a rank
correlation between the two annual series (association only, never cause).

Usage:
  python region_series.py --file grace.nc --var lwe_thickness --region india
  python region_series.py --file grace.nc --var lwe_thickness --region india \
      --driver imerg_monthly.nc --driver-var precipitation --out out/
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

try:
    import pymannkendall as mk
except ImportError:  # pragma: no cover
    sys.exit("pip install pymannkendall")


# ----------------------------------------------------------------- loading
def load_var(path, var=None):
    """Return a DataArray named by `var` with dims (time, lat, lon), lon in -180..180."""
    ds = xr.open_dataset(path)
    ren = {}
    for n in ds.coords:
        low = n.lower()
        if low in ("latitude", "lat"):
            ren[n] = "lat"
        elif low in ("longitude", "lon"):
            ren[n] = "lon"
    ds = ds.rename(ren)
    if var is None:
        c = [n for n, v in ds.data_vars.items() if {"time", "lat", "lon"} <= set(v.dims)]
        if len(c) != 1:
            sys.exit(f"Pass --var. Candidates: {c}")
        var = c[0]
    da = ds[var].transpose("time", "lat", "lon")
    if da["time"].dtype.kind == "O":  # cftime
        da = da.assign_coords(time=da.indexes["time"].to_datetimeindex())
    lon = ((da["lon"] + 180) % 360) - 180
    da = da.assign_coords(lon=lon).sortby("lon").sortby("lat")
    return da


def regional_mean(da, box):
    sub = da.sel(lat=slice(box["lat_min"], box["lat_max"]),
                 lon=slice(box["lon_min"], box["lon_max"]))
    if sub.sizes["lat"] == 0 or sub.sizes["lon"] == 0:
        sys.exit("Box selects no grid cells; check coordinates and longitude convention.")
    w = np.cos(np.deg2rad(sub["lat"]))
    m = sub.weighted(w).mean(dim=("lat", "lon"), skipna=True)
    s = m.to_series()
    s.index = pd.DatetimeIndex(s.index)
    return s.dropna()


# ----------------------------------------------------------------- series
def deseasonalise(s):
    clim = s.groupby(s.index.month).transform("mean")
    return s - clim


def annual_means(s, min_months=10):
    g = s.groupby(s.index.year)
    n = g.count()
    a = g.mean()[n >= min_months]
    return a


def record_gaps(s, min_missing=2):
    """Gaps measured in whole months between consecutive observations."""
    m = s.index.year * 12 + s.index.month
    d = np.diff(m)
    out = []
    for i in np.where(d > min_missing)[0]:
        out.append((str(s.index[i].date()), str(s.index[i + 1].date()), int(d[i] - 1)))
    return out


# ----------------------------------------------------------------- trends
def trend(annual):
    x = annual.index.values.astype(float)
    y = annual.values.astype(float)
    mkres = mk.original_test(y)  # tie-corrected, no autocorrelation correction on annual means
    slope, intercept, lo, hi = stats.theilslopes(y, x, alpha=0.95)
    return {
        "n_years": int(len(y)),
        "slope_per_year": float(slope),
        "slope_ci95": (float(lo), float(hi)),
        "mk_trend": mkres.trend,
        "mk_p": float(mkres.p),
        "mk_tau": float(mkres.Tau),
    }


def window_sign_share(annual, min_years=10):
    """Share of (start, end) windows with >= min_years whose Theil-Sen slope has the full-record sign."""
    x = annual.index.values.astype(float)
    y = annual.values.astype(float)
    full = np.sign(stats.theilslopes(y, x)[0])
    same = total = 0
    for i in range(len(y)):
        for j in range(i + min_years, len(y) + 1):
            total += 1
            same += int(np.sign(stats.theilslopes(y[i:j], x[i:j])[0]) == full)
    return (same / total) if total else float("nan"), total


def run_one(path, var, box):
    da = load_var(path, var)
    monthly = regional_mean(da, box)
    anom = deseasonalise(monthly)
    ann = annual_means(anom)
    return da.attrs.get("units", "?"), monthly, anom, ann


# ----------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--var")
    ap.add_argument("--benchmark", default="data/benchmark_regions.json")
    ap.add_argument("--region", required=True, help="part of a region name in the benchmark file, e.g. india")
    ap.add_argument("--driver")
    ap.add_argument("--driver-var")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    with open(args.benchmark) as f:
        doc = json.load(f)
    if not doc.get("frozen"):
        print("[warn] benchmark file is NOT frozen; freeze it before any real run you intend to report.")
    r0 = next((r for r in doc["regions"] if args.region.lower() in r["name"].lower()), None)
    if r0 is None:
        sys.exit("Region '%s' not found. Names: %s" % (args.region, [r["name"] for r in doc["regions"]]))
    box = {"name": r0["name"], "tier": r0.get("tier", ""), "lat_min": r0["lat"][0], "lat_max": r0["lat"][1],
           "lon_min": r0["lon"][0], "lon_max": r0["lon"][1], "expected_sign": {"up": 1, "down": -1, "none": 0}[r0["expected"]]}
    args.region = "".join(c if c.isalnum() else "_" for c in r0["name"])[:30]

    units, monthly, anom, ann = run_one(args.file, args.var, box)
    t = trend(ann)
    share, nwin = window_sign_share(ann)
    gaps = record_gaps(monthly)

    print(f"\nRegion: {box['name']}  (expected sign {box['expected_sign']:+d}, tier {box['tier']})")
    print(f"Units: {units}  | months: {len(monthly)}  | annual means: {t['n_years']}")
    print(f"Theil-Sen slope: {t['slope_per_year']:+.3f} {units}/yr  95% CI [{t['slope_ci95'][0]:+.3f}, {t['slope_ci95'][1]:+.3f}]")
    print(f"Mann-Kendall: {t['mk_trend']}  p={t['mk_p']:.4f}  tau={t['mk_tau']:+.2f}")
    print(f"Window robustness: {share:.0%} of {nwin} windows share the full-record sign")
    print("Gaps (>2 months): " + ("none" if not gaps else "; ".join(f"{a} -> {b} ({n} mo)" for a, b, n in gaps)))
    if gaps:
        print("  A trend that changes level across a gap may be an artifact; the main pipeline tests this.")
    got = int(np.sign(t["slope_per_year"]))
    sig = t["mk_p"] < 0.05
    exp = box["expected_sign"]
    verdict = ("matches expected sign" if (exp != 0 and got == exp and sig)
               else "no significant trend (as expected)" if (exp == 0 and not sig)
               else "does NOT match expectation: report it as a miss")
    print(f"Versus benchmark: {verdict}")

    os.makedirs(args.out, exist_ok=True)
    pd.DataFrame({"monthly": monthly, "deseasonalised": anom}).to_csv(os.path.join(args.out, f"{args.region}_monthly.csv"))
    ann.rename("annual_mean_anomaly").to_csv(os.path.join(args.out, f"{args.region}_annual.csv"))

    d_ann = None
    if args.driver:
        d_units, _, _, d_ann = run_one(args.driver, args.driver_var, box)
        dt = trend(d_ann)
        both = pd.concat([ann, d_ann], axis=1, join="inner").dropna()
        rho, p = stats.spearmanr(both.iloc[:, 0], both.iloc[:, 1]) if len(both) > 3 else (float("nan"), float("nan"))
        print(f"\nDriver ({args.driver_var}, {d_units}): slope {dt['slope_per_year']:+.4g}/yr, MK p={dt['mk_p']:.4f}")
        print(f"Spearman rho between annual series: {rho:+.2f} (p={p:.3f}, n={len(both)})  [association only]")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.plot(anom.index, anom.values, lw=0.8, color="0.6", label="monthly anomaly")
        ax.plot(pd.to_datetime(ann.index.astype(str) + "-07-01"), ann.values, "o-", label="annual mean")
        ax.set_title(f"{box['name']}: {t['slope_per_year']:+.2f} {units}/yr, MK p={t['mk_p']:.3f}")
        ax.set_ylabel(units)
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(args.out, f"{args.region}.png"), dpi=150)
        print(f"Saved plot and CSVs in {args.out}/")
    except ImportError:
        print(f"Saved CSVs in {args.out}/ (install matplotlib for a plot)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
