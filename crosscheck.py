"""Independent cross-check: re-test our trends on a monthly time series that you export from one of NASA's own
time-series tools (Giovanni, GES DISC Hydrology Time Series) or from KNMI Climate Explorer, then compare with ours.
Used by pages/cross_check.py. Real exported data only; nothing is fetched automatically."""
import datetime, os, re, numpy as np, pandas as pd
import counterpoint as cp
O = "output"; NOGAP = (1e9, 1e9+1)


def parse_series(text):
    """Monthly series from a Hydrology Time Series (Data Rods) text file, a Giovanni CSV, or a KNMI Climate Explorer text export."""
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

def compare(our, ref):
    """Run our trend engine, unchanged, on both series and compare direction, interval overlap and year-to-year agreement."""
    a, b = cp.analyse(our, NOGAP), cp.analyse(ref, NOGAP)
    if not a or not b: return None
    xa, ya = cp.annual(our); xb, yb = cp.annual(ref); common = np.intersect1d(xa, xb)
    r = float(np.corrcoef(ya[np.isin(xa, common)], yb[np.isin(xb, common)])[0, 1]) if len(common) >= 5 else float("nan")
    return dict(our_slope=a["slope"], our_lo=a["lo"], our_hi=a["hi"], our_p=a["p"], ref_slope=b["slope"], ref_lo=b["lo"], ref_hi=b["hi"], ref_p=b["p"],
                same_sign=bool(np.sign(a["slope"]) == np.sign(b["slope"])), ci_overlap=bool(a["lo"] <= b["hi"] and b["lo"] <= a["hi"]), annual_r=r, n_years=int(len(common)))

def save(row, path=f"{O}/crosscheck.csv"):
    """Append one comparison to output/crosscheck.csv (replaces an earlier row for the same tool, feature and point)."""
    os.makedirs(O, exist_ok=True); df = pd.DataFrame([row])
    if os.path.exists(path):
        old = pd.read_csv(path); key = ["tool", "feature", "unit_lat", "unit_lon"]
        if all(c in old.columns for c in key): old = old[~(old[key].astype(str).agg("|".join, axis=1) == df[key].astype(str).agg("|".join, axis=1).iloc[0])]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(path, index=False); return df
