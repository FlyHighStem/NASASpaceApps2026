# streamlit run app.py   (after: python counterpoint.py run --grace FILE.nc ...)
import json, os, numpy as np, pandas as pd, streamlit as st, plotly.express as px, plotly.graph_objects as go
import counterpoint as cp
st.set_page_config(layout="wide", page_title="Counterpoint"); O = "output"
if not os.path.exists(f"{O}/results.csv"): st.error("No results yet. Run: python counterpoint.py run --grace data/FILE.nc"); st.stop()
meta = json.load(open(f"{O}/sources.json")); df = pd.read_csv(f"{O}/results.csv"); series = pd.read_csv(f"{O}/series.csv", index_col=0, parse_dates=True)
def rd(n):
    try: return pd.read_csv(f"{O}/{n}.csv")
    except Exception: return pd.DataFrame()
R, P, B = rd("regions"), rd("pairs"), rd("benchmark")

# 1. Header
st.title("Counterpoint: Earth System Trend Detective")
st.info(f"REAL DATA: {meta['source']} | period {meta['period'][0]} to {meta['period'][1]} | fetched {meta['fetched']}")
st.markdown("**Question:** where is this variable changing, how much, is it real, and does the same variable move in *opposite* directions elsewhere?  \n"
            "**What** = liquid water equivalent thickness (cm): the depth of water that would hold the same stored mass (snow, soil, groundwater, surface water). "
            "**Where** = map. **How much** = Theil-Sen slope with 95% interval. **Is it real** = Evidence Grade A (robust), B (fragile), C (noise), D (unreliable).")

# 2. Map
g = st.sidebar.multiselect("Evidence grade", list("ABCD"), ["A", "B"]); d = df[df.grade.isin(g)]
st.header("Map"); st.caption("Colour = trend (cm/yr), symbol = grade. Real GRACE/GRACE-FO data.")
fig = px.scatter_geo(d, lat="lat", lon="lon", color="slope", symbol="grade", color_continuous_scale="RdBu", color_continuous_midpoint=0,
                     hover_data={"id": True, "grade": True, "q": ":.3f", "robust": ":.0%", "lat": False, "lon": False}, projection="natural earth")
fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0)); st.plotly_chart(fig, use_container_width=True)
c1, c2 = st.columns(2); c1.download_button("Download CSV", df.to_csv(index=False), "counterpoint_results.csv")
if os.path.exists(f"{O}/results.geojson"): c2.download_button("Download GeoJSON", open(f"{O}/results.geojson").read(), "counterpoint_results.geojson")

# 3. Inspector
st.header("Inspector")
pool = d if len(d) else df; pool = pool.reindex(pool.slope.abs().sort_values(ascending=False).index)
pick = st.selectbox("Mascon (sorted by trend size)", pool.id.tolist()); r = df[df.id == pick].iloc[0]
a, b2 = st.columns([2, 1]); x, y = cp.annual(series[str(pick)])
f2 = go.Figure(go.Scatter(x=x, y=y, mode="markers+lines", name="annual mean (deseasonalised)"))
ic = np.median(y-r.slope*x); f2.add_trace(go.Scatter(x=x, y=ic+r.slope*x, name="Theil-Sen trend"))
if x.min() < meta["gap"][0] and x.max() > meta["gap"][1]: f2.add_vrect(x0=meta["gap"][0], x1=meta["gap"][1], fillcolor="grey", opacity=0.3, annotation_text="mission gap")
f2.update_layout(height=340, xaxis_title="year", yaxis_title="cm"); a.plotly_chart(f2, use_container_width=True)
b2.metric("Slope (cm/yr)", f"{r.slope:.3f}", f"95% CI {r.lo:.3f} to {r.hi:.3f}", delta_color="off")
b2.write(f"**Grade {r.grade}.** {r.reason}"); b2.write(f"Mann-Kendall p = {r.p:.4f}; FDR q = {r.q:.3f}")
n = len(x); H = np.full((n, n), np.nan)
for i in range(n):
    for j in range(i+cp.MINWIN-1, n): H[i, j] = cp.sen(x[i:j+1], y[i:j+1])[0]
st.plotly_chart(px.imshow(H, x=x, y=x, color_continuous_scale="RdBu", color_continuous_midpoint=0, labels=dict(x="end year", y="start year", color="cm/yr"),
                          title="Window robustness: slope for every start/end year (>=10 yrs)").update_layout(height=380), use_container_width=True)

# 4. Mirror finder
st.header("Mirror finder")
if len(P):
    st.dataframe(P); 
    if "verdict" in P: 
        for _, p in P.iterrows(): st.write(f"Region {int(p.up)} (rising) vs region {int(p.down)} (falling), {p.km:.0f} km apart: **{p.up_driver} / {p.down_driver}**. {p.verdict}")
    else: st.caption("Run with --driver-var PRECTOTCORR to add the precipitation driver check.")
else: st.write("No opposite-sign A/B region pairs within 6,000 km in this run.")

# 5. Benchmark scorecard
st.header("Benchmark scorecard")
if meta.get("benchmark_sha256"):
    (st.success if meta["benchmark_frozen"] else st.warning)(("Region list FROZEN" if meta["benchmark_frozen"] else "WARNING: region list NOT frozen; results are exploratory") + f" | SHA-256 {meta['benchmark_sha256']}")
    st.dataframe(B); st.caption("Misses and contradictions are shown on purpose. Each box is re-tested as one series (p<0.05).")
else: st.write("No benchmark file used.")

# 6. Methods and limits
st.header("Methods and limits")
st.markdown("""Unit = one ~3-degree mascon (or approximate block; see source line). Annual means of the deseasonalised series; tie-corrected Mann-Kendall; Theil-Sen slope with Sen/Gilbert 95% interval;
Benjamini-Hochberg FDR (q=0.10); robustness = share of start/end windows (>=10 yrs) with the same sign; trend-plus-step test at the GRACE to GRACE-FO gap (step -> grade D).
Mirror pairs: adjacent same-sign A/B mascons merge into regions, re-tested as one series; opposite-sign regions within 6,000 km pair up. Driver labels: follows / opposes / unreliable (association, never cause).
**Limits:** GRACE measures total water storage, not groundwater alone; mascons are ~3 degrees wide; two decades can mistake natural cycles for trends.""")
if meta.get("monthly_check"): st.write("Monthly Hamed-Rao cross-check:", meta["monthly_check"])
if os.path.exists(f"{O}/validation.json"): st.caption("Method calibration on SYNTHETIC data (not GRACE):"); st.json(json.load(open(f"{O}/validation.json")))
