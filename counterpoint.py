"""Counterpoint: Earth System Trend Detective (Mirror Trends + Evidence Grade).
REAL DATA ONLY in the app. `validate` is labelled SYNTHETIC CALIBRATION and never feeds the app's results.
CLI: fetch | run --grace FILE.nc | power | validate"""
import argparse, json, hashlib, os, datetime, functools, numpy as np, pandas as pd, scipy.stats as st

GAP = (2017.5, 2018.4)            # GRACE -> GRACE-FO gap (decimal years)
Q, MINWIN, MAXKM, LINK_KM = 0.10, 10, 6000, 500
_GAP = GAP
def _init(g):
    global _GAP; _GAP = g

@functools.lru_cache(None)
def _tri(n): return np.triu_indices(n, 1)

def mk(y):
    """Mann-Kendall, tie-corrected: S, z, p, var(S)."""
    y = np.asarray(y, float); n = len(y); i, j = _tri(n)
    s = np.sign(y[j]-y[i]).sum(); _, c = np.unique(y, return_counts=True)
    v = (n*(n-1)*(2*n+5) - (c*(c-1)*(2*c+5)).sum())/18
    z = 0 if s == 0 else (s-np.sign(s))/np.sqrt(v); return s, z, 2*(1-st.norm.cdf(abs(z))), v

def sen(x, y, v=None):
    """Theil-Sen slope with Sen/Gilbert 95% CI."""
    i, j = _tri(len(x)); sl = np.sort((y[j]-y[i])/(x[j]-x[i])); N = len(sl)
    if v is None: v = mk(y)[3]
    C = 1.96*np.sqrt(v); lo = int(max(0, np.floor((N-C)/2)-1)); hi = int(min(N-1, np.ceil((N+C)/2)))
    return np.median(sl), sl[lo], sl[hi]

def annual(series):
    """Deseasonalise monthly series, return annual means (years with >=9 months)."""
    s = series.copy()
    s.index = pd.DatetimeIndex(pd.to_datetime(s.index))
    s = s.dropna()
    s = s - s.groupby(s.index.month).transform("mean")
    g = s.groupby(s.index.year)
    a = g.mean()[g.count() >= 9]
    return a.index.values.astype(float), a.values

def analyse(series, gap=None):
    gap = gap or _GAP; x, y = annual(series)
    if len(x) < MINWIN: return None
    s, z, p, v = mk(y); b, lo, hi = sen(x, y, v); se = (hi-lo)/(2*1.96); same = tot = 0
    for i in range(len(x)):
        for j in range(i+MINWIN-1, len(x)):
            same += np.sign(sen(x[i:j+1], y[i:j+1])[0]) == np.sign(b); tot += 1
    step_p = np.nan
    if x.min() < gap[0] and x.max() > gap[1]:
        X = np.c_[np.ones_like(x), x-x.mean(), (x > gap[1]).astype(float)]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None); r = y-X@beta
        cov = r@r/(len(y)-3)*np.linalg.inv(X.T@X)
        step_p = 2*(1-st.t.cdf(abs(beta[2]/np.sqrt(cov[2, 2])), len(y)-3))
    return dict(slope=b, lo=lo, hi=hi, se=se, p=p, robust=same/tot, step_p=step_p, n_years=len(x))

def bh(p):
    p = np.asarray(p); o = np.argsort(p); m = len(p)
    adj = np.minimum.accumulate((p[o]*m/np.arange(1, m+1))[::-1])[::-1]
    out = np.empty(m); out[o] = np.minimum(adj, 1); return out

def grade(r):
    if r["step_p"] < 0.01: return "D", "A step at the instrument gap fits better than a steady trend (possible artifact)."
    if r["q"] >= Q: return "C", f"Not significant after multiple-testing control (q={r['q']:.2f}); indistinguishable from noise."
    if r["robust"] >= 0.8: return "A", f"Significant (q={r['q']:.3f}) and keeps its sign in {r['robust']:.0%} of start/end windows."
    return "B", f"Significant (q={r['q']:.3f}) but only {r['robust']:.0%} of start/end windows agree: fragile."

def _one(item): return analyse(item[1])

def grade_frame(rows):
    df = pd.DataFrame(rows); df["q"] = bh(df["p"].values)
    gr = df.apply(lambda r: pd.Series(grade(r), index=["grade", "reason"]), axis=1)
    df = pd.concat([df, gr], axis=1); df["sign"] = np.sign(df["slope"]); return df

def analyse_all(table, jobs=1, gap=None):
    gap = gap or GAP; items = [(k, table[k]) for k in table.columns]; res = []
    if jobs > 1:
        from multiprocessing import Pool
        with Pool(jobs, initializer=_init, initargs=(gap,)) as pool:
            for n, r in enumerate(pool.imap(_one, items, chunksize=16)):
                res.append(r)
                if n % 200 == 0: print(f"  analysed {n}/{len(items)}", flush=True)
    else:
        _init(gap); res = [_one(i) for i in items]
    return grade_frame([dict(id=k, **r) for (k, _), r in zip(items, res) if r])

def hav(a, b, c, d):
    a, b, c, d = map(np.radians, (a, b, c, d))
    return 6371*2*np.arcsin(np.sqrt(np.sin((c-a)/2)**2+np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2))

def build_regions(df, table):
    """Adjacent same-sign A/B mascons merge into regions; each region is re-tested as one series."""
    g = df[df.grade.isin(["A", "B"])].reset_index(drop=True)
    if g.empty: return pd.DataFrame()
    la, lo, sg = g.lat.values, g.lon.values, g.sign.values
    D = hav(la[:, None], lo[:, None], la[None, :], lo[None, :]); par = list(range(len(g)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i, j in np.argwhere((D < LINK_KM) & (sg[:, None] == sg[None, :])):
        if i < j: par[f(i)] = f(j)
    g["reg"] = [f(i) for i in range(len(g))]; rows = []
    for _, m in g.groupby("reg"):
        ids = list(m.id); a = analyse(table[ids].mean(axis=1))
        if a: rows.append(dict(region=len(rows), members=";".join(map(str, ids)), n=len(ids), lat=m.lat.mean(), lon=m.lon.mean(), **a))
    R = pd.DataFrame(rows)
    if R.empty: return R
    return grade_frame(R.to_dict("records")).assign(region=R.region.values, members=R.members.values, n=R.n.values, lat=R.lat.values, lon=R.lon.values)

def mirror_pairs(R):
    cols = ["up", "down", "km", "up_slope", "down_slope", "score"]
    if R is None or R.empty: return pd.DataFrame(columns=cols)
    g = R[R.grade.isin(["A", "B"])]; out = []
    for _, a in g[g.sign > 0].iterrows():
        for _, b in g[g.sign < 0].iterrows():
            d = hav(a.lat, a.lon, b.lat, b.lon)
            if d <= MAXKM: out.append(dict(up=a.region, down=b.region, km=round(float(d)), up_slope=a.slope, down_slope=b.slope,
                                           score=min(abs(a.slope)/a.se, abs(b.slope)/b.se)))
    return pd.DataFrame(out, columns=cols).sort_values("score", ascending=False)

def power_monthly(lat, lon, param, start, end):
    """Monthly series from NASA POWER (MERRA-2, no login)."""
    import requests
    r = requests.get("https://power.larc.nasa.gov/api/temporal/monthly/point", timeout=90, params=dict(
        parameters=param, community="AG", latitude=lat, longitude=lon, start=start, end=end, format="JSON"))
    r.raise_for_status(); d = r.json()["properties"]["parameter"][param]
    return pd.Series({pd.Timestamp(int(k[:4]), int(k[4:]), 1): v for k, v in d.items() if not k.endswith("13") and v > -900})

def power_annual(lat, lon, param, start, end):
    s = power_monthly(lat, lon, param, start, end); g = s.groupby(s.index.year).mean()
    return g.index.values.astype(float), g.values

def power_grid(bbox, step, param, start, end, workers=8):
    from concurrent.futures import ThreadPoolExecutor
    s_, n_, w_, e_ = bbox
    pts = [(la, lo) for la in np.arange(s_, n_+1e-9, step) for lo in np.arange(w_, e_+1e-9, step)]
    def one(p):
        try: return p, power_monthly(p[0], p[1], param, start, end)
        except Exception: return p, None
    with ThreadPoolExecutor(workers) as ex: res = list(ex.map(one, pts))
    ok = [(p, s) for p, s in res if s is not None and len(s) > 120]; print(f"fetched {len(ok)}/{len(pts)} points from NASA POWER")
    if not ok: raise SystemExit("No data fetched. Check internet access and parameter name.")
    return pd.DataFrame({i: s for i, (p, s) in enumerate(ok)}), {i: p for i, (p, s) in enumerate(ok)}

def driver_label(x, y, slope):
    """follows / opposes / unreliable (association only)."""
    _, _, p, v = mk(y)
    if p >= 0.10: return "unreliable"
    return "follows" if np.sign(sen(x, y, v)[0]) == np.sign(slope) else "opposes"

def verdict(a, b):
    if a == "unreliable" or b == "unreliable": return "The precipitation trend is not significant on one or both sides, so the driver check is inconclusive."
    if a == b == "follows": return "Storage follows precipitation on both sides, consistent with a rainfall-driven split (association, not cause)."
    if a == b == "opposes": return "Storage moves against precipitation on both sides, so rainfall does not explain the split; other drivers are possible (association, not cause)."
    side = "wetter-trend" if a == "opposes" else "drying-trend"
    return f"Only one side tracks precipitation; the {side} side moves against it, so rainfall explains the split only partly (association, not cause)."

def load_grace(path, var="lwe_thickness"):
    import xarray as xr
    ds = xr.open_dataset(path); da = ds[var]
    for d in ("time", "lat", "lon"):
        if d not in da.dims: raise SystemExit(f"Expected dims time/lat/lon, found {da.dims}. Tell me and I'll adjust.")
    da = da.transpose("time", "lat", "lon"); lat, lon = ds["lat"].values, ds["lon"].values; lon = np.where(lon > 180, lon-360, lon)
    LA, LO = np.meshgrid(lat, lon, indexing="ij"); LA, LO = LA.ravel(), LO.ravel()
    v = da.values.reshape(da.sizes["time"], -1)
    keep = ds["land_mask"].values.ravel() == 1 if "land_mask" in ds else np.ones(LA.size, bool)
    keep &= ~np.isnan(v).all(axis=0); v, LA, LO = v[:, keep], LA[keep], LO[keep]
    if "mascon_id" in ds: ids = ds["mascon_id"].values.ravel()[keep]; note = "native_mascon_id"
    else: ids = np.floor(LA/3)*1000+np.floor(LO/3); note = "APPROXIMATE 3-degree blocks (no mascon id layer found)"
    o = np.argsort(ids, kind="stable"); ids, v, LA, LO = ids[o], v[:, o], LA[o], LO[o]
    u, start = np.unique(ids, return_index=True); ok = ~np.isnan(v)
    sums = np.add.reduceat(np.where(ok, v, 0), start, axis=1); cnt = np.add.reduceat(ok.astype(float), start, axis=1)
    m = np.where(cnt > 0, sums/np.maximum(cnt, 1), np.nan); n = np.diff(np.append(start, len(ids)))
    clat, clon = np.add.reduceat(LA, start)/n, np.add.reduceat(LO, start)/n
    table = pd.DataFrame(m, index=pd.to_datetime(da["time"].values), columns=[int(i) for i in u])
    print(f"land units: {len(u)} | grouping: {note}"); return table, {int(i): (a, b) for i, a, b in zip(u, clat, clon)}, note

def benchmark(table, coords, path, gap):
    if not path or not os.path.exists(path): return None, None, None
    raw = open(path, "rb").read(); cfg = json.loads(raw); sha = hashlib.sha256(raw).hexdigest()
    ids = list(table.columns); la = np.array([coords[k][0] for k in ids]); lo = np.array([coords[k][1] for k in ids]); rows = []
    for r in cfg["regions"]:
        m = (la >= r["lat"][0]) & (la <= r["lat"][1]) & (lo >= r["lon"][0]) & (lo <= r["lon"][1])
        base = dict(name=r["name"], tier=r["tier"], expected=r["expected"], n_mascons=int(m.sum()))
        a = analyse(table[[ids[i] for i in np.where(m)[0]]].mean(axis=1), gap) if m.any() else None
        if a is None: rows.append(dict(base, result="no data in box")); continue
        sign = "up" if a["slope"] > 0 else "down"; sig = a["p"] < 0.05
        if r["expected"] == "none": res = "recovered (no significant trend)" if not sig else f"contradicted ({sign}, significant)"
        elif sig and sign == r["expected"]: res = "recovered"
        elif sig: res = f"contradicted (observed {sign})"
        else: res = "missed (not significant)"
        rows.append(dict(base, slope=a["slope"], p=a["p"], observed=sign, result=res))
    return pd.DataFrame(rows), sha, bool(cfg.get("frozen"))

def monthly_check(table, df):
    try: import pymannkendall as pmk
    except ImportError: return dict(skipped="pip install pymannkendall")
    n = agree = 0
    for _, r in df[df.grade.isin(["A", "B"])].iterrows():
        s = table[r.id].dropna(); s = s-s.groupby(s.index.month).transform("mean"); h = pmk.hamed_rao_modification_test(s.values)
        n += 1; agree += int(h.p < 0.05 and np.sign(h.slope) == r.sign)
    return dict(n=n, agree=agree, share=agree/n if n else None)

def to_geojson(df, path):
    cols = ["id", "slope", "lo", "hi", "p", "q", "robust", "grade", "reason"]; d = df[cols].astype(object).where(df[cols].notna(), None); feats = []
    for (_, r), (la, lo) in zip(d.iterrows(), zip(df.lat, df.lon)):
        ring = [[lo-1.5, la-1.5], [lo+1.5, la-1.5], [lo+1.5, la+1.5], [lo-1.5, la+1.5], [lo-1.5, la-1.5]]
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]}, "properties": r.to_dict()})
    json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"), default=lambda o: o.item())

def run(table, coords, source, out="output", jobs=1, gap=None, driver_var=None, monthly=False, bench=None, top=10):
    os.makedirs(out, exist_ok=True); gap = gap or GAP; _init(gap)
    print(f"{table.shape[1]} units; analysing with {jobs} process(es)...", flush=True)
    df = analyse_all(table, jobs, gap); df["lat"] = df.id.map(lambda k: coords[k][0]); df["lon"] = df.id.map(lambda k: coords[k][1])
    R = build_regions(df, table); P = mirror_pairs(R)
    if driver_var and len(P):
        P = P.head(top).copy(); Rr = R.set_index("region"); y0, y1 = int(table.index.year.min()), int(table.index.year.max())
        for i, r in P.iterrows():
            for side in ("up", "down"):
                try: x, y = power_annual(Rr.loc[r[side], "lat"], Rr.loc[r[side], "lon"], driver_var, y0, y1); lab = driver_label(x, y, Rr.loc[r[side], "slope"])
                except Exception as e: print("driver fetch failed:", e); lab = "unreliable"
                P.loc[i, side+"_driver"] = lab
            P.loc[i, "verdict"] = verdict(P.loc[i, "up_driver"], P.loc[i, "down_driver"])
    B, sha, frozen = benchmark(table, coords, bench, gap); mc = monthly_check(table, df) if monthly else None
    df.to_csv(f"{out}/results.csv", index=False); to_geojson(df, f"{out}/results.geojson"); table.round(3).to_csv(f"{out}/series.csv")
    R.to_csv(f"{out}/regions.csv", index=False); P.to_csv(f"{out}/pairs.csv", index=False)
    if B is not None: B.to_csv(f"{out}/benchmark.csv", index=False)
    json.dump(dict(source=source, driver=driver_var, fetched=datetime.datetime.utcnow().isoformat()+"Z", n_units=len(df), gap=list(gap),
                   period=[str(table.index.min().date()), str(table.index.max().date())], benchmark_sha256=sha, benchmark_frozen=frozen,
                   monthly_check=mc), open(f"{out}/sources.json", "w"), indent=2)
    print("REAL DATA:", source); print("grades:", df.grade.value_counts().to_dict(), "| regions:", len(R), "| pairs:", len(P))
    if B is not None: print(B[["name", "tier", "expected", "result"]].to_string(index=False)); print("benchmark frozen:", frozen, "sha256:", sha[:12])
    if len(P): print(P.head(5).to_string())

def validate(out="output", sims=300):
    """SYNTHETIC CALIBRATION: shows the method behaves as designed. Says nothing about GRACE."""
    os.makedirs(out, exist_ok=True); rng = np.random.default_rng(0); res = {"label": "SYNTHETIC CALIBRATION - NOT GRACE DATA"}
    def ar1(n, phi):
        e = rng.normal(size=n); y = np.empty(n); y[0] = e[0]
        for i in range(1, n): y[i] = phi*y[i-1]+e[i]
        return y
    t = pd.date_range("2002-04-01", "2025-12-01", freq="MS"); yrs = (t.year+(t.month-1)/12).values; cols = {}
    res["annual_MK_false_positive_rate_at_5pct (monthly AR(1) noise, annual means)"] = {str(p): float(np.mean([mk(annual(pd.Series(ar1(len(t), p), index=t))[1])[2] < 0.05 for _ in range(sims)])) for p in (0.3, 0.5, 0.7)}
    for i in range(140):
        y = 2*np.sin(2*np.pi*yrs)+ar1(len(t), 0.3)*2
        if 100 <= i < 120: y += 0.5*(yrs-2002)
        if i >= 120: y += 8*(yrs > 2018)
        y[(yrs > GAP[0]) & (yrs < GAP[1])] = np.nan; cols[i] = y
    df = analyse_all(pd.DataFrame(cols, index=t), 1, GAP).set_index("id"); g = df.grade
    res["noise_cells_graded_A_or_B"] = float(g.loc[:99].isin(["A", "B"]).mean()); res["planted_trends_graded_A"] = float((g.loc[100:119] == "A").mean())
    res["planted_gap_artifacts_graded_D"] = float((g.loc[120:] == "D").mean())
    json.dump(res, open(f"{out}/validation.json", "w"), indent=2); print(json.dumps(res, indent=2))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True); cpu = max(1, (os.cpu_count() or 2)-1)
    f = sub.add_parser("fetch"); f.add_argument("--short-name", default="TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4")
    r = sub.add_parser("run"); r.add_argument("--grace", required=True); r.add_argument("--var", default="lwe_thickness")
    r.add_argument("--driver-var", default=None); r.add_argument("--jobs", type=int, default=cpu); r.add_argument("--monthly-check", action="store_true")
    r.add_argument("--benchmark", default="data/benchmark_regions.json"); r.add_argument("--top", type=int, default=10)
    p = sub.add_parser("power"); p.add_argument("--bbox", nargs=4, type=float, default=[-40, 60, -20, 140]); p.add_argument("--step", type=float, default=10)
    p.add_argument("--var", default="T2M"); p.add_argument("--start", type=int, default=1995); p.add_argument("--end", type=int, default=2025)
    p.add_argument("--driver-var", default=None); p.add_argument("--jobs", type=int, default=cpu)
    sub.add_parser("validate"); a = ap.parse_args()
    if a.cmd == "fetch":
        import earthaccess; earthaccess.login(strategy="environment"); res = earthaccess.search_data(short_name=a.short_name); print(len(res), "granules"); earthaccess.download(res, "data/")
    elif a.cmd == "run":
        t, c, note = load_grace(a.grace, a.var)
        run(t, c, f"JPL GRACE/GRACE-FO mascons RL06.3 CRI, {os.path.basename(a.grace)} (cm LWE; {note})", jobs=a.jobs, driver_var=a.driver_var, monthly=a.monthly_check, bench=a.benchmark, top=a.top)
    elif a.cmd == "power":
        t, c = power_grid(a.bbox, a.step, a.var, a.start, a.end)
        run(t, c, f"NASA POWER monthly {a.var} (MERRA-2), {a.start}-{a.end}", jobs=a.jobs, gap=(1e9, 1e9+1), driver_var=a.driver_var)
    else: validate()
