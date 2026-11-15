# streamlit run app.py
import json, os, numpy as np, pandas as pd, streamlit as st, plotly.express as px, plotly.graph_objects as go
import counterpoint as cp, features as ft
import pipeline

os.chdir(pipeline.ROOT)  # run from the project folder no matter where streamlit was launched
O = "output";
V = f"{O}/vars";
CAT = ft.CATALOG
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

ACCENT = "#2563A6"  # cobalt blue (matches the buttons). For dark teal use "#0F766E"
st.markdown(f"""<style>
[data-baseweb="tag"] {{ background-color: {ACCENT} !important; }}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg {{ color: #FFFFFF !important; fill: #FFFFFF !important; }}
[data-testid="stSlider"] [role="slider"] {{ background-color: {ACCENT} !important; }}
[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{ color: {ACCENT} !important; }}
</style>""", unsafe_allow_html=True)


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


def explain(what, why):
    """Plain-language caption shown under a chart."""
    st.markdown(
        f"<div style='background:rgba(255,255,255,.85);border-left:4px solid #2563A6;border-radius:8px;padding:10px 14px;margin:2px 0 16px 0;font-size:14px;line-height:1.5;color:#1E293B'>"
        f"<b>What you&rsquo;re seeing:</b> {what}<br><b>Why it matters:</b> {why}</div>", unsafe_allow_html=True)


pipeline.start()  # background setup: download, analyse, fetch features (skips finished steps)
if not pipeline.core_ready(): pipeline.render(st); st.stop()
avail = [k for k in CAT if pipeline.has(k)]
if not avail: st.error("GRACE finished but no features were found. Check output/pipeline.log."); st.stop()


@st.cache_data
def load(k):
    rd = lambda n: pd.read_csv(f"{V}/{k}/{n}.csv") if os.path.getsize(f"{V}/{k}/{n}.csv") > 5 else pd.DataFrame()
    return rd("results"), pd.read_csv(f"{V}/{k}/series.csv", index_col=0, parse_dates=True), rd("regions"), rd(
        "pairs"), json.load(open(f"{V}/{k}/meta.json"))


def nearest(k, lat, lon, maxkm=700):
    d = load(k)[0];
    D = cp.hav(lat, lon, d.lat.values, d.lon.values);
    i = D.argmin()
    return (d.iloc[i], float(D[i])) if D[i] <= maxkm else (None, None)


def xrows(lat, lon):
    """Trend of every loaded feature at the nearest unit (within 700 km)."""
    out = []
    for k in avail:
        q, km = nearest(k, lat, lon)
        if q is not None: out.append(
            dict(key=k, label=CAT[k]["label"], unit=CAT[k]["unit"], slope=q.slope, sign=int(np.sign(q.slope)),
                 grade=q.grade, clear=q.grade in "AB", km=round(km)))
    return out


def find_region(R_, uid_):
    if len(R_):
        for _, g_ in R_.iterrows():
            if str(uid_) in str(g_.members).split(";"): return g_
    return None


def mirror_also(feat_, a_, b_):
    names = []
    for k in avail:
        if k == feat_: continue
        q1, _ = nearest(k, a_.lat, a_.lon);
        q2, _ = nearest(k, b_.lat, b_.lon)
        if q1 is not None and q2 is not None and q1.grade in "AB" and q2.grade in "AB" and q1.sign != q2.sign: names.append(
            CAT[k]["label"])
    return names


def causes(feat_, r_, X_):
    """Plain-English, rule-based hypotheses from the other features at this place. Association only."""
    s_ = int(np.sign(r_.slope));
    out = [];
    P_ = X_.get("PRECTOTCORR", {}).get("sign", 0)
    if r_.grade == "D": out.append(
        "Grade D: a step at the GRACE to GRACE-FO gap fits better than a steady trend, so this may be an instrument artifact rather than a real change.")
    if feat_ in ("grace_lwe", "GW_ANOM"):
        if s_ < 0 and P_ < 0:
            out.append(
                "Storage is falling and precipitation is falling too: consistent with drying driven by less rainfall.")
        elif s_ < 0:
            out.append("Storage is falling without a matching rainfall decline (" + (
                "rainfall is rising" if P_ > 0 else "no clear rainfall trend") + "). Rainfall alone does not explain it; groundwater pumping for irrigation, higher evaporation, or snow and ice loss are candidates.")
        elif s_ > 0 and P_ > 0:
            out.append("Storage is rising and precipitation is rising too: consistent with wetter conditions.")
        elif s_ > 0:
            out.append(
                "Storage is rising without more rainfall. Reservoirs, irrigation return flow, land-use change, or recovery after a past drought are candidates.")
        if X_.get("EVLAND", {}).get("sign", 0) > 0 and s_ < 0: out.append(
            "Evaporation is rising here too, which would drain storage.")
    else:
        pro = [x["label"] for k, x in X_.items() if
               CAT[k]["fire_dir"] and x["sign"] * CAT[k]["fire_dir"] > 0 and k != feat_]
        con = [x["label"] for k, x in X_.items() if
               CAT[k]["fire_dir"] and x["sign"] * CAT[k]["fire_dir"] < 0 and k != feat_]
        if pro: out.append("Moving in a fire-promoting direction here: " + ", ".join(pro) + ".")
        if con: out.append("Moving against fire risk here: " + ", ".join(con) + ".")
        if not pro and not con: out.append(
            "No other loaded feature shows a clear trend here, so the data cannot suggest a driver.")
    if r_.robust < 0.6: out.append(
        f"Only {r_.robust:.0%} of start/end windows agree on the sign, so natural variability (multi-year droughts, El Niño and La Niña) may be involved.")
    return out


GRADE_NAME = {"A": "robust", "B": "fragile", "C": "indistinguishable from noise", "D": "unreliable"}
GRADE_COL = {"A": "#15803D", "B": "#B45309", "C": "#64748B", "D": "#B91C1C"}
PRESETS = {"World": None, "Africa": ([-38, 40], [-20, 55]), "Asia": ([-12, 60], [25, 150]),
           "Europe": ([34, 72], [-25, 45]), "North America": ([5, 75], [-170, -50]),
           "South America": ([-57, 15], [-85, -30]), "Oceania": ([-48, 0], [110, 180]),
           "Western USA": ([30, 52], [-125, -100]), "Mediterranean": ([30, 46], [-10, 40])}
arrow = lambda s: "↑ rising" if s > 0 else "↓ falling"

# ---- Sidebar filters
st.sidebar.header("Filters")
pipeline.sidebar_status(st, set(avail), set(CAT))
theme = st.sidebar.radio("Theme", ["Water", "Wildfire conditions"])
opts = [k for k in avail if CAT[k]["group"] == theme]
if not opts: st.warning(f"No {theme} features loaded yet (see README)."); st.stop()
feat = st.sidebar.selectbox("Feature", opts, format_func=lambda k: CAT[k]["label"]);
C = CAT[feat]
grades = st.sidebar.multiselect("Evidence grade", list("ABCD"), ["A", "B"])
direction = st.sidebar.radio("Direction", ["Both", "Rising", "Falling"], horizontal=True)
region = st.sidebar.selectbox("Region", list(PRESETS));
box = PRESETS[region]
if st.sidebar.button("Reset map view"): st.session_state["map_rev"] = st.session_state.get("map_rev", 0) + 1
rev = st.session_state.get("map_rev", 0)
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
st.markdown(
    f"**{C['label']}.** {C['desc']}  \nGrade **A** robust, **B** fragile, **C** indistinguishable from noise, **D** unreliable. Colour = trend in {C['unit']} (symmetric about zero; brown/red end = drying or warming, blue/green = wetting).")

# ---- Map (click a point to inspect it)
st.header("Map")
if d.empty: st.warning("No units match these filters."); st.stop()
m = max(float(np.percentile(d.slope.abs(), pct)), 1e-9)
fig = px.scatter_geo(d, lat="lat", lon="lon", color="slope", symbol="grade", category_orders={"grade": list("ABCD")},
                     symbol_sequence=["circle", "diamond", "square", "x"], custom_data=["id"],
                     color_continuous_scale=C["cmap"], range_color=[-m, m],
                     hover_data={"id": True, "grade": True, "slope": ":.3g", "q": ":.3f", "robust": ":.0%",
                                 "lat": ":.1f", "lon": ":.1f"})
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
    **({"projection_type": "natural earth", "projection_rotation": {"lon": 0},
        "center": {"lon": 0, "lat": 10}} if box is None else {
        "projection_type": "equirectangular",
        "lataxis_range": box[0],
        "lonaxis_range": box[1]
    })
)

fig.update_layout(
    height=560,
    margin=dict(l=0, r=0, t=0, b=0),
    # grade legend: bottom-left, inside the map, horizontal, so it never touches the colour bar
    legend=dict(title_text="Evidence grade", orientation="h", x=0.01, y=0.02, xanchor="left", yanchor="bottom",
                bgcolor="rgba(255,255,255,0.85)", bordercolor="#D5E0EC", borderwidth=1),
    # colour bar: title on top, shorter and vertically centred, clear of the legend
    coloraxis_colorbar=dict(title=dict(text=C["unit"], side="top"), len=0.7, y=0.5, thickness=14),
    uirevision=f"{region}-{rev}"
)

fig = style_plotly(fig)

ev = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points", key=f"map-{region}-{rev}")
uid = None
try:
    uid = int(ev["selection"]["points"][0]["customdata"][0])
except Exception:
    pass
clicked = uid if (
            uid is not None and uid in set(d.id)) else None  # None = nothing selected: the details panel stays closed
uid = clicked
st.caption("Click a point to open its details and mirror cases below.")
_warm = C["cmap"].startswith("BrBG")
explain(
    f"Each dot is one 3-degree block of land (the same blocks are used for every feature). The colour is the trend: how fast {C['label'].lower()} is changing per year, in {C['unit']}. "
    + (
        "Brown means falling or drying, blue-green means rising or wetting" if _warm else "Red means rising or warming, blue means falling") + ", pale means almost no change, and the scale is centred on zero. "
                                                                                                                                               "The marker shape is the evidence grade, and hovering shows the grade and the exact numbers. By default only grade A and B trends are drawn, so noise is not plotted.",
    "This answers the challenge's questions in one view: what is changing, where, how much, and whether it is real. Look for neighbouring areas with opposite colours: those are candidate mirror cases, where the same variable moves up in one place and down in another.")
c1, c2 = st.columns(2);
c1.download_button("Download CSV", df.to_csv(index=False), f"{feat}_results.csv")
if feat == "grace_lwe" and os.path.exists(f"{O}/results.geojson"): c2.download_button("Download GeoJSON", open(
    f"{O}/results.geojson").read(), "counterpoint_results.geojson")
if uid is None:
    ids = d.sort_values("slope", key=abs, ascending=False).id.tolist();
    uid = st.selectbox("...or pick a location (largest trends first)", ids)
r = df[df.id == uid].iloc[0]

# ---- Right-hand details panel: exists only while a point is selected
if clicked is not None:
    bench_ = json.load(open("data/benchmark_regions.json"))["regions"] if os.path.exists(
        "data/benchmark_regions.json") else []
    xr_ = xrows(r.lat, r.lon);
    X = {x["key"]: x for x in xr_ if x["clear"]}
    reg_ = find_region(R, clicked);
    places = [n for n, bx in PRESETS.items() if bx and bx[0][0] <= r.lat <= bx[0][1] and bx[1][0] <= r.lon <= bx[1][1]]
    places += [b_["name"] for b_ in bench_ if
               b_["lat"][0] <= r.lat <= b_["lat"][1] and b_["lon"][0] <= r.lon <= b_["lon"][1]]
    st.markdown("""<style>
    .st-key-detail_panel{position:fixed;top:4rem;right:1rem;width:390px;max-height:calc(100vh - 5.5rem);overflow-y:auto;background:#FFFFFF;border:1px solid #D5E0EC;border-radius:14px;
      box-shadow:0 10px 30px rgba(15,23,42,.20);padding:16px 18px;z-index:999;}
    .st-key-detail_panel p,.st-key-detail_panel li,.st-key-detail_panel td,.st-key-detail_panel th{color:#1E293B !important;font-size:13.5px;}
    [data-testid="stMain"] .block-container{padding-right:27rem !important;}
    </style>""", unsafe_allow_html=True)
    with st.container(key="detail_panel"):
        st.markdown(
            f"<div style='font-size:11px;letter-spacing:.08em;color:#64748B'>SELECTED DATA POINT</div><div style='font-size:20px;font-weight:800;color:#1E293B'>{C['label']}</div>"
            f"<span style='background:{GRADE_COL[r.grade]};color:#fff;padding:2px 10px;border-radius:999px;font-weight:700'>Grade {r.grade}</span> "
            f"<span style='color:#64748B'>{GRADE_NAME[r.grade]}</span>", unsafe_allow_html=True)
        st.caption("Click an empty part of the map (or double-click) to close.")
        st.markdown(f"**Location**  \nLatitude {r.lat:.2f}, longitude {r.lon:.2f} (unit {clicked})" + (
            f"  \nWithin: {', '.join(places)}" if places else ""))
        mu_ = float(series[str(clicked)].mean())  # results.csv has no "mean" column
        pct_ = f"; about {r.slope * 10 / abs(mu_) * 100:.1f}% of its average level per decade" if C["pct"] and abs(mu_) > 1e-9 else ""
        st.markdown(
            f"**Trend**  \n{'Rising' if r.slope > 0 else 'Falling'} {abs(r.slope):.3g} {C['unit']} (95% interval {r.lo:.3g} to {r.hi:.3g}){pct_}.")
        st.markdown(
            f"**Significance**  \n{'Significant' if r.q < cp.Q else 'Not significant'} after false-discovery-rate control (Mann-Kendall p = {r.p:.3g}, q = {r.q:.3f}). "
            f"The sign holds in {r.robust:.0%} of start/end windows; {int(r.n_years)} years of data" + (
                f"; gap-step p = {r.step_p:.3g}" if pd.notna(r.step_p) else "") + ".")
        st.markdown(f"**Why this grade**  \n{r.reason}")
        st.markdown("**Mirror pair**")
        if reg_ is None:
            st.markdown("Not part of an A/B region, so no mirror analysis was run for this point.")
        else:
            pp_ = P[(P.up == reg_.region) | (P.down == reg_.region)] if len(P) else P
            if pp_.empty:
                st.markdown(
                    f"Region {int(reg_.region)} ({int(reg_.n)} unit(s)) has no opposite-direction A/B region within 6,000 km: **no mirror pair**.")
            else:
                pp_ = pp_.assign(partner=np.where(pp_.up == reg_.region, pp_.down, pp_.up));
                Rr_ = R.set_index("region");
                o_ = Rr_.loc[pp_.iloc[0].partner]
                st.markdown(
                    f"**Yes.** Region {int(reg_.region)} has {len(pp_)} mirror partner(s). Best-supported: region {int(pp_.iloc[0].partner)} at {o_.lat:.1f}, {o_.lon:.1f}, "
                    f"{pp_.iloc[0].km:.0f} km away, {'rising' if o_.slope > 0 else 'falling'} {abs(o_.slope):.3g} (grade {o_.grade}) while this side is {'rising' if reg_.slope > 0 else 'falling'}.")
                also = mirror_also(feat, reg_, o_)
                st.markdown("Features that also split in opposite directions: " + (
                    ", ".join(also) if also else "none, so no other loaded feature explains the split."))
        st.markdown("**What may be behind it** (association, not cause)")
        for c_ in causes(feat, r, X): st.markdown("- " + c_)
        st.markdown("**Other features here**")
        st.markdown("| Feature | Direction | Grade |\n|---|---|---|\n" + "\n".join(
            f"| {x['label']} | {('↑ rising' if x['sign'] > 0 else '↓ falling') if x['clear'] else 'no clear trend'} | {x['grade']} |"
            for x in xr_))
        xs_, ys_ = cp.annual(series[str(clicked)])
        fp = go.Figure([go.Scatter(x=xs_, y=ys_, mode="markers+lines", showlegend=False),
                        go.Scatter(x=xs_, y=np.median(ys_ - r.slope * xs_) + r.slope * xs_, line=dict(dash="dash"),
                                   showlegend=False)])
        fp.update_layout(height=170, margin=dict(l=0, r=0, t=6, b=0), xaxis_title=None, yaxis_title=None);
        fp = style_plotly(fp)
        st.plotly_chart(fp, width="stretch", key="panel-chart")
        st.caption(
            "Annual averages with the trend line (dashed) for this point: a compact version of the main trend chart below the map.")

# ---- Inspector
st.header(f"Trend details: {C['label']} at {r.lat:.1f}, {r.lon:.1f}")
word = "rising" if r.slope > 0 else "falling"
st.markdown(
    f"**{C['label']} is {word} by {abs(r.slope):.3g} {C['unit']}** (95% interval {r.lo:.3g} to {r.hi:.3g}). **Grade {r.grade}:** {r.reason}")

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

b.table(pd.DataFrame({"value": [f"{r.slope:.4g}", f"{r.lo:.4g} to {r.hi:.4g}", f"{r.p:.4g}", f"{r.q:.4f}",
                                f"{r.robust:.0%}", f"{int(r.n_years)}",
                                f"{r.step_p:.3g}" if pd.notna(r.step_p) else "n/a"]},
                     index=["Trend slope", "95% interval", "Mann-Kendall p", "FDR q", "Windows agreeing", "Years used",
                            "Gap-step p"]))
explain(
    f"The grey line is the monthly value after removing the normal seasonal cycle. The dots are annual averages, which are what the statistics test. The dashed line is the Theil-Sen trend: the median slope between all pairs of years, so one odd year barely moves it."
    + (" The grey band marks the gap between the GRACE and GRACE-FO satellites (mid-2017 to mid-2018)." if feat in (
        "grace_lwe", "GW_ANOM") else ""),
    "It lets you judge the trend with your own eyes: a steady drift is convincing, while a sudden jump (for example across the satellite gap) points to an instrument artifact, which is what grade D flags. Annual averages are tested because month-to-month values are strongly linked, and testing them directly would overstate how certain the trend is.")
n = len(x);
H = np.full((n, n), np.nan)
for i in range(n):
    for j in range(i + cp.MINWIN - 1, n): H[i, j] = cp.sen(x[i:j + 1], y[i:j + 1])[0]

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
explain(
    "Each cell is the trend you would get using only the years from its row (start year) to its column (end year), for windows of at least 10 years, so only the upper-right triangle is filled. The colours use the same scale as the map.",
    "This is the robustness check. If the whole triangle has one colour, the trend does not depend on which years you pick (grade A). If colours flip between red and blue, the answer changes with the window, so it is fragile (grade B) and could be a natural cycle such as a multi-year drought. About two decades of data can mistake a cycle for a trend, and this chart shows when that risk is real.")

st.subheader("All features at this location")
st.caption(
    "The same place seen through every loaded feature. Features that move together (for example less rain and falling storage) support a story; features that disagree are worth a second look. 'No clear trend' means the grade was C or D.")
rows = []
for k in avail:
    q, km = nearest(k, r.lat, r.lon)
    if q is not None: rows.append({"feature": CAT[k]["label"], "trend": f"{q.slope:.3g} {CAT[k]['unit']}",
                                   "direction": arrow(q.slope) if q.grade in "AB" else "no clear trend",
                                   "grade": q.grade, "distance_km": round(km)})
st.dataframe(pd.DataFrame(rows), hide_index=True)

# ---- Mirror cases for this selection
st.header("Mirror cases for this trend")
region = None
if len(R):
    for _, g in R.iterrows():
        if str(uid) in str(g.members).split(";"): region = g; break
if region is None:
    st.info("This location is not part of an A/B region, so it has no mirror analysis. Pick an A or B point.")
else:
    pp = P[(P.up == region.region) | (P.down == region.region)] if len(P) else P
    st.write(
        f"This location belongs to region {int(region.region)} ({int(region.n)} mascon(s), {arrow(region.slope)}, grade {region.grade}).")
    if pp.empty:
        st.write("No opposite-sign A/B region within 6,000 km: no mirror case for this trend.")
    else:
        pp = pp.assign(partner=np.where(pp.up == region.region, pp.down, pp.up));
        Rr = R.set_index("region")
        pick = st.selectbox("Mirror partner (best-supported first)", pp.partner.tolist(), format_func=lambda
            i: f"region {int(i)} at {Rr.loc[i, 'lat']:.1f}, {Rr.loc[i, 'lon']:.1f} ({arrow(Rr.loc[i, 'slope'])})")
        o = Rr.loc[pick];
        km = float(pp[pp.partner == pick].km.iloc[0])
        st.write(
            f"**{CAT[feat]['label']} moves {arrow(region.slope)} here and {arrow(o.slope)} {km:.0f} km away** (partner grade {o.grade}, slope {o.slope:.3g}).")
        mp = px.scatter_geo(pd.DataFrame(
            {"lat": [region.lat, o.lat], "lon": [region.lon, o.lon], "side": ["selected", "mirror partner"]}),
                            lat="lat", lon="lon", color="side")

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
        explain(
            f"The two markers are the selected region and its best mirror partner: two areas where {C['label'].lower()} moves in opposite directions, each with a trend graded A or B and within 6,000 km of each other.",
            "This is the central idea of the challenge: the same process can push a variable up in one region and down in another. The table below checks whether other features split the same way, which points to a candidate explanation (association, never proof of cause).")
        rows = []
        for k in avail:
            if k == feat: continue
            q1, _ = nearest(k, region.lat, region.lon);
            q2, _ = nearest(k, o.lat, o.lon)
            if q1 is None or q2 is None: continue
            c1_, c2_ = q1.grade in "AB", q2.grade in "AB"
            verdict = (
                "ALSO MIRRORS: opposite directions" if c1_ and c2_ and q1.sign != q2.sign else "same direction on both sides" if c1_ and c2_ else "trend clear on one side only" if c1_ or c2_ else "no clear trend")
            rows.append({"feature": CAT[k]["label"], "here": arrow(q1.slope) if c1_ else "no clear trend",
                         "partner": arrow(q2.slope) if c2_ else "no clear trend", "reading": verdict})
        st.markdown(
            "**Which other features mirror too?** A feature that splits the same way is a candidate explanation (association only, never proof of cause).")
        st.dataframe(pd.DataFrame(rows), hide_index=True)

# ---- Benchmark + methods
if os.path.exists(f"{O}/benchmark.csv") and os.path.exists(f"{O}/sources.json"):
    sm = json.load(open(f"{O}/sources.json"));
    st.header("Benchmark scorecard (GRACE)")
    (st.success if sm.get("benchmark_frozen") else st.warning)(("Region list FROZEN" if sm.get(
        "benchmark_frozen") else "NOT frozen: exploratory") + f" | SHA-256 {sm.get('benchmark_sha256')}")
    st.dataframe(pd.read_csv(f"{O}/benchmark.csv"));
    st.caption("Misses and contradictions are shown on purpose.")
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