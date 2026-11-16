from pathlib import Path

import streamlit as st


# ---------------------------------------------------------------------
# Page setup and shared styling
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Credits | Counterpoint",
    page_icon="🌎",
    layout="wide",
)

PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_css():
    """Load the project's shared stylesheet when it is available."""
    css_path = PROJECT_DIR / "style.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css()

if st.button("← Back to Main Dashboard", key="back_home"):
    st.switch_page("home.py")


# ---------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------
st.title("🌎 Credits & Acknowledgments")
st.caption("The people, data, and tools behind Counterpoint.")
st.divider()

st.markdown(
    """
    **Counterpoint: Earth System Trend Detective** is an independent student
    project developed for the **NASA Space Apps Challenge 2026**.

    The project explores long-term patterns in Earth-system data and presents
    them through an interactive dashboard. Its results depend on the work of
    the scientific teams and organizations that make these datasets available.
    """
)

st.header("Our Team")

team = [
    ("Aanya Tiwari", "Project Lead/Backend/Pipeline"),
    ("Dat Hoang Vien", "Frontend/DevOps"),
    ("Swapnil Tiwari", "Strategist"),
    ("Tuhina Tiwari", "Coordinator"),
]

for name, role in team:
    st.markdown(f"- **{name}** — {role}")

st.divider()
st.header("Data Sources")

st.markdown(
    """
    Counterpoint uses or is designed to work with Earth-observation and
    Earth-system datasets from the following providers. The exact datasets
    used in a particular analysis are recorded in the project's output
    metadata where available.
    """
)

with st.expander("GRACE and GRACE-FO — Gravity Recovery and Climate Experiment", expanded=True):
    st.markdown(
        """
        **Provider:** NASA and the German Research Centre for Geosciences (GFZ),
        with data products distributed through NASA's Physical Oceanography
        Distributed Active Archive Center (PO.DAAC).

        **Product used:** JPL GRACE and GRACE-FO Mascon RL06.3 (CRI-filtered, version 4).

        **How it is used:** GRACE/GRACE-FO gravity observations are used to
        estimate changes in terrestrial water storage. These measurements
        represent changes in total water storage, not groundwater alone.

        **Data access:** [NASA PO.DAAC — GRACE and GRACE-FO](https://podaac.jpl.nasa.gov/GRACE)
        """
    )

with st.expander("Giovanni and GES DISC Hydrology Time Series — independent time-series tools"):
    st.markdown(
        """
        **Provider:** NASA Goddard Earth Sciences Data and Information Services
        Center (GES DISC).

        **How it is used:** Monthly time series for chosen points are exported
        from these tools (and from KNMI Climate Explorer) and uploaded on the
        Cross-check page, where the same trend test is run on them and compared
        with our results.

        **Data access:** [NASA Giovanni](https://giovanni.gsfc.nasa.gov/) ·
        [NASA Hydrology Time Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series) ·
        [KNMI Climate Explorer](https://climexp.knmi.nl/)
        """
    )

with st.expander("MERRA-2 — Modern-Era Retrospective Analysis for Research and Applications"):
    st.markdown(
        """
        **Provider:** NASA Global Modeling and Assimilation Office (GMAO).

        **How it is used:** MERRA-2 provides atmospheric and land-surface
        reanalysis variables that can help describe broader environmental
        conditions. Reanalysis products combine observations with a numerical
        model; they are not direct measurements at every location.

        **Data access:** [NASA GES DISC — MERRA-2](https://disc.gsfc.nasa.gov/datasets?keywords=MERRA-2)
        """
    )

with st.expander("MODIS — Moderate Resolution Imaging Spectroradiometer"):
    st.markdown(
        """
        **Provider:** NASA.

        **How it is used:** MODIS products can provide satellite-based
        observations relevant to vegetation, land cover, and fire activity.
        Active-fire detections should not be interpreted as a direct measure
        of total burned area, and observations may be affected by clouds and
        other detection limitations.

        **Data access:** [NASA Earthdata — MODIS](https://www.earthdata.nasa.gov/data/instruments/modis)
        """
    )

with st.expander("NASA POWER — Prediction Of Worldwide Energy Resources"):
    st.markdown(
        """
        **Provider:** NASA Applied Sciences Program.

        **How it is used:** NASA POWER provides gridded meteorological and
        solar-related data products that can support environmental analysis.

        **Data access:** [NASA POWER](https://power.larc.nasa.gov/)
        """
    )

with st.expander("NASA FIRMS — Fire Information for Resource Management System"):
    st.markdown(
        """
        **Provider:** NASA.

        **How it is used:** FIRMS distributes satellite-derived active-fire
        and thermal-anomaly detections. Detection counts and fire radiative
        power are indicators of observed fire activity, not a complete record
        of every fire or a direct burned-area measurement.

        **Data access:** [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)
        """
    )

st.divider()
st.header("Technologies")

technology_items = [
    ("Python", "Core programming language"),
    ("Streamlit", "Interactive web application and dashboard"),
    ("Pandas", "Tabular data processing and analysis"),
    ("NumPy", "Numerical computing"),
    ("Plotly", "Interactive charts and geographic visualizations"),
    ("Earthaccess", "Access to supported NASA Earthdata resources"),
    ("SciPy and xarray", "Statistical functions and NetCDF data handling"),
    ("Requests", "Retrieval from NASA POWER and FIRMS web services"),
]

for technology, purpose in technology_items:
    st.markdown(f"- **{technology}** — {purpose}")

st.divider()
st.header("Acknowledgments")

st.markdown(
    """
    We acknowledge NASA, its data centers, mission teams, and scientific
    collaborators for making Earth-observation data and documentation
    available to researchers, students, and the public.

    We also thank the NASA Space Apps Challenge organizers, mentors, and
    community for creating an environment where people can explore
    meaningful challenges using open data.
    """
)

st.header("Methodology & Limitations")

st.markdown(
    """
    Counterpoint is an exploratory trend-analysis tool, not an official NASA
    product or a substitute for peer-reviewed scientific analysis.

    - Statistical trends indicate patterns in the selected observations; they
      do not, by themselves, establish cause and effect.
    - Different datasets have different spatial resolutions, temporal
      coverage, uncertainty, and measurement methods.
    - GRACE-derived total water storage changes should not be labeled as
      direct groundwater measurements.
    - Satellite fire detections are affected by observation conditions and
      should not be treated as a complete inventory of all fires.
    - Results should be interpreted together with dataset documentation and
      the project's validation notes.
    """
)

st.divider()
st.caption(
    "Counterpoint: Earth System Trend Detective | NASA Space Apps Challenge 2026"
)
