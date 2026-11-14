"""Counterpoint: Earth System Trend Detective (Mirror Trends + Evidence Grade).


def mk(y):
    v = (n*(n-1)*(2*n+5) - (c*(c-1)*(2*c+5)).sum())/18

def sen(x, y, v=None):
    """Theil-Sen slope with Sen/Gilbert 95% CI."""
    if v is None: v = mk(y)[3]
    C = 1.96*np.sqrt(v); lo = int(max(0, np.floor((N-C)/2)-1)); hi = int(min(N-1, np.ceil((N+C)/2)))
    return np.median(sl), sl[lo], sl[hi]

def annual(series):
    s = series.dropna(); s = s - s.groupby(s.index.month).transform("mean")
    g = s.groupby(s.index.year); a = g.mean()[g.count() >= 9]
    return a.index.values.astype(float), a.values

    if len(x) < MINWIN: return None
    for i in range(len(x)):
        for j in range(i+MINWIN-1, len(x)):
            same += np.sign(sen(x[i:j+1], y[i:j+1])[0]) == np.sign(b); tot += 1
    step_p = np.nan
        beta, *_ = np.linalg.lstsq(X, y, rcond=None); r = y-X@beta
        cov = r@r/(len(y)-3)*np.linalg.inv(X.T@X)
        step_p = 2*(1-st.t.cdf(abs(beta[2]/np.sqrt(cov[2, 2])), len(y)-3))
    return dict(slope=b, lo=lo, hi=hi, se=se, p=p, robust=same/tot, step_p=step_p, n_years=len(x))

    p = np.asarray(p); o = np.argsort(p); m = len(p)
    adj = np.minimum.accumulate((p[o]*m/np.arange(1, m+1))[::-1])[::-1]
    out = np.empty(m); out[o] = np.minimum(adj, 1); return out

def grade(r):

    df = pd.DataFrame(rows); df["q"] = bh(df["p"].values)

def hav(a, b, c, d):
    a, b, c, d = map(np.radians, (a, b, c, d))
    return 6371*2*np.arcsin(np.sqrt(np.sin((c-a)/2)**2+np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2))

            d = hav(a.lat, a.lon, b.lat, b.lon)
                                           score=min(abs(a.slope)/a.se, abs(b.slope)/b.se)))

    import requests


def load_grace(path, var="lwe_thickness"):
    import xarray as xr
    ds = xr.open_dataset(path); da = ds[var]


            for side in ("up", "down"):

if __name__ == "__main__":
