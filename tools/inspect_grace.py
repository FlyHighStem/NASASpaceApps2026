"""Inspect a GRACE/GRACE-FO mascon NetCDF file BEFORE running the pipeline.

Prints what the README lists as unverified: variable names, units, time
encoding, longitude convention, mascon-id layer candidates, and record gaps.

Usage:  python inspect_grace.py path/to/file.nc
"""
import argparse
import sys

import numpy as np
import xarray as xr


def open_any(path):
    """Open with time decoding; fall back to raw time if decoding fails."""
    try:
        return xr.open_dataset(path), True
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] default time decoding failed ({exc}); opening raw")
        return xr.open_dataset(path, decode_times=False), False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()

    ds, decoded = open_any(args.path)

    print("=== DIMENSIONS ===")
    for k, v in ds.sizes.items():
        print(f"  {k}: {v}")

    print("\n=== VARIABLES (name | dims | units | long_name) ===")
    for name, v in {**ds.coords, **ds.data_vars}.items():
        print(
            f"  {name:28s} {str(v.dims):28s} "
            f"{v.attrs.get('units', '-'):22s} {v.attrs.get('long_name', '-')}"
        )

    print("\n=== GLOBAL ATTRIBUTES (selected) ===")
    for k in ("title", "summary", "version", "product_version", "time_coverage_start",
              "time_coverage_end", "institution", "source", "references"):
        if k in ds.attrs:
            print(f"  {k}: {str(ds.attrs[k])[:200]}")

    # candidate data variables: 3-D with a time dimension
    cands = [n for n, v in ds.data_vars.items() if len(v.dims) == 3 and "time" in v.dims[0].lower()]
    print("\n=== CANDIDATE 3-D VARIABLES (time, lat, lon) ===")
    print("  " + (", ".join(cands) if cands else "none found: check dimension names above"))

    # time axis
    tname = next((n for n in ds.coords if n.lower() == "time"), None)
    if tname is None:
        print("\n[!] No coordinate named 'time'. Find the time variable above.")
    else:
        t = ds[tname]
        print("\n=== TIME ===")
        print(f"  decoded by xarray: {decoded}; dtype={t.dtype}; attrs={dict(t.attrs)}")
        print(f"  first={t.values[0]}  last={t.values[-1]}  n={t.size}")
        if decoded and np.issubdtype(t.dtype, np.datetime64):
            months = t.dt.year.values * 12 + t.dt.month.values
            d = np.diff(months)
            print(f"  median step (months): {np.median(d):.0f}")
            gaps = np.where(d > 1)[0]
            print(f"  gaps > 1 month: {len(gaps)}")
            for i in gaps:
                print(f"    {str(t.values[i])[:10]} -> {str(t.values[i + 1])[:10]}  ({d[i] - 1} missing months)")
            if np.any(d == 0):
                print("  [!] duplicate months found (several time slices per month)")
        else:
            print("  [!] time is not datetime64. Decode it by hand from the units attribute.")

    # grid
    for cname in ("lat", "latitude", "lon", "longitude"):
        if cname in ds.coords:
            c = ds[cname].values
            print(f"\n=== {cname.upper()} === min={c.min():.3f} max={c.max():.3f} n={c.size}")
            if cname.startswith("lon"):
                conv = "0..360" if c.max() > 180 else "-180..180"
                print(f"  longitude convention: {conv} (region_series.py wraps to -180..180)")

    # mascon id layer candidates
    ids = [n for n in {**ds.coords, **ds.data_vars} if "mascon" in n.lower() or n.lower().endswith("_id") or n.lower() == "id"]
    print("\n=== MASCON-ID LAYER CANDIDATES ===")
    if ids:
        for n in ids:
            v = ds[n]
            print(f"  {n}: dims={v.dims}, n_unique={len(np.unique(v.values[~np.isnan(v.values)])) if v.dtype.kind == 'f' else len(np.unique(v.values))}")
    else:
        print("  none in this file. The product may ship the mascon layout as a separate file;")
        print("  if not, the loader falls back to approximate block grouping, so say so in the methods.")

    print("\n=== COMPATIBILITY WITH counterpoint.py load_grace ===")
    for need, why in (("lwe_thickness", "data variable; otherwise pass --var NAME"),
                      ("land_mask", "optional land mask"),
                      ("mascon_id", "optional native mascon layer; otherwise pass --mascon-var NAME, else 3-degree blocks are used")):
        print(f"  {need:14s} {'found' if need in ds.variables else 'NOT found'}  ({why})")
    print("  the data variable must have dims time, lat, lon.")

    # mask / scale-factor hints
    hints = [n for n in ds.data_vars if any(s in n.lower() for s in ("mask", "scale", "error", "uncert"))]
    print("\n=== MASK / SCALE / UNCERTAINTY VARIABLES ===")
    print("  " + (", ".join(hints) if hints else "none"))

    # sanity stats of the first candidate variable
    if cands:
        v = ds[cands[0]]
        print(f"\n=== VALUES: {cands[0]} ===")
        print(f"  units={v.attrs.get('units', '-')}  min={float(v.min()):.3f}  max={float(v.max()):.3f}  "
              f"nan_fraction={float(np.isnan(v.values).mean()):.3f}")
        print("  Check: magnitudes plausible for the stated units (cm vs mm), land-only or global.")


if __name__ == "__main__":
    sys.exit(main())
