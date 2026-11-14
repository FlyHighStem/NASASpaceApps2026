"""Counterpoint: Earth System Trend Detective (Mirror Trends + Evidence Grade).
CLI: python counterpoint.py demo | run --grace FILE.nc [--var lwe_thickness] [--driver]
Everything is computed from the data file you give it. `demo` is SYNTHETIC and says so."""
import argparse, json, hashlib, numpy as np, pandas as pd, scipy.stats as st

GAP = (2017.5, 2018.4)   # GRACE -> GRACE-FO gap (decimal years); edit for other missions
Q, MINWIN, MAXKM = 0.10, 10, 6000

def mk(y):
    """Mann-Kendall, tie-corrected. Returns S, z, p."""
    y = np.asarray(y, float); n = len(y)
    s = np.sign(y[None, :] - y[:, None])[np.triu_indices(n, 1)].sum()
    _, c = np.unique(y, return_counts=True)
    v = (n*(n-1)*(2*n+5) - (c*(c-1)*(2*c+5)).sum())/18
    z = 0 if s == 0 else (s-np.sign(s))/np.sqrt(v)
    return s, z, 2*(1-st.norm.cdf(abs(z))), v

def sen(x, y, v=None):
    """Theil-Sen slope with Sen/Gilbert 95% CI."""
    i, j = np.triu_indices(len(x), 1)
    sl = np.sort((y[j]-y[i])/(x[j]-x[i])); N = len(sl)
    if v is None: v = mk(y)[3]
    C = 1.96*np.sqrt(v); lo = int(max(0, np.floor((N-C)/2)-1)); hi = int(min(N-1, np.ceil((N+C)/2)))
    return np.median(sl), sl[lo], sl[hi]

def annual(series):
    """Deseasonalise monthly series (index = datetime), return annual means (years with >=9 months)."""
    s = series.dropna(); s = s - s.groupby(s.index.month).transform("mean")
    g = s.groupby(s.index.year); a = g.mean()[g.count() >= 9]
    return a.index.values.astype(float), a.values

def analyse(series):
    x, y = annual(series)
    if len(x) < MINWIN: return None
    s, z, p, v = mk(y); b, lo, hi = sen(x, y, v)
    se = (hi-lo)/(2*1.96)
    # robustness: share of windows (>=MINWIN yrs) with same sign as full-record slope
    same = tot = 0
    for i in range(len(x)):
        for j in range(i+MINWIN-1, len(x)):
            same += np.sign(sen(x[i:j+1], y[i:j+1])[0]) == np.sign(b); tot += 1
    # step test at the instrument gap: trend + step regression
    step_p = np.nan
    if x.min() < GAP[0] and x.max() > GAP[1]:
        X = np.c_[np.ones_like(x), x-x.mean(), (x > GAP[1]).astype(float)]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None); r = y-X@beta
        cov = r@r/(len(y)-3)*np.linalg.inv(X.T@X)
        step_p = 2*(1-st.t.cdf(abs(beta[2]/np.sqrt(cov[2, 2])), len(y)-3))
    return dict(slope=b, lo=lo, hi=hi, se=se, p=p, robust=same/tot, step_p=step_p, n_years=len(x))

def bh(p, q=Q):
    p = np.asarray(p); o = np.argsort(p); m = len(p)
    adj = np.minimum.accumulate((p[o]*m/np.arange(1, m+1))[::-1])[::-1]
    out = np.empty(m); out[o] = np.minimum(adj, 1); return out

def grade(r):
    if r["step_p"] < 0.01: return "D"          # step at record gap: possible instrument artifact
    if r["q"] >= Q: return "C"                  # indistinguishable from noise
    return "A" if r["robust"] >= 0.8 else "B"   # robust / fragile

def analyse_all(table):
    """table: DataFrame (time x unit) + dict of unit coordinates -> results DataFrame."""
    rows = []
    for k in table.columns:
        r = analyse(table[k])
        if r: rows.append(dict(id=k, **r))
    df = pd.DataFrame(rows); df["q"] = bh(df["p"].values)
    df["grade"] = df.apply(grade, axis=1); df["sign"] = np.sign(df["slope"]); return df

def hav(a, b, c, d):
    a, b, c, d = map(np.radians, (a, b, c, d))
    return 6371*2*np.arcsin(np.sqrt(np.sin((c-a)/2)**2+np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2))

def mirror_pairs(df, coords):
    g = df[df.grade.isin(["A", "B"])].copy(); g["lat"] = g.id.map(lambda k: coords[k][0]); g["lon"] = g.id.map(lambda k: coords[k][1])
    pos, neg = g[g.sign > 0], g[g.sign < 0]; out = []
    for _, a in pos.iterrows():
        for _, b in neg.iterrows():
            d = hav(a.lat, a.lon, b.lat, b.lon)
            if d <= MAXKM:
                out.append(dict(up=a.id, down=b.id, km=round(d), up_slope=a.slope, down_slope=b.slope,
                                score=min(abs(a.slope)/a.se, abs(b.slope)/b.se)))
    return pd.DataFrame(out).sort_values("score", ascending=False) if out else pd.DataFrame()

def driver_series(lat, lon, start, end):
    """Annual precip (mm) at a point from Open-Meteo ERA5 archive (CC BY 4.0, non-NASA: list it in your submission)."""
    import requests
    r = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=60, params=dict(
        latitude=lat, longitude=lon, start_date=f"{start}-01-01", end_date=f"{end}-12-31",
        daily="precipitation_sum", timezone="GMT")).json()
    d = pd.Series(r["daily"]["precipitation_sum"], index=pd.to_datetime(r["daily"]["time"]))
    a = d.groupby(d.index.year).sum(); return a.index.values.astype(float), a.values

def driver_label(slope_target, x, y):
    """follows / opposes / no clear driver signal (association, never cause)."""
    _, _, p, v = mk(y); b = sen(x, y, v)[0]
    if p >= 0.10: return "no significant driver trend"
    return "follows driver" if np.sign(b) == np.sign(slope_target) else "opposes driver"

def load_grace(path, var="lwe_thickness"):
    import xarray as xr
    ds = xr.open_dataset(path); da = ds[var]
    lat, lon = ds["lat"].values, ds["lon"].values; lon = np.where(lon > 180, lon-360, lon)
    if "mascon_id" in ds: ids = ds["mascon_id"].values.ravel(); note = "native_mascon_id"
    else:
        LA, LO = np.meshgrid(lat, lon, indexing="ij"); ids = (np.floor(LA/3)*1000+np.floor(LO/3)).ravel(); note = "APPROXIMATE 3-degree blocks (no mascon id layer found)"
    v = da.transpose("time", "lat", "lon").values.reshape(da.sizes["time"], -1)
    df = pd.DataFrame(v, index=pd.to_datetime(da["time"].values)); df.columns = ids
    df = df.loc[:, ~pd.isna(df.columns)].T.groupby(level=0).mean().T
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    c = pd.DataFrame({"id": ids, "lat": LA.ravel(), "lon": np.tile(lon, len(lat))}).dropna().groupby("id").mean()
    return df, {k: (r.lat, r.lon) for k, r in c.iterrows()}, note

def demo_data(seed=0):
    """SYNTHETIC: planted +/- trends, noise, one gap artifact. For testing the pipeline only."""
    rng = np.random.default_rng(seed); t = pd.date_range("2002-04-01", "2025-12-01", freq="MS")
    yrs = (t.year+(t.month-1)/12).values; cols, co = {}, {}
    for i in range(60):
        lat, lon = -30+i % 10*6, -60+i//10*20; tr = 0.5 if i < 15 else (-0.5 if i < 30 else 0)
        y = tr*(yrs-2002)+2*np.sin(2*np.pi*yrs)+rng.normal(0, 2, len(t))
        if i in (40, 41, 42): y += 8*(yrs > 2018)
        y[(yrs > GAP[0]) & (yrs < GAP[1])] = np.nan; cols[i] = y; co[i] = (lat, lon)
    return pd.DataFrame(cols, index=t), co

def run(table, coords, driver=False, out="output"):
    import os; os.makedirs(out, exist_ok=True)
    df = analyse_all(table); df["lat"] = df.id.map(lambda k: coords[k][0]); df["lon"] = df.id.map(lambda k: coords[k][1])
    pairs = mirror_pairs(df, coords)
    if driver and len(pairs):
        for i, r in pairs.head(10).iterrows():
            for side in ("up", "down"):
                k = r[side]; x, y = driver_series(*coords[k], int(table.index.year.min()), int(table.index.year.max()))
                pairs.loc[i, side+"_driver"] = driver_label(df.set_index("id").loc[k, "slope"], x, y)
    df.to_csv(f"{out}/results.csv", index=False); pairs.to_csv(f"{out}/pairs.csv", index=False)
    print(df.grade.value_counts().to_dict()); print(pairs.head(10).to_string() if len(pairs) else "no mirror pairs")
    return df, pairs

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["demo", "run"])
    ap.add_argument("--grace"); ap.add_argument("--var", default="lwe_thickness"); ap.add_argument("--driver", action="store_true")
    a = ap.parse_args()
    if a.cmd == "demo": print("SYNTHETIC DEMO DATA"); run(*demo_data())
    else:
        t, c, note = load_grace(a.grace, a.var); print("grouping:", note); run(t, c, a.driver)
