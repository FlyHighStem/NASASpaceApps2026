from pathlib import Path

import streamlit as st


# ---------------------------------------------------------------------
# Page setup and shared styling
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="User Guide | Counterpoint",
    page_icon="📖",
    layout="wide",
)

PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_css():
    """Load the project's shared stylesheet when it is available."""
    css_path = PROJECT_DIR / "style.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def note(title, body):
    """A small callout box, styled like the explanation boxes on the Cross-check page."""
    st.markdown(
        "<div style='background:rgba(255,255,255,.85);border-left:4px solid #2563A6;border-radius:8px;"
        "padding:10px 14px;margin:6px 0 16px 0;font-size:14px;line-height:1.5;color:#1E293B'>"
        f"<b>{title}</b> {body}</div>",
        unsafe_allow_html=True,
    )


load_css()

if st.button("← Back to Main Dashboard", key="back_home"):
    st.switch_page("home.py")


# ---------------------------------------------------------------------
# Introduction
# ---------------------------------------------------------------------
st.title("📖 User Guide")
st.caption("How to read and use Counterpoint: Earth System Trend Detective.")
st.divider()

st.markdown(
    """
    Counterpoint looks at how water storage, rainfall, temperature and wildfire
    activity have changed since 2002, using real NASA satellite data. It answers
    four questions for every location: **what** is changing, **where**, **by how
    much**, and **is it real?** Then it adds a fifth: **how far can you trust the answer?**

    This guide explains each page, the terms you will see, and how to read the results.
    """
)

st.subheader("The 60-second version")
st.markdown(
    """
    1. Open the **Home** page and wait for the first-time setup to finish.
    2. Look at the map. Colour shows the direction and size of a trend.
       The evidence grade (A to D) shows how much to trust it.
    3. Click a location to see its time series and the reason for its grade.
    4. Check the **mirror pairs** to find regions moving in opposite directions.
    5. Read the **scorecard** and the **Methods** page to see what the tool got right and what it missed.
    """
)

# ---------------------------------------------------------------------
# First launch
# ---------------------------------------------------------------------
st.header("First launch and setup")

st.markdown(
    """
    The first time you open the app, it downloads real NASA data and runs the
    analysis for you. A progress page shows each step and updates by itself.
    """
)

with st.expander("What the setup does", expanded=True):
    st.markdown(
        """
        | Step | What happens | Required? |
        | --- | --- | --- |
        | Download GRACE/GRACE-FO | Fetches the water-storage data from NASA Earthdata | Yes |
        | Grade every trend | Tests each location and assigns an evidence grade, finds mirror pairs and scores the benchmark | Yes |
        | Make GRACE visible | Registers the results so the dashboard can show them | Yes |
        | Water and fire-weather variables | Adds rainfall, soil wetness, evaporation, temperature, humidity and wind (NASA POWER / MERRA-2) | Optional |
        | Wildfire detections | Adds fire counts, intensity and peak season (NASA FIRMS) | Optional, needs a free key |
        | Groundwater-style anomaly | Subtracts modelled soil moisture and snow from GRACE (large download) | Optional, switched on in the sidebar |
        """
    )
    st.markdown(
        "The dashboard opens as soon as the required GRACE steps finish. Optional layers appear "
        "on their own when they are ready. Finished steps are skipped on later launches."
    )

with st.expander("Logging in to NASA Earthdata"):
    st.markdown(
        """
        GRACE data needs a free **Earthdata login** from
        [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov). If the app cannot find
        your login it shows a form on the setup page.

        - Tick **Save to .env** only on a computer you control. The password is stored as plain text.
        - You can also provide the login through the `EARTHDATA_USERNAME` and
          `EARTHDATA_PASSWORD` environment variables or a `~/.netrc` file.
        """
    )

with st.expander("Adding wildfire layers"):
    st.markdown(
        """
        1. Get a free MAP_KEY from the [FIRMS area API page](https://firms.modaps.eosdis.nasa.gov/api/area).
        2. Open **Background setup** in the sidebar and paste the key.
        3. Enter the fire area as four numbers in the order **West South East North**
           (the default is a box over California and Nevada).
        4. Select **Apply and run**. The fire layers appear when they finish.
        """
    )

with st.expander("If a step fails"):
    st.markdown(
        """
        Open the **Log** section on the setup page to see what went wrong, then select **Retry**.
        The same log is saved at `output/pipeline.log`. A required step that fails stops the
        setup. An optional step that fails is marked unavailable and the rest carries on.
        """
    )

# ---------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------
st.header("The pages")

st.markdown(
    """
    | Page | Use it to |
    | --- | --- |
    | **Home** | Explore the map, inspect a location, find mirror pairs and see the benchmark scorecard |
    | **Data** | Browse and download the processed results, regional summaries, mirror pairs and time series |
    | **Cross-check** | Test our trends against an independent time series exported from NASA or KNMI tools |
    | **Methods** | Read how the trends, grades and pairs are calculated |
    | **Credits** | See the team, data sources and software used |
    """
)

# ---------------------------------------------------------------------
# Evidence grades
# ---------------------------------------------------------------------
st.header("Reading the evidence grades")

st.markdown(
    "Every trend carries a grade, so no number appears without its evidence."
)

grades = [
    ("A", "Robust", "The trend holds up across different time windows and is clearly distinguishable from noise."),
    ("B", "Fragile", "There is a trend, but it changes noticeably depending on the time window you choose."),
    ("C", "Indistinguishable from noise", "Any trend could be natural variation. Do not read a direction into it."),
    ("D", "Possible gap artifact", "The trend looks significant, but it may come from the gap between the GRACE and GRACE-FO missions (2017 to 2018)."),
]
cols = st.columns(4)
for col, (letter, name, desc) in zip(cols, grades):
    with col:
        st.markdown(f"### {letter}")
        st.markdown(f"**{name}**")
        st.caption(desc)

note(
    "Tip:",
    "A grade C or D result is not a failure. It is the tool telling you honestly that the data cannot "
    "support a firm conclusion for that place.",
)

# ---------------------------------------------------------------------
# Home page walk-through
# ---------------------------------------------------------------------
st.header("Using the Home page")

with st.expander("1. The map", expanded=True):
    st.markdown(
        """
        Each map unit is coloured by the **sign and size** of its trend, and the **evidence grade**
        controls how strongly it is drawn. Use the grade filter to hide weak evidence, and the
        download buttons to save the results as CSV or GeoJSON.

        Choose a different feature (for example precipitation or temperature) to see the same
        analysis on another variable. Only features that have finished processing appear.
        """
    )

with st.expander("2. The inspector"):
    st.markdown(
        """
        Click a location to open its inspector. It shows:

        - The **time series** with a seasonal-cycle-removed trend line
        - The **Theil-Sen slope** with its **95% interval**: the best estimate of change per year, and the range it could plausibly fall in
        - The **Mann-Kendall result**: a test of whether the series really trends up or down
        - The **window-robustness heatmap**: whether the answer survives when the start and end years change
        - The **gap marker**: where the GRACE and GRACE-FO missions are joined
        - The **grade** and a plain-English reason for it
        """
    )

with st.expander("3. Mirror pairs"):
    st.markdown(
        """
        A **mirror pair** is two regions where the same variable moves in opposite directions,
        for example one region drying while another gets wetter. The pairs are ranked, and where
        precipitation data is available each pair gets a driver check:

        - **Follows**: the water trend matches the rainfall trend
        - **Opposes**: the water trend goes against the rainfall trend
        - **Unreliable**: the rainfall data cannot support a conclusion

        These labels describe **association, not cause**.
        """
    )

with st.expander("4. The benchmark scorecard"):
    st.markdown(
        """
        The scorecard checks the tool against regions whose water changes are already described
        in NASA's published story. Each region has an expected direction. A region counts as
        **recovered** only if the tool finds the expected sign **and** grades it A or B.

        Misses are shown as prominently as hits. A **frozen** badge with a SHA-256 code means the
        list of regions was locked before the analysis ran, so it could not be tuned to flatter
        the results. If the list was not frozen, treat the scorecard as exploratory.
        """
    )

# ---------------------------------------------------------------------
# Cross-check
# ---------------------------------------------------------------------
st.header("Running a cross-check")

st.markdown(
    """
    The **Cross-check** page lets you test our trends against an independent source.

    1. Export a **monthly** time series for one point from
       [Giovanni](https://giovanni.gsfc.nasa.gov/),
       [Hydrology Time Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series)
       or [KNMI Climate Explorer](https://climexp.knmi.nl/).
    2. Upload the file and select the matching feature.
    3. Enter the latitude and longitude of your point.
    4. If your units differ from ours, enter a conversion in **Multiply your values by**.
       For precipitation, kg m-2 s-1 times 86400 gives mm/day.
    5. Select **Compare**.

    The result shows whether both series trend in the **same direction**, whether their
    **95% intervals overlap**, and how closely the **year-to-year values** match. Every comparison,
    including disagreements, is saved to `output/crosscheck.csv`.
    """
)

# ---------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------
st.header("Glossary")

glossary = {
    "GRACE / GRACE-FO": "Twin-satellite missions that measure tiny changes in Earth's gravity, which reveal changes in how much water is stored on land.",
    "Liquid water equivalent (LWE) thickness": "The depth of water, in centimetres, that would cover an area if all stored water, including ice, snow and soil moisture, were spread evenly.",
    "Mascon": "A patch of Earth's surface, roughly 3 degrees wide, treated as one unit by GRACE. Smaller features cannot be resolved.",
    "Theil-Sen slope": "A robust estimate of the average rate of change per year that is not thrown off by a few unusual values.",
    "Mann-Kendall test": "A test of whether a series shows a consistent upward or downward direction rather than random wandering.",
    "95% interval": "The range in which the true trend very likely falls. If it includes zero, the trend is not clearly up or down.",
    "p-value": "The chance of seeing a trend this strong if there were really no trend. Smaller values mean stronger evidence.",
    "Deseasonalised": "With the regular yearly cycle removed, so the long-term change is easier to see.",
    "Mirror pair": "Two regions where the same variable moves in opposite directions.",
    "Benchmark": "A fixed set of regions with known expected behaviour, used to check that the tool finds what it should.",
}
for term, meaning in glossary.items():
    st.markdown(f"- **{term}**: {meaning}")

# ---------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------
st.header("What to keep in mind")

st.markdown(
    """
    - **GRACE measures total water storage**, not groundwater alone.
    - **Each unit is about 3 degrees wide.** Small regions cannot be resolved.
    - **About two decades of data** can mistake natural cycles for lasting trends.
    - **The precipitation driver is a single point** at each region's centre, so it can misrepresent a large region.
    - **Reanalysis variables** (MERRA-2) are model output constrained by observations, not direct measurements.
    - **Fire counts are detections**, not burned area, and clouds can hide fires.
    - **Everything shown is association, not cause.**
    """
)

st.markdown(
    "For the full method, see the **Methods** page. For data providers and software, see **Credits**."
)

# ---------------------------------------------------------------------
# Troubleshooting
# ---------------------------------------------------------------------
st.header("Troubleshooting")

with st.expander("The dashboard shows a setup page instead of the map"):
    st.markdown(
        "The required GRACE steps have not finished yet. Leave the page open, it updates by itself. "
        "If a step shows a red cross, open the log and select **Retry**."
    )

with st.expander("A feature I expect is missing"):
    st.markdown(
        "Optional layers only appear after they finish. Check **Background setup** in the sidebar. "
        "Fire layers need a FIRMS MAP_KEY, and the groundwater layer must be switched on there."
    )

with st.expander("The Data page says no outputs were found"):
    st.markdown(
        "Let the setup on the Home page finish first, then refresh the Data page."
    )

with st.expander("The Cross-check page says my point is too far away"):
    st.markdown(
        "Our nearest unit is more than 700 km from the latitude and longitude you entered. "
        "Pick a point closer to a location we have analysed."
    )

with st.expander("The Cross-check page cannot read my file"):
    st.markdown(
        "The file needs at least two years of monthly values, with dates in a recognisable form. "
        "Giovanni CSV, Hydrology Time Series text and KNMI text exports are supported, and the file "
        "must overlap ours by at least 10 years."
    )

st.divider()
st.caption(
    "Counterpoint: Earth System Trend Detective | NASA Space Apps Challenge 2026"
)