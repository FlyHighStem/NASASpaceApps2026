# streamlit run app.py   (after: python counterpoint.py demo|run ...)
import streamlit as st, pandas as pd, plotly.express as px
st.set_page_config(layout="wide"); st.title("Counterpoint: Earth System Trend Detective")
df = pd.read_csv("output/results.csv"); pairs = pd.read_csv("output/pairs.csv")
g = st.sidebar.multiselect("Evidence grade", list("ABCD"), ["A", "B"]); d = df[df.grade.isin(g)]
c1, c2 = st.columns([2, 1])
c1.plotly_chart(px.scatter_geo(d, lat="lat", lon="lon", color="slope", color_continuous_scale="RdBu", color_continuous_midpoint=0,
    hover_data=["id", "grade", "q", "robust"]), use_container_width=True)
c2.subheader("Mirror pairs"); c2.dataframe(pairs.head(20))
pick = st.selectbox("Inspect unit", d.id); r = df[df.id == pick].iloc[0]
st.write(f"**What/How much:** {r.slope:.3f}/yr (95% CI {r.lo:.3f} to {r.hi:.3f}) | **Is it real:** grade {r.grade}, FDR q={r.q:.3f}, robust to window choice {r.robust:.0%}")
st.download_button("Download CSV", df.to_csv(index=False), "results.csv")
st.caption("Association, not cause. GRACE = total water storage. Sources: list every dataset in your submission.")
