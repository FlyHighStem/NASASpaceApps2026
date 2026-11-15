from pathlib import Path
import json

import pandas as pd
import streamlit as st
import features as ft


# ---------------------------------------------------------------------
# Page setup and shared styling
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Data Explorer | Counterpoint",
    page_icon="📊",
    layout="wide",
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
VARS_DIR = OUTPUT_DIR / "vars"


def load_css():
    """Load the project's shared stylesheet when it is available."""
    css_path = PROJECT_DIR / "style.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css()

if st.button("← Back to Main Dashboard", key="back_home"):
    st.switch_page("home.py")


st.title("📊 Data Explorer")
st.caption(
    "Explore the datasets and processed outputs behind "
    "Counterpoint: Earth System Trend Detective."
)
st.divider()


# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------
def read_csv_if_available(path, **kwargs):
    """Read a CSV if it exists and is not empty; otherwise return an empty frame."""
    if path.exists() and path.stat().st_size > 5:
        try:
            return pd.read_csv(path, **kwargs)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
            return pd.DataFrame()
    return pd.DataFrame()


@st.cache_data
def load_feature(folder_string, stamp):
    """Load all available outputs for one feature folder."""
    folder = Path(folder_string)

    results = read_csv_if_available(folder / "results.csv")
    regions = read_csv_if_available(folder / "regions.csv")
    pairs = read_csv_if_available(folder / "pairs.csv")
    series = read_csv_if_available(
        folder / "series.csv",
        index_col=0,
        parse_dates=True,
    )

    meta_path = folder / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = {}
    else:
        meta = {}

    return results, regions, pairs, series, meta


def feature_description(feature_key):
    """Get a readable description from the feature catalog when possible."""
    item = ft.CATALOG.get(feature_key, {})
    if isinstance(item, dict):
        return (
            item.get("desc")
            or item.get("label")
            or item.get("name")
            or "Processed Earth-system feature."
        )
    return str(item) if item else "Processed Earth-system feature."


available_features = sorted(
    folder.name
    for folder in VARS_DIR.iterdir()
    if folder.is_dir() and (folder / "results.csv").exists()
) if VARS_DIR.exists() else []

if not available_features:
    st.warning(
        "No processed feature outputs were found yet. "
        "Run the feature-processing pipeline first, then refresh this page."
    )
    st.caption(f"Expected output location: `{VARS_DIR}`")
    st.stop()


# ---------------------------------------------------------------------
# Feature selection and overview
# ---------------------------------------------------------------------
selected_feature = st.selectbox(
    "Choose a processed feature",
    available_features,
    format_func=lambda key: ft.CATALOG.get(key, {}).get("label", key),
)

results, regions, pairs, series, meta = load_feature(
    str(VARS_DIR / selected_feature),
    (VARS_DIR / selected_feature / "results.csv").stat().st_mtime,  # reload when a run rewrites the files
)

st.subheader(ft.CATALOG.get(selected_feature, {}).get("label", selected_feature))
st.write(feature_description(selected_feature))

if meta:
    with st.expander("Feature metadata", expanded=False):
        st.json(meta)

# Display useful summary metrics without assuming a fixed schema.
metric_values = [
    ("Result rows", len(results)),
    ("Regional rows", len(regions)),
    ("Mirror-pair rows", len(pairs)),
    ("Time-series rows", len(series)),
]
metric_columns = st.columns(len(metric_values))
for column, (label, value) in zip(metric_columns, metric_values):
    column.metric(label, f"{value:,}")


# ---------------------------------------------------------------------
# Processed results
# ---------------------------------------------------------------------
st.divider()
st.subheader("Processed Results")
st.caption("The main trend-analysis output for the selected feature.")

if results.empty:
    st.info("No rows are available in results.csv for this feature.")
else:
    st.dataframe(results, width="stretch", hide_index=True)
    st.download_button(
        "Download results.csv",
        data=results.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_feature}_results.csv",
        mime="text/csv",
        key="download_results",
    )


# ---------------------------------------------------------------------
# Regional results
# ---------------------------------------------------------------------
st.divider()
st.subheader("Regional Results")

if regions.empty:
    st.info("No regional summary is available for this feature.")
else:
    st.dataframe(regions, width="stretch", hide_index=True)
    st.download_button(
        "Download regions.csv",
        data=regions.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_feature}_regions.csv",
        mime="text/csv",
        key="download_regions",
    )


# ---------------------------------------------------------------------
# Mirror pairs
# ---------------------------------------------------------------------
st.divider()
st.subheader("Mirror Cases")

if pairs.empty:
    st.info("No mirror-pair records are available for this feature.")
else:
    st.dataframe(pairs, width="stretch", hide_index=True)
    st.download_button(
        "Download pairs.csv",
        data=pairs.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_feature}_pairs.csv",
        mime="text/csv",
        key="download_pairs",
    )


# ---------------------------------------------------------------------
# Time series
# ---------------------------------------------------------------------
st.divider()
st.subheader("Monthly Time Series")

if series.empty:
    st.info("No time-series data is available for this feature.")
else:
    st.caption(
        "Raw monthly values, one column per unit id (the seasonal cycle is not removed here). "
        "The statistics use deseasonalised annual means of these series."
    )
    st.dataframe(series, width="stretch")
    st.download_button(
        "Download series.csv",
        data=series.to_csv().encode("utf-8"),
        file_name=f"{selected_feature}_series.csv",
        mime="text/csv",
        key="download_series",
    )

    numeric_columns = series.select_dtypes(include="number").columns.tolist()
    if numeric_columns:
        st.markdown("**Quick time-series view**")
        picked = st.multiselect(
            "Units to plot (column = unit id)", numeric_columns, default=numeric_columns[:3]
        )
        if picked:
            st.line_chart(series[picked])


# ---------------------------------------------------------------------
# Benchmark and project-wide files
# ---------------------------------------------------------------------
st.divider()
st.subheader("Benchmark Data")

try:
    _sm = json.loads((OUTPUT_DIR / "sources.json").read_text(encoding="utf-8"))
    if _sm.get("benchmark_frozen"):
        st.success("Region list was FROZEN before this run.")
    else:
        st.warning("Region list was NOT frozen before this run: scorecard is exploratory.")
except (OSError, ValueError):
    pass

benchmark_candidates = [
    OUTPUT_DIR / "benchmark.csv",
    VARS_DIR / selected_feature / "benchmark.csv",
]
benchmark_path = None if selected_feature != "grace_lwe" else next(
    (path for path in benchmark_candidates if path.exists() and path.stat().st_size > 5),
    None,
)

if benchmark_path:
    benchmark = read_csv_if_available(benchmark_path)
    if benchmark.empty:
        st.info("The benchmark file exists but contains no readable rows.")
    else:
        st.dataframe(benchmark, width="stretch", hide_index=True)
        st.download_button(
            "Download benchmark.csv",
            data=benchmark.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected_feature}_benchmark.csv",
            mime="text/csv",
            key="download_benchmark",
        )
else:
    st.info(
        "The benchmark scores the GRACE analysis only. Choose 'Water storage (GRACE)' above to see it."
        if selected_feature != "grace_lwe"
        else "No benchmark.csv file was found in the expected output locations."
    )

with st.expander("Other project output files"):
    for filename in ("results.geojson", "sources.json", "benchmark_regions.json", "crosscheck.csv"):
        candidates = [
            OUTPUT_DIR / filename,
            PROJECT_DIR / "data" / filename,
        ]
        found = next((path for path in candidates if path.exists()), None)
        if found:
            st.write(f"**{filename}** — `{found.relative_to(PROJECT_DIR)}`")
        else:
            st.write(f"**{filename}** — not found")


st.divider()
st.caption(
    "Counterpoint | Data Explorer — Values shown here are processed outputs. "
    "Interpret them alongside the project's methodology and data limitations."
)
