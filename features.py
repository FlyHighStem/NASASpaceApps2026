"""Water + wildfire features on the same engine. Real NASA data only.
  python features.py register-grace
  python features.py power --stride 2                       # NASA POWER/MERRA-2: precip, soil wetness, evaporation, T2M, RH2M, VPD, wind
  python features.py fires --map-key KEY --bbox W S E N     # MODIS active fires (NASA FIRMS): counts, radiative power, peak-season trend
  python features.py fires --csv FILE.csv ...                # or FIRMS archive CSVs (latitude, longitude, acq_date[, frp])
  python features.py groundwater --fetch                     # GRACE minus GLDAS soil moisture/snow/canopy (needs Earthdata login)
  python features.py burned --nc FILE.nc --var NAME          # gridded monthly burned area (lat/lon/time NetCDF)
"""
import argparse
import glob
import io
import json
import os
import shutil
import datetime

import numpy as np
import pandas as pd
import counterpoint as cp

O = "output"
V = f"{O}/vars"
NOGAP = (1e9, 1e9 + 1)
RE = "Reanalysis (MERRA-2 via NASA POWER)"


def _c(label, group, unit, cmap, kind, desc, pct=True, fd=0):
    return dict(
        label=label, group=group, unit=unit, cmap=cmap,
        kind=kind, desc=desc, pct=pct, fire_dir=fd
    )


CATALOG = {
    "grace_lwe": _c(
        "Water storage (GRACE)", "Water", "cm/yr", "BrBG",
        "Satellite observation",
        "Liquid water equivalent thickness: depth of water holding the same stored mass (snow, soil, groundwater, surface water). JPL GRACE/GRACE-FO mascons.",
        False, -1
    ),
    "GW_ANOM": _c(
        "Groundwater-style anomaly", "Water", "cm/yr", "BrBG",
        "GRACE minus GLDAS (derived)",
        "GRACE storage minus GLDAS-Noah soil moisture, snow and canopy water (anomalies vs 2004-2009). Indicative only: surface water and reservoirs are not removed.",
        False, -1
    ),
    "PRECTOTCORR": _c(
        "Precipitation", "Water", "mm/day per yr", "BrBG", RE,
        "Bias-corrected total precipitation.", True, -1
    ),
    "GWETTOP": _c(
        "Surface soil wetness", "Water", "index per yr", "BrBG", RE,
        "Soil wetness of the top ~5 cm, 0 (dry) to 1 (saturated).", True, -1
    ),
    "GWETROOT": _c(
        "Root-zone soil wetness", "Water", "index per yr", "BrBG", RE,
        "Soil wetness in the root zone, 0 to 1.", True, -1
    ),
    "EVLAND": _c(
        "Evaporation over land", "Water", "mm/day per yr", "BrBG", RE,
        "Evaporation from the land surface.", True, 0
    ),
    "T2M": _c(
        "Air temperature (2 m)", "Wildfire conditions", "°C per yr",
        "RdBu_r", RE, "Mean air temperature at 2 m.", False, 1
    ),
    "RH2M": _c(
        "Relative humidity (2 m)", "Wildfire conditions", "% per yr",
        "BrBG", RE, "Falling humidity dries fuels.", True, -1
    ),
    "VPD": _c(
        "Vapor pressure deficit", "Wildfire conditions", "kPa per yr",
        "RdBu_r", "Derived from T2M and RH2M (MERRA-2)",
        "How strongly air pulls moisture from fuels; higher = more fire-prone.",
        True, 1
    ),
    "WS2M": _c(
        "Wind speed (2 m)", "Wildfire conditions", "m/s per yr",
        "RdBu_r", RE, "Mean wind speed at 2 m.", True, 1
    ),
    "FIRE_COUNT": _c(
        "Active-fire detections", "Wildfire conditions",
        "detections/month per yr", "RdBu_r",
        "Satellite observation (MODIS via NASA FIRMS)",
        "Monthly MODIS thermal-anomaly detections per 3-degree block. Cloud cover and overpass changes affect counts.",
        True, 1
    ),
    "FIRE_FRP": _c(
        "Fire radiative power", "Wildfire conditions", "MW/month per yr",
        "RdBu_r", "Satellite observation (MODIS via NASA FIRMS)",
        "Summed fire radiative power of detections: a measure of fire intensity, not just frequency.",
        True, 1
    ),
    "FIRE_SEASON": _c(
        "Peak-season fire detections", "Wildfire conditions",
        "detections/month per yr", "RdBu_r",
        "Satellite observation (MODIS via NASA FIRMS)",
        "Detections in each unit's three peak fire months only, so trends are not diluted by the off-season.",
        True, 1
    ),
    "BURNED_AREA": _c(
        "Burned area", "Wildfire conditions", "units of file per yr",
        "RdBu_r", "Satellite observation (gridded file you supply)",
        "Mean monthly burned area per 3-degree block, in the units of the file.",
        True, 1
    ),
}


import contextlib
@contextlib.contextmanager
def _atomic(path):
    """Write to a temp file, then rename, so a reader never sees a half-written (empty) file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f: yield f
    os.replace(tmp, path)

def add_var(name, table, coords, source, jobs=1, gap=NOGAP):
    d = f"{V}/{name}"
    os.makedirs(d, exist_ok=True)

    df = cp.analyse_all(table, jobs, gap)
    if df.empty:
        print(name, ": no analysable units")
        return

    df["lat"] = df.id.map(lambda k: coords[k][0])
    df["lon"] = df.id.map(lambda k: coords[k][1])
    R = cp.build_regions(df, table)
    P = cp.mirror_pairs(R)

    df.to_csv(f"{d}/results.csv", index=False)
    table.round(4).to_csv(f"{d}/series.csv")
    R.to_csv(f"{d}/regions.csv", index=False)
    P.to_csv(f"{d}/pairs.csv", index=False)

    with _atomic(f"{d}/meta.json") as f:
        json.dump(
            dict(
                source=source,
                gap=list(gap),
                fetched=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                period=[
                    str(table.index.min().date()),
                    str(table.index.max().date())
                ],
            ),
            f
        )

    print(
        f"{name}: {len(df)} units | "
        f"grades {df.grade.value_counts().to_dict()} | "
        f"regions {len(R)} | mirror pairs {len(P)}"
    )


def units():
    return pd.read_csv(f"{O}/results.csv")[["id", "lat", "lon"]]


def coords_of(u):
    return {r.id: (r.lat, r.lon) for r in u.itertuples()}


def register_grace():
    d = f"{V}/grace_lwe"
    os.makedirs(d, exist_ok=True)

    for n in ("results", "series", "regions", "pairs"):
        shutil.copy(f"{O}/{n}.csv", f"{d}/{n}.csv")

    with open(f"{O}/sources.json") as f:
        m = json.load(f)

    with _atomic(f"{d}/meta.json") as f:
        json.dump(
            dict(
                source=m["source"],
                fetched=m["fetched"],
                period=m["period"],
                gap=m["gap"]
            ),
            f
        )

    print("registered grace_lwe")


def power_multi(lat, lon, params, start, end):
    import requests

    r = requests.get(
        "https://power.larc.nasa.gov/api/temporal/monthly/point",
        timeout=90,
        params=dict(
            parameters=",".join(params),
            community="AG",
            latitude=round(lat, 3),
            longitude=round(lon, 3),
            start=start,
            end=end,
            format="JSON",
        ),
    )
    r.raise_for_status()
    d = r.json()["properties"]["parameter"]

    return pd.DataFrame({
        p: pd.Series({
            pd.Timestamp(int(k[:4]), int(k[4:]), 1): v
            for k, v in d[p].items()
            if not k.endswith("13") and v > -900
        })
        for p in params if p in d
    })


POWER_PARAMS = [
    "PRECTOTCORR", "GWETTOP", "GWETROOT", "EVLAND",
    "T2M", "RH2M", "WS2M"
]


def power_features(stride=2, start=2002, end=2025, jobs=1, include_ice=False):
    from concurrent.futures import ThreadPoolExecutor

    u = units()
    keep = (np.floor(u.lat / 3) % stride == 0) & (
        np.floor(u.lon / 3) % stride == 0
    )

    if not include_ice:
        keep &= ~(
            (u.lat < -60)
            | ((u.lat > 60) & (u.lon > -75) & (u.lon < -10))
        )

    u = u[keep]
    os.makedirs(f"{O}/cache", exist_ok=True)
    print(f"fetching {len(u)} points from NASA POWER (cached; safe to rerun)")

    def one(r):
        fn = f"{O}/cache/{r.lat:.2f}_{r.lon:.2f}_{start}_{end}.pkl"
        if os.path.exists(fn):
            return r.id, pd.read_pickle(fn)

        for _ in range(3):
            try:
                df = power_multi(r.lat, r.lon, POWER_PARAMS, start, end)
                df.to_pickle(fn)
                return r.id, df
            except Exception as e:
                err = e

        print("failed", r.id, err)
        return r.id, None

    with ThreadPoolExecutor(6) as ex:
        res = [
            x for x in ex.map(one, u.itertuples())
            if x[1] is not None and len(x[1]) > 120
        ]

    print(f"fetched {len(res)}/{len(u)}")
    if not res:
        raise SystemExit("No POWER data fetched (check internet; try again).")

    tabs = {
        p: pd.DataFrame({i: df[p] for i, df in res if p in df})
        for p in POWER_PARAMS
    }

    es = 0.6108 * np.exp(
        17.27 * tabs["T2M"] / (tabs["T2M"] + 237.3)
    )
    tabs["VPD"] = es * (1 - tabs["RH2M"] / 100)

    for p, t in tabs.items():
        if t.shape[1]:
            add_var(
                p, t, coords_of(u),
                f"NASA POWER monthly {p} (MERRA-2), {start}-{end}",
                jobs
            )


def to_units(vals, lat, lon, u, how="mean"):
    """(T,Y,X) grid -> (T x unit) table: 3-degree block means (or sums),
    blocks assigned to the nearest GRACE unit (<400 km).
    """
    LA, LO = np.meshgrid(
        lat, np.where(lon > 180, lon - 360, lon), indexing="ij"
    )
    la, lo = LA.ravel(), LO.ravel()
    v = vals.reshape(vals.shape[0], -1).astype("float32")

    ok = ~np.isnan(v).all(axis=0)
    v, la, lo = v[:, ok], la[ok], lo[ok]
    key = np.floor(la / 3) * 1000 + np.floor(lo / 3)
    o = np.argsort(key, kind="stable")
    key, v, la, lo = key[o], v[:, o], la[o], lo[o]

    _, st = np.unique(key, return_index=True)
    good = ~np.isnan(v)
    n = np.diff(np.append(st, len(key)))
    sm = np.add.reduceat(np.where(good, v, 0), st, axis=1)
    ct = np.add.reduceat(good.astype(float), st, axis=1)
    bm = sm if how == "sum" else np.where(ct > 0, sm / np.maximum(ct, 1), np.nan)

    D = cp.hav(
        (np.add.reduceat(la, st) / n)[:, None],
        (np.add.reduceat(lo, st) / n)[:, None],
        u.lat.values[None, :],
        u.lon.values[None, :],
    )
    j = D.argmin(1)
    ok = D.min(1) < 400

    grouped = getattr(
        pd.DataFrame(bm[:, ok]).T.groupby(u.id.values[j[ok]]),
        "sum" if how == "sum" else "mean"
    )
    return grouped().T


def peak_season(t):
    """Keep only each unit's three consecutive peak months (others NaN)."""
    clim = t.groupby(t.index.month).mean().reindex(range(1, 13)).fillna(0).values
    mo = t.index.month.values
    a = t.values.astype(float)

    for j in range(a.shape[1]):
        c = clim[:, j]
        b = max(
            range(12),
            key=lambda m: c[m] + c[(m + 1) % 12] + c[(m + 2) % 12]
        )
        a[
            ~np.isin(
                mo,
                [b + 1, (b + 1) % 12 + 1, (b + 2) % 12 + 1]
            ),
            j
        ] = np.nan

    return pd.DataFrame(a, index=t.index, columns=t.columns)


def _count(df):
    m = pd.to_datetime(df.acq_date).dt.to_period("M").dt.to_timestamp()
    d = pd.DataFrame({
        "bl": np.floor(df.latitude.values / 3).astype(int),
        "bo": np.floor(df.longitude.values / 3).astype(int),
        "m": m.values,
        "n": 1,
        "frp": df["frp"].values if "frp" in df else 0.0,
    })
    return d.groupby(["bl", "bo", "m"]).agg(
        n=("n", "sum"),
        frp=("frp", "sum")
    )


def fires(csvs=None, key=None, bbox=None, start=2002, end=2025, jobs=1):
    u = units()
    parts = []

    if csvs:
        for f in csvs:
            for ch in pd.read_csv(
                f,
                usecols=lambda c: c in (
                    "latitude", "longitude", "acq_date", "frp"
                ),
                chunksize=500000,
            ):
                parts.append(_count(ch))
    else:
        import requests
        from concurrent.futures import ThreadPoolExecutor

        w, s, e, n = bbox

        # FIRMS area API day range must be 1–5.
        # Step by five days so the requested windows cover the period.
        days = pd.date_range(
            f"{start}-01-01",
            f"{end}-12-31",
            freq="5D"
        )

        import time
        os.makedirs(f"{O}/cache/firms", exist_ok=True)

        def one(d):
            """One 5-day window. Cached on disk, so a rerun only fetches what is missing.
            FIRMS limits requests per 10 minutes: on that error, wait and retry instead of aborting."""
            fn = f"{O}/cache/firms/{w}_{s}_{e}_{n}_{d.date()}.csv"
            if os.path.exists(fn):
                t = open(fn).read()
            else:
                url = (
                    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                    f"{key}/MODIS_SP/{w},{s},{e},{n}/5/{d.date()}"
                )
                t = None
                for attempt in range(40):
                    try:
                        response = requests.get(url, timeout=120)
                    except requests.RequestException:
                        time.sleep(5)
                        continue
                    if response.ok and ("latitude" in response.text[:300] or not response.text.strip()):
                        t = response.text
                        break
                    if "transaction limit" in response.text.lower():
                        time.sleep(60)  # the allowance resets every few minutes
                        continue
                    raise RuntimeError(f"FIRMS HTTP {response.status_code}: {response.text[:300]}")
                if t is None:
                    raise RuntimeError("FIRMS kept refusing requests (rate limit or network). Run again in a few minutes; finished windows are cached.")
                with open(fn + ".tmp", "w") as f_:
                    f_.write(t)
                os.replace(fn + ".tmp", fn)
            if not t.strip():
                return None
            df = pd.read_csv(io.StringIO(t))
            return _count(df) if len(df) else None

        print(
            f"{len(days)} FIRMS requests (MODIS_SP). "
            "If you see errors, check the source name in the FIRMS API docs."
        )

        with ThreadPoolExecutor(3) as ex:
            parts = [p for p in ex.map(one, days) if p is not None]

    if not parts:
        raise SystemExit("No fire detections found.")

    c = pd.concat(parts).groupby(level=[0, 1, 2]).sum()
    idx = pd.date_range(f"{start}-01-01", f"{end}-12-01", freq="MS")
    out = {}

    for col in ("n", "frp"):
        w_ = c[col].unstack(2)
        g = w_.index
        la = np.array([i[0] for i in g]) * 3 + 1.5
        lo = np.array([i[1] for i in g]) * 3 + 1.5

        D = cp.hav(
            la[:, None], lo[:, None],
            u.lat.values[None, :], u.lon.values[None, :]
        )
        ok = D.min(1) < 400
        t = w_[ok].groupby(u.id.values[D.argmin(1)[ok]]).sum().T
        t.index = pd.DatetimeIndex(t.index)
        out[col] = t.reindex(idx).fillna(0)

    cnt = out["n"]
    cnt = cnt.loc[:, cnt.sum() >= 12]
    if cnt.empty:
        raise SystemExit("No land units with enough detections.")

    src = f"MODIS active fires, NASA FIRMS, {start}-{end}"
    cc = coords_of(u)

    add_var("FIRE_COUNT", cnt, cc, src, jobs)

    if out["frp"][cnt.columns].sum().sum() > 0:
        add_var("FIRE_FRP", out["frp"][cnt.columns], cc, src + " (FRP)", jobs)

    add_var(
        "FIRE_SEASON",
        peak_season(cnt),
        cc,
        src + " (peak 3 months per unit)",
        jobs
    )


def groundwater(gdir="data/gldas", fetch=False, start=2002, end=2025, jobs=1):
    import xarray as xr

    if fetch:
        import earthaccess

        earthaccess.login(strategy="environment")
        res = earthaccess.search_data(
            short_name="GLDAS_NOAH025_M",
            version="2.1",
            temporal=(f"{start}-04-01", f"{end}-12-31"),
        )
        print(len(res), "GLDAS granules")
        earthaccess.download(res, gdir)

    files = sorted(glob.glob(f"{gdir}/GLDAS_NOAH025_M*.nc4"))
    ds = xr.open_mfdataset(files, combine="by_coords") if files else None
    if ds is None:
        raise SystemExit(
            f"No GLDAS_NOAH025_M files in {gdir}. "
            "Use --fetch or download them."
        )

    names = [
        v for v in (
            "SoilMoi0_10cm_inst", "SoilMoi10_40cm_inst",
            "SoilMoi40_100cm_inst", "SoilMoi100_200cm_inst",
            "SWE_inst", "CanopInt_inst"
        )
        if v in ds
    ]
    print(
        "GLDAS storage variables used:", names,
        "| all:", list(ds.data_vars)[:12]
    )
    if not names:
        raise SystemExit(
            "Expected GLDAS Noah 2.1 variable names not found; "
            "send me the variable list above."
        )

    tot = sum(ds[v] for v in names).transpose("time", "lat", "lon")
    u = units()
    parts = []

    for i in range(0, tot.sizes["time"], 24):
        parts.append(
            to_units(
                tot.isel(time=slice(i, i + 24)).values / 10,
                tot["lat"].values,
                tot["lon"].values,
                u
            )
        )  # kg/m2 -> cm

    gl = pd.concat(parts)
    gl.index = (
        pd.DatetimeIndex(tot["time"].values)
        .to_period("M")
        .to_timestamp()
    )
    gl = gl - gl.loc["2004-01":"2009-12"].mean()

    g = pd.read_csv(
        f"{V}/grace_lwe/series.csv",
        index_col=0,
        parse_dates=True
    )
    g.columns = [int(c) for c in g.columns]
    g.index = g.index.to_period("M").to_timestamp()

    cols = [c for c in g.columns if c in gl.columns]
    gw = (g[cols] - gl[cols].reindex(g.index)).dropna(how="all")

    with open(f"{V}/grace_lwe/meta.json") as f:
        gap = tuple(json.load(f)["gap"])

    add_var(
        "GW_ANOM",
        gw,
        coords_of(u),
        "GRACE minus GLDAS-Noah 2.1 soil moisture+snow+canopy "
        "(GES DISC), anomalies vs 2004-2009",
        jobs,
        gap
    )


def burned(nc, var, start=2002, end=2025, jobs=1):
    import xarray as xr

    da = xr.open_dataset(nc)[var].transpose("time", "lat", "lon")
    u = units()

    t = pd.concat([
        to_units(
            da.isel(time=slice(i, i + 24)).values,
            da["lat"].values,
            da["lon"].values,
            u
        )
        for i in range(0, da.sizes["time"], 24)
    ])

    t.index = (
        pd.DatetimeIndex(da["time"].values)
        .to_period("M")
        .to_timestamp()
    )
    t = t.loc[f"{start}":f"{end}"]
    t = t.loc[:, t.sum() > 0]

    add_var(
        "BURNED_AREA",
        t,
        coords_of(u),
        f"Burned area, {os.path.basename(nc)} ({var})",
        jobs
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    cpu = max(1, (os.cpu_count() or 2) - 1)

    sub.add_parser("register-grace")

    p = sub.add_parser("power")
    p.add_argument("--stride", type=int, default=2)
    p.add_argument("--include-ice", action="store_true")

    f = sub.add_parser("fires")
    f.add_argument("--csv", nargs="*")
    f.add_argument("--map-key")
    f.add_argument("--bbox", nargs=4, type=float)

    g = sub.add_parser("groundwater")
    g.add_argument("--dir", default="data/gldas")
    g.add_argument("--fetch", action="store_true")

    b = sub.add_parser("burned")
    b.add_argument("--nc", required=True)
    b.add_argument("--var", required=True)

    for x in (p, f, g, b):
        x.add_argument("--start", type=int, default=2002)
        x.add_argument("--end", type=int, default=2025)
        x.add_argument("--jobs", type=int, default=cpu)

    a = ap.parse_args()

    if a.cmd == "register-grace":
        register_grace()
    elif a.cmd == "power":
        power_features(
            a.stride, a.start, a.end, a.jobs, a.include_ice
        )
    elif a.cmd == "groundwater":
        groundwater(a.dir, a.fetch, a.start, a.end, a.jobs)
    elif a.cmd == "burned":
        burned(a.nc, a.var, a.start, a.end, a.jobs)
    else:
        if not a.csv and not (a.map_key and a.bbox):
            raise SystemExit(
                "Give --csv FILES or --map-key KEY with --bbox W S E N"
            )
        fires(a.csv, a.map_key, a.bbox, a.start, a.end, a.jobs)