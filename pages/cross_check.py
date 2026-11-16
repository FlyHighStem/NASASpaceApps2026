import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import counterpoint as cp
import crosscheck as xc
import features as ft
import pipeline

PROJECT_DIR = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_DIR)

st.set_page_config(page_title="Cross-check | Counterpoint", page_icon="🔁", layout="wide")
css_path = PROJECT_DIR / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

if st.button("← Back to Main Dashboard", key="back_home"):
    st.switch_page("home.py")


def explain(what, why):
    st.markdown(
        "<div style='background:rgba(255,255,255,.85);border-left:4px solid #2563A6;border-radius:8px;"
        "padding:10px 14px;margin:2px 0 16px 0;font-size:14px;line-height:1.5;color:#1E293B'>"
        f"<b>What you&rsquo;re seeing:</b> {what}<br><b>Why it matters:</b> {why}</div>",
        unsafe_allow_html=True,
    )


st.title("🔁 Independent cross-check")
st.markdown(
    "Our trends could be an artefact of one data source or one method. Here you export a monthly time series "
    "for one point from NASA and KNMI time-series tools and upload it. The **same trend engine, unchanged,** is run on "
    "your file and compared with our result at that location."
)

with st.expander("How to get a file (about two minutes)", expanded=True):
    st.markdown(
        """
        1. Open one of the tools:
           [Giovanni](https://giovanni.gsfc.nasa.gov/),
           [Hydrology Time Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series)
           (GES DISC) or [KNMI Climate Explorer](https://climexp.knmi.nl/).
        2. Choose a **monthly** variable that matches one of our features, for example monthly precipitation
           (GLDAS-Noah or MERRA-2) for our precipitation feature, or monthly air temperature for temperature.
        3. Pick one point (a latitude and longitude) in a region of interest and use the longest period
           the tool offers (our features run from 2002).
        4. Download the time series as CSV or text, then upload it below with the same latitude and longitude.
        5. If the units differ from ours (precipitation: our unit is mm/day, and kg m-2 s-1 times 86400 gives mm/day),
           enter the conversion in "Multiply your values by". Only the trend is compared, so a constant offset
           (for example kelvin versus degrees Celsius) does not matter.

        The menu names on those sites change from time to time, so follow the tool's own labels.
        """
    )

# ---------------- saved comparisons
fn = Path("output/crosscheck.csv")
if fn.exists() and fn.stat().st_size > 5:
    try:
        df = pd.read_csv(fn)
    except Exception:
        df = pd.DataFrame()
else:
    df = pd.DataFrame()
if not df.empty and {"same_sign", "annual_r"} <= set(df.columns):
    st.header("Saved comparisons")
    c1, c2, c3 = st.columns(3)
    c1.metric("Comparisons", len(df))
    c2.metric("Same direction", f"{df.same_sign.mean():.0%}")
    c3.metric("Median year-to-year correlation", f"{df.annual_r.median():.2f}")
    cols = [c for c in ["tool", "feature", "unit_lat", "unit_lon", "our_slope", "ref_slope", "same_sign", "ci_overlap", "annual_r", "checked"] if c in df.columns]
    st.dataframe(df[cols].round(3), hide_index=True, width="stretch")
    st.download_button("Download crosscheck.csv", df.to_csv(index=False).encode("utf-8"), "crosscheck.csv", "text/csv", key="dl_cc")
    explain(
        "Each row is one file you uploaded, compared with our feature at the nearest unit. 'ci_overlap' says whether the two 95% intervals overlap; "
        "'annual_r' is the correlation of the two annual-mean series.",
        "Two independent sources agreeing on direction and year-to-year behaviour is evidence that our trends reflect the signal and not one dataset's quirks. "
        "Disagreements are saved and shown too.",
    )

# ---------------- compare an export
st.header("Compare an export")
feats = [k for k in ft.CATALOG if pipeline.has(k)]
if not feats:
    st.warning("No features loaded yet. Open the Home page and let the setup finish first.")
    st.stop()

tool = st.selectbox("Where is the file from?", ["Giovanni", "Hydrology Time Series (GES DISC)", "KNMI Climate Explorer", "AppEEARS", "Other"])
up = st.file_uploader("Time series file (CSV or text, monthly)", type=["csv", "txt", "asc", "dat"])
feat = st.selectbox("Compare with our feature", feats, format_func=lambda k: ft.CATALOG[k]["label"])
a, b, c = st.columns(3)
lat = a.number_input("Latitude of your series", -90.0, 90.0, 28.0)
lon = b.number_input("Longitude of your series", -180.0, 180.0, 74.0)
mult = c.number_input("Multiply your values by", value=1.0, format="%.6g", help="Unit conversion, e.g. 86400 turns kg m-2 s-1 into mm/day")

if up and st.button("Compare"):
    try:
        ref = xc.parse_series(up.getvalue().decode("utf-8", "ignore")) * mult
        res = pd.read_csv(f"output/vars/{feat}/results.csv")
        D = cp.hav(lat, lon, res.lat.values, res.lon.values)
        i = int(D.argmin())
        if D[i] > 700:
            st.error(f"Our nearest {ft.CATALOG[feat]['label']} unit is {D[i]:.0f} km away; pick a closer point.")
            st.stop()
        ours = pd.read_csv(f"output/vars/{feat}/series.csv", index_col=0, parse_dates=True)[str(int(res.iloc[i].id))]
        cmp = xc.compare(ours, ref)
        if not cmp:
            st.error("Not enough years of overlap (need at least 10 annual means in both series).")
            st.stop()
        u = res.iloc[i]
        xc.save(dict(tool=tool, feature=feat, unit_id=int(u.id), unit_lat=round(float(u.lat), 3), unit_lon=round(float(u.lon), 3),
                     file=up.name, **cmp, checked=pd.Timestamp.now().strftime("%Y-%m-%d")))
        m1, m2, m3 = st.columns(3)
        m1.metric("Same direction", "Yes" if cmp["same_sign"] else "No")
        m2.metric("Intervals overlap", "Yes" if cmp["ci_overlap"] else "No")
        m3.metric("Annual correlation", f"{cmp['annual_r']:.2f}")
        st.table(pd.DataFrame(
            {"trend per year": [f"{cmp['our_slope']:.4g}", f"{cmp['ref_slope']:.4g}"],
             "95% interval": [f"{cmp['our_lo']:.3g} to {cmp['our_hi']:.3g}", f"{cmp['ref_lo']:.3g} to {cmp['ref_hi']:.3g}"],
             "Mann-Kendall p": [f"{cmp['our_p']:.3g}", f"{cmp['ref_p']:.3g}"]},
            index=[f"Ours ({ft.CATALOG[feat]['label']}, unit at {u.lat:.1f}, {u.lon:.1f})", f"{tool} file"]))
        xa, ya = cp.annual(ours)
        xb, yb = cp.annual(ref)
        z = lambda v: (v - v.mean()) / (v.std() or 1)
        fig = go.Figure([go.Scatter(x=xa, y=z(ya), mode="lines+markers", name="Ours"),
                         go.Scatter(x=xb, y=z(yb), mode="lines+markers", name=tool)])
        fig.update_layout(height=340, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(color="#000000"),
                          xaxis_title="year", yaxis_title="annual mean (standardized)")
        st.plotly_chart(fig, width="stretch")
        explain("Annual means of both series, each rescaled to zero mean and unit spread so they can share one axis despite different units.",
                "If the two lines rise and fall together, both sources see the same behaviour; the table says whether they also agree on the long-term trend. "
                "This comparison was saved to output/crosscheck.csv.")
        st.caption("Reload this page to see the updated list of saved comparisons.")
    except Exception as e:
        st.error(f"Could not use this file: {e}")

st.header("For your References field")
st.code("NASA Giovanni, https://giovanni.gsfc.nasa.gov/\n"
        "NASA GES DISC Hydrology Time Series, https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series\n"
        "KNMI Climate Explorer, https://climexp.knmi.nl/\n"
        "Used for independent cross-checks of our trends: a monthly series exported from the tool was re-tested with the same method and compared with ours.")