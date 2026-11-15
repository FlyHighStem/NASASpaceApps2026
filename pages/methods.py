import json
from pathlib import Path

import streamlit as st


# ---------------------------------------------------------------------
# Page setup and shared styling
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="Methodology & Evidence | Counterpoint",
    page_icon="📐",
    layout="wide",
)

PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_css():
    """Load the project's shared stylesheet when available."""
    css_path = PROJECT_DIR / "style.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )


load_css()

if st.button("← Back to Main Dashboard", key="back_home"):
    st.switch_page("home.py")


# ---------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------

st.title("📐 Methodology & Evidence")
st.caption(
    "How Counterpoint measures environmental change, evaluates robustness, "
    "and classifies the strength of evidence."
)
st.divider()

st.markdown(
    """
    **Counterpoint: Earth System Trend Detective** does more than identify
    increasing and decreasing environmental trends. It evaluates whether
    those trends are statistically significant, consistent over time, and
    potentially affected by measurement limitations.

    This page explains the analytical framework behind the dashboard,
    including the robustness calculation, evidence grades, statistical
    methods, and limitations.
    """
)

# ---------------------------------------------------------------------
# 1. Analytical framework
# ---------------------------------------------------------------------

st.header("1. Analytical Framework")

st.markdown(
    """
    Environmental datasets contain natural variability, seasonal cycles,
    measurement uncertainty, and occasional discontinuities. A trend
    observed over a limited period may therefore not represent a persistent
    change.

    Counterpoint uses several complementary statistical methods to
    distinguish potential long-term patterns from these sources of
    uncertainty.
    """
)

with st.expander("Overview of the analysis process", expanded=True):
    st.markdown(
        """
        The analysis follows these general steps:

        1. **Data preparation:** Retrieve and organize environmental
           observations into consistent geographic units and time series.

        2. **Seasonal adjustment:** Remove the average monthly seasonal
           cycle from monthly observations.

        3. **Annual aggregation:** Calculate annual averages and use
           them for the statistical trend tests. A year counts only if it
           has at least 9 months of data (peak-season fire series use their
           3 peak months), so the years inside the GRACE to GRACE-FO gap
           normally drop out.

        4. **Trend estimation:** Estimate the direction and magnitude
           of change using the Theil-Sen estimator.

        5. **Statistical significance:** Apply the Mann-Kendall test
           and correct for multiple comparisons.

        6. **Robustness testing:** Recalculate trends across different
           start-year and end-year combinations.

        7. **Evidence classification:** Assign grades based on statistical
           significance, consistency, and relevant reliability checks.
        """
    )

# ---------------------------------------------------------------------
# 2. Robustness
# ---------------------------------------------------------------------

st.divider()
st.header("2. Robustness Analysis")

st.markdown(
    """
    **A trend is not automatically a reliable trend.**

    Two regions may show similar overall slopes even though their
    underlying behavior is very different. One may experience a steady
    change throughout the observation period, while another may show
    a temporary change driven by an unusual climate event.

    Robustness analysis evaluates whether a trend remains consistent
    when different portions of the observation period are examined.
    """
)

st.subheader("How robustness is calculated")

st.markdown(
    """
    Counterpoint calculates trends across multiple combinations of
    start years and end years rather than relying exclusively on the
    complete observation period.

    Only windows containing at least **10 annual means** are considered (the full record is one of them).
    For every eligible window, the Theil-Sen estimator calculates
    a trend slope. Its direction is then compared with the direction
    of the overall trend.
    """
)

st.latex(
    r"\text{Robustness} = "
    r"\frac{\text{Windows agreeing with the overall trend direction}}"
    r"{\text{Total eligible windows}}"
)

st.markdown(
    """
    A robustness value of 1.0 means all eligible windows agree with
    the overall trend direction. A value of 0.5 means half agree.
    """
)

st.subheader("Interpreting the robustness heatmap")

st.markdown(
    """
    The dashboard's robustness heatmap displays the estimated trend
    for every eligible start-year and end-year combination.
    """
)

with st.expander("How to read the heatmap", expanded=True):
    st.markdown(
        """
        - **Consistent colours:** Different time windows produce trends
          in the same direction, supporting a more robust interpretation.

        - **Mixed colours:** Some windows produce opposite-direction
          trends, suggesting that the overall result depends on the
          observation period.

        - **Blank cells:** The selected window does not meet the
          minimum 10-year requirement.

        The heatmap is therefore a sensitivity analysis: it shows
        whether the conclusion changes when the observation period changes.
        """
    )

st.info(
    "Robustness measures directional consistency across time windows. "
    "It does not independently establish statistical significance "
    "or prove that a trend will continue into the future."
)

# ---------------------------------------------------------------------
# 3. Evidence grades
# ---------------------------------------------------------------------

st.divider()
st.header("3. Evidence Classification")

st.markdown(
    """
    Each geographic unit receives an evidence grade that summarizes
    the reliability of its estimated trend.

    The classification considers statistical significance, trend
    consistency, and potential measurement discontinuities.
    """
)

st.subheader("The four evidence grades")

grade_data = [
    (
        "A — Robust",
        "The trend is supported by strong statistical evidence and "
        "consistent directional behavior across different observation "
        "windows."
    ),
    (
        "B — Fragile",
        "The trend has evidence of a directional change, but its "
        "consistency across different observation windows is weaker."
    ),
    (
        "C — Indistinguishable from noise",
        "The available statistical evidence does not sufficiently "
        "distinguish the estimated trend from natural variability."
    ),
    (
        "D — Unreliable (possible gap artifact)",
        "GRACE-based series only. A step at the GRACE to GRACE-FO gap "
        "is statistically significant, so the trend may be an instrument "
        "offset. It could also be a real change that happens to straddle "
        "the gap: this is a caution flag, not proof of an artifact."
    ),
]

for grade, description in grade_data:
    with st.expander(grade):
        st.write(description)

st.subheader("What determines a grade?")

st.markdown(
    """
    The rules are applied in this order, and the first one that matches wins:

    1. **D:** the gap-step test gives p < 0.01 **and** the plain trend test
       gives p < 0.05. Only GRACE-based series can receive D; other
       features have no gap, so they are graded A, B or C.
    2. **C:** the false-discovery-rate q-value is 0.10 or more.
    3. **A:** q < 0.10 and the trend keeps its sign in at least 80% of
       start/end windows.
    4. **B:** q < 0.10 but fewer than 80% of windows agree.

    Because D is checked first, a unit can be graded D even when it would
    otherwise be A or B. That is intentional: the grade says "look at the
    gap before trusting this", not "this trend is false".
    """
)

st.info(
    "A Grade C result does not mean that nothing is changing. It means "
    "the available evidence cannot reliably distinguish the estimated "
    "trend from noise. Grade D represents a separate measurement-reliability "
    "concern."
)

# ---------------------------------------------------------------------
# 4. Statistical methods
# ---------------------------------------------------------------------

st.divider()
st.header("4. Statistical Methods")

st.markdown(
    """
    Counterpoint combines non-parametric statistical methods and
    multiple-comparison correction to evaluate environmental trends.
    """
)

with st.expander("Mann-Kendall Test", expanded=True):
    st.markdown(
        """
        The Mann-Kendall test evaluates whether a time series exhibits
        a statistically significant increasing or decreasing tendency.

        It is a non-parametric test, meaning it does not require the
        observations to follow a normal distribution.

        Counterpoint applies the test to annual averages rather than
        directly to monthly observations, which removes most of the
        month-to-month dependence. Year-to-year dependence is not
        corrected, so p-values can be somewhat optimistic for slowly
        varying series. The test is tie-corrected.

        **Output:** A p-value representing the statistical evidence
        against the absence of a monotonic trend.
        """
    )

with st.expander("Theil-Sen Estimator"):
    st.markdown(
        """
        The Theil-Sen estimator calculates the median slope between
        all pairs of observations.

        Because it uses the median rather than fitting a line by
        minimizing squared errors, it is less sensitive to individual
        unusually high or low observations.

        **Output:** An estimated trend slope and its 95% confidence
        interval.
        """
    )

with st.expander("Benjamini-Hochberg Correction"):
    st.markdown(
        """
        Counterpoint analyzes many geographic units simultaneously.
        Conducting many statistical tests increases the probability
        of identifying apparently significant results by coincidence.

        The Benjamini-Hochberg procedure adjusts for multiple comparisons
        by controlling the expected proportion of false discoveries
        among results declared significant. It is applied across the
        units of each feature, and again across merged regions.
        Neighbouring units are spatially correlated, so q-values are
        approximate.

        Counterpoint uses a false-discovery-rate threshold of:

        **q = 0.10**
        """
    )

with st.expander("GRACE Mission-Gap Test"):
    st.markdown(
        """
        The GRACE and GRACE-FO satellites are separated by a gap of
        roughly a year (mid-2017 to mid-2018), and the two instruments
        can differ slightly in offset.

        For GRACE-based series, Counterpoint fits the annual means with
        a straight trend plus a step for the years after the gap and
        tests the step. A significant step (p < 0.01) together with a
        significant raw trend (p < 0.05) gives Grade D.

        **What this can and cannot tell you:** the test finds a jump
        that coincides with the gap. It cannot tell an instrument offset
        from a real change that is accelerating or happens to straddle
        the gap. Treat D as "check this one", and compare with a smooth
        curve (see `tools/diagnose_box.py`) before calling it an artifact.
        """
    )

with st.expander("Seasonal Adjustment and Annual Aggregation"):
    st.markdown(
        """
        Environmental variables frequently exhibit recurring seasonal
        cycles. For example, precipitation and water storage can vary
        considerably between wet and dry seasons.

        Counterpoint removes the average monthly seasonal cycle
        before calculating annual averages.

        These annual averages are then used in the statistical trend
        analysis, reducing the influence of recurring seasonal
        fluctuations.
        """
    )

# ---------------------------------------------------------------------
# 5. Mirror cases and driver check
# ---------------------------------------------------------------------

st.divider()
st.header("5. Mirror Cases and Driver Check")

st.markdown(
    """
    Grade A and B units with the same trend direction that lie within
    500 km of each other are merged into regions. Each region's average
    series is tested and graded again as one series. A **mirror pair** is
    a rising A/B region and a falling A/B region within 6,000 km of each
    other. Pairs are ranked by the smaller of the two ratios
    |slope| / standard error, so a pair is only as strong as its weaker side.

    For the top pairs, the driver check compares each region with the
    annual NASA POWER (MERRA-2) precipitation trend at the region's
    centre point. A side is labelled *follows* or *opposes* the
    precipitation trend, or *unreliable* when the precipitation trend is
    not significant (p of 0.10 or more). One point can misrepresent a
    large region, and this is association only, never proof of cause.
    """
)

# ---------------------------------------------------------------------
# 6. Benchmark
# ---------------------------------------------------------------------

st.divider()
st.header("6. Benchmark")

st.markdown(
    """
    The benchmark scores the GRACE analysis against a fixed list of
    regions with an expected direction (`data/benchmark_regions.json`).
    A region counts as **recovered** only if the observed sign matches
    AND the grade is A or B, with false-discovery control across the
    benchmark regions. A region expected to show no trend is recovered
    only if it is graded C. Misses and contradictions are shown. The
    file's SHA-256 is stored with each run, and the dashboard says whether
    the list was frozen before the run; if it was not, treat the scorecard
    as exploratory.
    """
)

# ---------------------------------------------------------------------
# 7. Limitations
# ---------------------------------------------------------------------

st.divider()
st.header("7. Limitations & Interpretation")

st.markdown(
    """
    Environmental datasets provide valuable information about
    large-scale changes, but every dataset has limitations.
    Understanding these limitations is essential when interpreting
    the results.
    """
)

_src = ""
try:
    _src = json.loads((PROJECT_DIR / "output" / "sources.json").read_text(encoding="utf-8")).get("source", "")
except (OSError, ValueError):
    pass

with st.expander("Spatial Resolution"):
    st.markdown(
        """
        The JPL GRACE/GRACE-FO product is built from 4,551 equal-area
        3-degree mascons, published on a 0.5-degree grid, so neighbouring
        grid cells are not independent and localized changes are not
        visible. Signal near coastlines can still leak between land and ocean.
        """
    )
    if _src:
        st.caption(f"Grouping used in this run: {_src}")

with st.expander("Groundwater Interpretation"):
    st.markdown(
        """
        GRACE measures total water storage rather than groundwater alone.
        Changes can also reflect soil moisture, surface water, snow,
        and ice.
        """
    )

with st.expander("Reanalysis Data"):
    st.markdown(
        """
        MERRA-2 variables are reanalysis products that combine
        observations with numerical models. They are not direct
        measurements at every geographic location.
        """
    )

with st.expander("Natural Climate Variability"):
    st.markdown(
        """
        Approximately two decades of observations may not fully
        distinguish long-term trends from natural climate cycles,
        including multi-year droughts and El Niño and La Niña events.
        """
    )

with st.expander("Association vs. Causation"):
    st.markdown(
        """
        Two environmental variables moving together does not establish
        that one causes the other.

        Proposed explanations in Counterpoint are hypotheses based
        on observed associations, not proof of causal relationships.
        """
    )

with st.expander("Fire Observations"):
    st.markdown(
        """
        MODIS fire detections represent satellite-observed active fires
        and thermal anomalies. They are affected by cloud cover and
        other observation limitations and should not be interpreted
        as direct measurements of total burned area.
        """
    )

st.info(
    "Counterpoint is an exploratory trend-analysis tool, not an official "
    "NASA product or a substitute for peer-reviewed scientific analysis."
)

# ---------------------------------------------------------------------
# Bottom navigation
# ---------------------------------------------------------------------

st.divider()

nav1, nav2 = st.columns(2)

with nav1:
    if st.button(
        "← Back to Main Dashboard",
        key="back_home",
        width="stretch"
    ):
        st.switch_page("home.py")

with nav2:
    if st.button(
        "🌎 Meet the Team & View Credits",
        key="credits_button",
        width="stretch"
    ):
        st.switch_page("pages/credits.py")

st.caption(
    "Counterpoint: Earth System Trend Detective | "
    "NASA Space Apps Challenge 2026"
)
