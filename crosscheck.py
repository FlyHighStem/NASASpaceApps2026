"""Independent cross-check: re-test our trends on a time series from NASA's own Hydrology Time Series service
(GES DISC Data Rods for Hydrology, GLDAS-Noah 2.1 monthly). Also parses exports from Giovanni and KNMI Climate Explorer.
  python crosscheck.py run        # compares our POWER precipitation and temperature trends at each benchmark region
Needs `features.py power` first. Real data only."""
import argparse, datetime, json, os, re, numpy as np, pandas as pd
import counterpoint as cp
O = "output"; V = f"{O}/vars"; NOGAP = (1e9, 1e9+1)
SRC = "NASA GES DISC Hydrology Time Series (GLDAS-Noah 2.1 monthly)"
RODS = "https://hydro1.gesdisc.eosdis.nasa.gov/daac-bin/access/timeseries.cgi"
# our feature -> (Hydrology Time Series variable, multiplier into our units)
PAIRS = {"PRECTOTCORR": ("GLDAS2:GLDAS_NOAH025_M_v2.1:Rainf_f_tavg", 86400.0),   # kg m-2 s-1 -> mm/day
         "T2M": ("GLDAS2:GLDAS_NOAH025_M_v2.1:Tair_f_inst", 1.0)}              # kelvin; only the trend is compared, offset is irrelevant

def parse_series(text):
    """Monthly series from a Data Rods .asc2, Giovanni CSV, or KNMI Climate Explorer text export."""
    rows = {}
    for line in text.splitlines():
        t = [x for x in re.split(r"[,\t; ]+", line.strip()) if x]
        if len(t) < 2 or t[0].startswith("#"): continue
        try:
            if len(t) >= 13 and re.fullmatch(r"\d{4}", t[0]):                       # KNMI: year then 12 monthly values
                for m in range(1, 13):
                    v = float(t[m])
                    if v > -900: rows[pd.Timestamp(int(t[0]), m, 1)] = v
                continue
            if len(t) >= 3 and re.fullmatch(r"\d{4}", t[0]) and re.fullmatch(r"\d{1,2}", t[1]) and 1 <= int(t[1]) <= 12: d, v = pd.Timestamp(int(t[0]), int(t[1]), 1), float(t[2])
            elif re.match(r"\d{4}-\d{2}-\d{2}", t[0]): d, v = pd.Timestamp(t[0][:10]), float(t[1])
            else: continue
        except ValueError: continue
        if v > -900: rows[d] = v
    s = pd.Series(rows, dtype=float).sort_index()
    if len(s) < 24: raise ValueError(f"only {len(s)} data rows could be read; is this a monthly time series?")
    return s.resample("MS").mean()

def fetch_rods(lat, lon, var, start, end):
    import requests
    url = f"{RODS}?variable={var}&startDate={start}-01-01T00&endDate={end}-12-31T23&location=GEOM:POINT({lon},%20{lat})&type=asc2"
    r = requests.get(url, timeout=180); r.raise_for_status(); return r.text

def compare(our, ref):
    """Run our trend engine, unchanged, on both series and compare direction, interval overlap and year-to-year agreement."""
    a, b = cp.analyse(our, NOGAP), cp.analyse(ref, NOGAP)
    if not a or not b: return None
    xa, ya = cp.annual(our); xb, yb = cp.annual(ref); common = np.intersect1d(xa, xb)
    r = float(np.corrcoef(ya[np.isin(xa, common)], yb[np.isin(xb, common)])[0, 1]) if len(common) >= 5 else float("nan")
    return dict(our_slope=a["slope"], our_lo=a["lo"], our_hi=a["hi"], our_p=a["p"], ref_slope=b["slope"], ref_lo=b["lo"], ref_hi=b["hi"], ref_p=b["p"],
                same_sign=bool(np.sign(a["slope"]) == np.sign(b["slope"])), ci_overlap=bool(a["lo"] <= b["hi"] and b["lo"] <= a["hi"]), annual_r=r, n_years=int(len(common)))

def run(start=2002, end=2025):
    bench = json.load(open("data/benchmark_regions.json"))["regions"]; rows = []; os.makedirs(f"{O}/cache", exist_ok=True)
    for feat, (rv, mult) in PAIRS.items():
        d = f"{V}/{feat}"
        if not os.path.exists(f"{d}/results.csv"): print(f"skip {feat}: not loaded (run features.py power first)"); continue
        res = pd.read_csv(f"{d}/results.csv"); ser = pd.read_csv(f"{d}/series.csv", index_col=0, parse_dates=True)
        for b in bench:
            D = cp.hav(np.mean(b["lat"]), np.mean(b["lon"]), res.lat.values, res.lon.values); i = int(D.argmin())
            if D[i] > 700: continue
            u = res.iloc[i]; fn = f"{O}/cache/rods_{feat}_{u.lat:.2f}_{u.lon:.2f}_{start}_{end}.txt"
            try:
                txt = open(fn).read() if os.path.exists(fn) else fetch_rods(u.lat, u.lon, rv, start, end)
                ref = parse_series(txt) * mult; open(fn, "w").write(txt)           # cache only responses that parsed
                c = compare(ser[str(int(u.id))], ref)
            except Exception as e: print(f"  {b['name']} / {feat}: failed ({e})"); continue
            if c: rows.append(dict(region=b["name"], feature=feat, unit_id=int(u.id), lat=u.lat, lon=u.lon, **c, source=SRC, variable=rv, checked=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")))
    if not rows: raise SystemExit("No comparisons completed. Open the service URL for one point in a browser to check it still answers.")
    df = pd.DataFrame(rows); df.to_csv(f"{O}/crosscheck.csv", index=False)
    print(f"{len(df)} comparisons | same direction: {df.same_sign.mean():.0%} | intervals overlap: {df.ci_overlap.mean():.0%} | median annual r: {df.annual_r.median():.2f}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True); r = sub.add_parser("run"); r.add_argument("--start", type=int, default=2002); r.add_argument("--end", type=int, default=2025)
    a = ap.parse_args(); run(a.start, a.end)