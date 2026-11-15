import os, numpy as np, pandas as pd, streamlit as st, plotly.graph_objects as go
from pathlib import Path
import pipeline, counterpoint as cp, crosscheck as xc, features as ft
os.chdir(pipeline.ROOT)
st.set_page_config(layout="wide", page_title="Counterpoint | Cross-check")
css = Path(pipeline.ROOT) / "style.css"
if css.exists(): st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
if st.button("← Back to Main Dashboard", key="back_home"):
    st.switch_page("home.py")

def explain(what, why):
    st.markdown(f"<div style='background:rgba(255,255,255,.85);border-left:4px solid #2563A6;border-radius:8px;padding:10px 14px;margin:2px 0 16px 0;font-size:14px;line-height:1.5;color:#1E293B'>"
                f"<b>What you&rsquo;re seeing:</b> {what}<br><b>Why it matters:</b> {why}</div>", unsafe_allow_html=True)

st.title("Independent cross-check")
st.markdown("Our trends could be an artefact of one data source or one method. Here the **same trend engine, unchanged,** is run on independent time series from NASA's own tools "
            "(**Hydrology Time Series** at GES DISC, **Giovanni**) and from KNMI Climate Explorer, and the results are compared with ours.")

# ---------------- A. automated: Hydrology Time Series vs our NASA POWER series, at the benchmark regions
st.header("Automatic check: NASA Hydrology Time Series")
fn = "output/crosscheck.csv"
if os.path.exists(fn):
    df = pd.read_csv(fn); c1, c2, c3 = st.columns(3)
    c1.metric("Comparisons", len(df)); c2.metric("Same direction", f"{df.same_sign.mean():.0%}"); c3.metric("Median year-to-year correlation", f"{df.annual_r.median():.2f}")
    show = df[["region", "feature", "lat", "lon", "our_slope", "ref_slope", "same_sign", "ci_overlap", "annual_r"]].round(3)
    st.dataframe(show, hide_index=True)
    explain(f"For each benchmark region, our precipitation and temperature series (NASA POWER / MERRA-2) are compared with GLDAS-Noah series fetched live from the GES DISC Hydrology Time Series service at the same point. "
            "Slopes are in each series' own units per year; 'ci_overlap' says whether their 95% intervals overlap; 'annual_r' is the correlation of annual means.",
            "Two different NASA products agreeing on direction, size and year-to-year behaviour is evidence that our trends reflect the climate signal and not one model's quirks. Disagreements are shown on purpose.")
    st.caption(f"Source: {df.source.iloc[0]}, checked {df.checked.iloc[0]}.")
else:
    st.info("Not run yet. Run `python crosscheck.py run` (needs the NASA POWER layers first), or press the button to run it with the rest of the setup.")
    if st.button("Run the automatic check"): pipeline.start(force=True); st.rerun()

# ---------------- B. compare an export the user pulled by hand
st.header("Compare an export from Giovanni, Hydrology Time Series or KNMI")
st.caption("Pull one monthly time series for a point in the tool's website, download it, and upload it here. We run the same trend test on it and compare it with our feature at that location.")
feats = [k for k in ft.CATALOG if pipeline.has(k)]
if not feats: st.warning("No features loaded yet."); st.stop()
tool = st.selectbox("Where is the file from?", ["Giovanni", "Hydrology Time Series (GES DISC)", "KNMI Climate Explorer", "Other"])
up = st.file_uploader("Time series file (CSV or text, monthly)", type=["csv", "txt", "asc", "dat"])
feat = st.selectbox("Compare with our feature", feats, format_func=lambda k: ft.CATALOG[k]["label"])
a, b, c = st.columns(3)
lat = a.number_input("Latitude of your series", -90.0, 90.0, 28.0); lon = b.number_input("Longitude of your series", -180.0, 180.0, 74.0)
mult = c.number_input("Multiply your values by", value=1.0, format="%.6g", help="Unit conversion, e.g. 86400 turns kg m-2 s-1 into mm/day")
if up and st.button("Compare"):
    try:
        ref = xc.parse_series(up.getvalue().decode("utf-8", "ignore")) * mult
        res = pd.read_csv(f"output/vars/{feat}/results.csv"); D = cp.hav(lat, lon, res.lat.values, res.lon.values); i = int(D.argmin())
        if D[i] > 700: st.error(f"Our nearest {ft.CATALOG[feat]['label']} unit is {D[i]:.0f} km away; pick a closer point."); st.stop()
        ours = pd.read_csv(f"output/vars/{feat}/series.csv", index_col=0, parse_dates=True)[str(int(res.iloc[i].id))]; cmp = xc.compare(ours, ref)
        if not cmp: st.error("Not enough years of overlap (need at least 10)."); st.stop()
        m1, m2, m3 = st.columns(3); m1.metric("Same direction", "Yes" if cmp["same_sign"] else "No"); m2.metric("Intervals overlap", "Yes" if cmp["ci_overlap"] else "No"); m3.metric("Annual correlation", f"{cmp['annual_r']:.2f}")
        st.table(pd.DataFrame({"trend per year": [f"{cmp['our_slope']:.4g}", f"{cmp['ref_slope']:.4g}"], "95% interval": [f"{cmp['our_lo']:.3g} to {cmp['our_hi']:.3g}", f"{cmp['ref_lo']:.3g} to {cmp['ref_hi']:.3g}"],
                               "Mann-Kendall p": [f"{cmp['our_p']:.3g}", f"{cmp['ref_p']:.3g}"]}, index=[f"Ours ({ft.CATALOG[feat]['label']}, unit at {res.iloc[i].lat:.1f}, {res.iloc[i].lon:.1f})", f"{tool} file"]))
        xa, ya = cp.annual(ours); xb, yb = cp.annual(ref); z = lambda v: (v - v.mean()) / (v.std() or 1)
        fig = go.Figure([go.Scatter(x=xa, y=z(ya), mode="lines+markers", name="Ours"), go.Scatter(x=xb, y=z(yb), mode="lines+markers", name=tool)])
        fig.update_layout(height=340, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(color="#000000"), xaxis_title="year", yaxis_title="annual mean (standardized)"); st.plotly_chart(fig, width="stretch")
        explain("Annual means of both series, each rescaled to zero mean and unit spread so they can share one axis despite different units.",
                "If the two lines rise and fall together, both sources see the same climate behaviour; the table above says whether they also agree on the long-term trend.")
    except Exception as e: st.error(f"Could not use this file: {e}")

st.header("For your References field")
st.code("NASA GES DISC Hydrology Time Series (Data Rods for Hydrology), GLDAS-Noah 2.1 monthly, https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series : "
        "used for independent cross-checks of our precipitation and temperature trends.\nNASA Giovanni, https://giovanni.gsfc.nasa.gov/ (list only if you used it)\nKNMI Climate Explorer, https://climexp.knmi.nl/ (list only if you used it)")