# streamlit run app.py
import json, os, numpy as np, pandas as pd, streamlit as st, plotly.express as px, plotly.graph_objects as go
import counterpoint as cp, features as ft
import pipeline
os.chdir(pipeline.ROOT)                                   # run from the project folder no matter where streamlit was launched
O = "output"; V = f"{O}/vars"; CAT = ft.CATALOG
st.set_page_config(layout="wide", page_title="Counterpoint")

from pathlib import Path

def load_css():
    css_path = Path(__file__).parent / "style.css"
    with open(css_path, "r", encoding="utf-8") as file:
        st.markdown(
            f"<style>{file.read()}</style>",
            unsafe_allow_html=True
        )

load_css()

def style_plotly(fig):
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            color="#000000",
            family="sans-serif"
        ),
        title_font=dict(color="#000000"),
        legend=dict(
            font=dict(color="#000000"),
            title_font=dict(color="#000000")
        ),
        xaxis=dict(
            tickfont=dict(color="#000000"),
            title_font=dict(color="#000000"),
            showline=True,
            linewidth=1,
            linecolor="#64748B",
            gridwidth=0.5,
            gridcolor="#E5E7EB"
        ),
        yaxis=dict(
            tickfont=dict(color="#000000"),
            title_font=dict(color="#000000"),
            showline=True,
            linewidth=1,
            linecolor="#64748B",
            gridwidth=0.5,
            gridcolor="#E5E7EB"
        ),
        coloraxis_colorbar=dict(
            tickfont=dict(color="#000000"),
            title_font=dict(color="#000000")
        )
    )

    return fig

pipeline.start()                                           # background setup: download, analyse, fetch features (skips finished steps)
if not pipeline.core_ready(): pipeline.render(st); st.stop()
avail = [k for k in CAT if os.path.exists(f"{V}/{k}/results.csv")]
if not avail: st.error("GRACE finished but no features were found. Check output/pipeline.log."); st.stop()

@st.cache_data
def load(k):
    rd = lambda n: pd.read_csv(f"{V}/{k}/{n}.csv") if os.path.getsize(f"{V}/{k}/{n}.csv") > 5 else pd.DataFrame()
    return rd("results"), pd.read_csv(f"{V}/{k}/series.csv", index_col=0, parse_dates=True), rd("regions"), rd("pairs"), json.load(open(f"{V}/{k}/meta.json"))
def nearest(k, lat, lon, maxkm=700):
    d = load(k)[0]; D = cp.hav(lat, lon, d.lat.values, d.lon.values); i = D.argmin()
    return (d.iloc[i], float(D[i])) if D[i] <= maxkm else (None, None)
PRESETS = {"World": None, "Africa": ([-38, 40], [-20, 55]), "Asia": ([-12, 60], [25, 150]), "Europe": ([34, 72], [-25, 45]), "North America": ([5, 75], [-170, -50]),
           "South America": ([-57, 15], [-85, -30]), "Oceania": ([-48, 0], [110, 180]), "Western USA": ([30, 52], [-125, -100]), "Mediterranean": ([30, 46], [-10, 40])}
arrow = lambda s: "↑ rising" if s > 0 else "↓ falling"

# ---- Sidebar filters
st.sidebar.header("Filters")
pipeline.sidebar_status(st, set(avail), set(CAT))
theme = st.sidebar.radio("Theme", ["Water", "Wildfire conditions"])
opts = [k for k in avail if CAT[k]["group"] == theme]
if not opts: st.warning(f"No {theme} features loaded yet (see README)."); st.stop()
feat = st.sidebar.selectbox("Feature", opts, format_func=lambda k: CAT[k]["label"]); C = CAT[feat]
grades = st.sidebar.multiselect("Evidence grade", list("ABCD"), ["A", "B"])
direction = st.sidebar.radio("Direction", ["Both", "Rising", "Falling"], horizontal=True)
region = st.sidebar.selectbox("Region", list(PRESETS)); box = PRESETS[region]
hide_ice = st.sidebar.checkbox("Hide Antarctica and Greenland", True)
pct = st.sidebar.slider("Colour range = percentile of trend size", 80, 100, 95)
df, series, R, P, meta = load(feat)
d = df[df.grade.isin(grades)]
if direction != "Both": d = d[d.sign > 0] if direction == "Rising" else d[d.sign < 0]
if hide_ice: d = d[~((d.lat < -60) | ((d.lat > 60) & (d.lon > -75) & (d.lon < -10)))]
if box: d = d[(d.lat >= box[0][0]) & (d.lat <= box[0][1]) & (d.lon >= box[1][0]) & (d.lon <= box[1][1])]

# ---- Header
st.title("Counterpoint: Earth System Trend Detective")
st.caption(f"{theme} | {C['label']} | {C['kind']} | {meta['source']} | fetched {meta['fetched'][:10]}")
st.markdown(f"**{C['label']}.** {C['desc']}  \nGrade **A** robust, **B** fragile, **C** indistinguishable from noise, **D** unreliable. Colour = trend in {C['unit']} (symmetric about zero; brown/red end = drying or warming, blue/green = wetting).")

# ---- Map (click a point to inspect it)
st.header("Map")
if d.empty: st.warning("No units match these filters."); st.stop()
m = max(float(np.percentile(d.slope.abs(), pct)), 1e-9)
fig = px.scatter_geo(d, lat="lat", lon="lon", color="slope", symbol="grade", custom_data=["id"], color_continuous_scale=C["cmap"], range_color=[-m, m],
                     hover_data={"id": True, "grade": True, "slope": ":.3g", "q": ":.3f", "robust": ":.0%", "lat": ":.1f", "lon": ":.1f"})
fig.update_traces(marker=dict(size=9, line=dict(width=0.4, color="#444")))

fig.update_geos(
    showland=True,
    landcolor="#FFFFFF",
    showocean=True,
    oceancolor="#D5F3FC",
    showcountries=True,
    countrycolor="#B9B9B9",
    countrywidth=0.8,
    coastlinecolor="#777777",
    coastlinewidth=0.8,
    showframe=False,
    **({"projection_type": "natural earth"} if box is None else {
        "projection_type": "equirectangular",
        "lataxis_range": box[0],
        "lonaxis_range": box[1]
    })
)

fig.update_layout(
    height=560,
    margin=dict(l=0, r=0, t=0, b=0),
    coloraxis_colorbar=dict(title=C["unit"]),
    uirevision=region
)

fig = style_plotly(fig)

ev = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points", key=f"map-{region}")
uid = None
try: uid = int(ev["selection"]["points"][0]["customdata"][0])
except Exception: pass
st.caption("Click a point to open its details and mirror cases below.")
c1, c2 = st.columns(2); c1.download_button("Download CSV", df.to_csv(index=False), f"{feat}_results.csv")
if feat == "grace_lwe" and os.path.exists(f"{O}/results.geojson"): c2.download_button("Download GeoJSON", open(f"{O}/results.geojson").read(), "counterpoint_results.geojson")
if uid is None:
    ids = d.sort_values("slope", key=abs, ascending=False).id.tolist(); uid = st.selectbox("...or pick a location (largest trends first)", ids)
r = df[df.id == uid].iloc[0]

# ---- Inspector
st.header(f"Trend details: {C['label']} at {r.lat:.1f}, {r.lon:.1f}")
word = "rising" if r.slope > 0 else "falling"
st.markdown(f"**{C['label']} is {word} by {abs(r.slope):.3g} {C['unit']}** (95% interval {r.lo:.3g} to {r.hi:.3g}). **Grade {r.grade}:** {r.reason}")

a, b = st.columns([2, 1])

s = series[str(uid)]
x, y = cp.annual(s)

sd = s.dropna()
sd = sd - sd.groupby(sd.index.month).transform("mean")

f2 = go.Figure()

f2.add_trace(go.Scatter(
    x=sd.index.year + (sd.index.month - 1) / 12,
    y=sd.values,
    mode="lines",
    name="monthly (deseasonalised)",
    line=dict(color="#AAB7C4", width=2)
))

f2.add_trace(go.Scatter(
    x=x,
    y=y,
    mode="markers+lines",
    name="annual mean",
    line=dict(width=2),
    marker=dict(size=6)
))

f2.add_trace(go.Scatter(
    x=x,
    y=np.median(y - r.slope * x) + r.slope * x,
    name="Theil-Sen trend",
    line=dict(width=2, dash="dash")
))

if feat == "grace_lwe" and "gap" in meta and x.min() < meta["gap"][0] and x.max() > meta["gap"][1]:
    f2.add_vrect(
        x0=meta["gap"][0],
        x1=meta["gap"][1],
        fillcolor="grey",
        opacity=0.3,
        annotation_text="mission gap"
    )

f2.update_layout(
    height=340,
    xaxis_title="year",
    yaxis_title=C["unit"].split(" per")[0].split("/")[0]
)

f2 = style_plotly(f2)

a.plotly_chart(f2, width="stretch", key="trend-chart")

b.table(pd.DataFrame({"value": [f"{r.slope:.4g}", f"{r.lo:.4g} to {r.hi:.4g}", f"{r.p:.4g}", f"{r.q:.4f}", f"{r.robust:.0%}", f"{int(r.n_years)}", f"{r.step_p:.3g}" if pd.notna(r.step_p) else "n/a"]},
    index=["Trend slope", "95% interval", "Mann-Kendall p", "FDR q", "Windows agreeing", "Years used", "Gap-step p"]))
n = len(x); H = np.full((n, n), np.nan)
for i in range(n):
    for j in range(i+cp.MINWIN-1, n): H[i, j] = cp.sen(x[i:j+1], y[i:j+1])[0]

hm = max(np.nanpercentile(np.abs(H), 95), 1e-9)

heatmap = px.imshow(
    H,
    x=x,
    y=x,
    color_continuous_scale=C["cmap"],
    zmin=-hm,
    zmax=hm,
    labels=dict(
        x="end year",
        y="start year",
        color="trend"
    ),
    title="Does the trend depend on the years chosen? (slope for every start/end year, >=10 years)"
)

heatmap.update_layout(height=380)
heatmap = style_plotly(heatmap)

st.plotly_chart(
    heatmap,
    width="stretch",
    key="trend-heatmap"
)

st.subheader("All features at this location")
rows = []
for k in avail:
    q, km = nearest(k, r.lat, r.lon)
    if q is not None: rows.append({"feature": CAT[k]["label"], "trend": f"{q.slope:.3g} {CAT[k]['unit']}", "direction": arrow(q.slope) if q.grade in "AB" else "no clear trend", "grade": q.grade, "distance_km": round(km)})
st.dataframe(pd.DataFrame(rows), hide_index=True)

# ---- Mirror cases for this selection
st.header("Mirror cases for this trend")
region = None
if len(R):
    for _, g in R.iterrows():
        if str(uid) in str(g.members).split(";"): region = g; break
if region is None: st.info("This location is not part of an A/B region, so it has no mirror analysis. Pick an A or B point.")
else:
    pp = P[(P.up == region.region) | (P.down == region.region)] if len(P) else P
    st.write(f"This location belongs to region {int(region.region)} ({int(region.n)} mascon(s), {arrow(region.slope)}, grade {region.grade}).")
    if pp.empty: st.write("No opposite-sign A/B region within 6,000 km: no mirror case for this trend.")
    else:
        pp = pp.assign(partner=np.where(pp.up == region.region, pp.down, pp.up)); Rr = R.set_index("region")
        pick = st.selectbox("Mirror partner (best-supported first)", pp.partner.tolist(), format_func=lambda i: f"region {int(i)} at {Rr.loc[i,'lat']:.1f}, {Rr.loc[i,'lon']:.1f} ({arrow(Rr.loc[i,'slope'])})")
        o = Rr.loc[pick]; km = float(pp[pp.partner == pick].km.iloc[0])
        st.write(f"**{CAT[feat]['label']} moves {arrow(region.slope)} here and {arrow(o.slope)} {km:.0f} km away** (partner grade {o.grade}, slope {o.slope:.3g}).")
        mp = px.scatter_geo(pd.DataFrame({"lat": [region.lat, o.lat], "lon": [region.lon, o.lon], "side": ["selected", "mirror partner"]}), lat="lat", lon="lon", color="side")
        
        mp.update_traces(marker=dict(size=12))

        mp.update_geos(
            fitbounds="locations",
            showland=True,
            landcolor="#FFFFFF",
            showocean=True,
            oceancolor="#D5F3FC",
            showcountries=True,
            countrycolor="#B9B9B9"
        )

        mp.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )

        mp = style_plotly(mp)
        st.plotly_chart(mp, width="stretch", key="mirror-map")
        rows = []
        for k in avail:
            if k == feat: continue
            q1, _ = nearest(k, region.lat, region.lon); q2, _ = nearest(k, o.lat, o.lon)
            if q1 is None or q2 is None: continue
            c1_, c2_ = q1.grade in "AB", q2.grade in "AB"
            verdict = ("ALSO MIRRORS: opposite directions" if c1_ and c2_ and q1.sign != q2.sign else "same direction on both sides" if c1_ and c2_ else "trend clear on one side only" if c1_ or c2_ else "no clear trend")
            rows.append({"feature": CAT[k]["label"], "here": arrow(q1.slope) if c1_ else "no clear trend", "partner": arrow(q2.slope) if c2_ else "no clear trend", "reading": verdict})
        st.markdown("**Which other features mirror too?** A feature that splits the same way is a candidate explanation (association only, never proof of cause).")
        st.dataframe(pd.DataFrame(rows), hide_index=True)

# ---- Benchmark + methods
if os.path.exists(f"{O}/benchmark.csv") and os.path.exists(f"{O}/sources.json"):
    sm = json.load(open(f"{O}/sources.json")); st.header("Benchmark scorecard (GRACE)")
    (st.success if sm.get("benchmark_frozen") else st.warning)(("Region list FROZEN" if sm.get("benchmark_frozen") else "NOT frozen: exploratory") + f" | SHA-256 {sm.get('benchmark_sha256')}")
    st.dataframe(pd.read_csv(f"{O}/benchmark.csv")); st.caption("Misses and contradictions are shown on purpose.")
st.header("Methods and limits")
st.markdown("""Annual means of deseasonalised monthly series; tie-corrected Mann-Kendall; Theil-Sen slope with 95% interval; Benjamini-Hochberg FDR (q=0.10) across units of each feature;
robustness = share of start/end windows (>=10 yrs) with the same sign; step test at the GRACE gap (grade D). Mirror cases: adjacent same-sign A/B units merge into regions; opposite-sign regions within 6,000 km pair up.
**Limits:** GRACE = total water storage, not groundwater alone; ~3 degree resolution. Precipitation, soil wetness, humidity, wind and temperature are MERRA-2 reanalysis (a model constrained by observations), not direct measurements.
Fire counts are MODIS detections, not burned area, and are affected by cloud cover. About two decades can mistake natural cycles for trends. Everything is association, not cause.""")

# ---- Bottom navigation
st.markdown("---")

nav1, nav2 = st.columns(2)

with nav1:
    if st.button(
        "📊 Explore Our Data",
        key="data_button",
        use_container_width=True
    ):
        st.switch_page("pages/data.py")

with nav2:
    if st.button(
        "🌎 Meet the Team & View Credits",
        key="credits_button",
        use_container_width=True
    ):
        st.switch_page("pages/credits.py")
