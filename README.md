# Quick start: just launch

```bash
pip install -r requirements.txt
streamlit run app.py
```

On first launch the app runs every preliminary step by itself (`pipeline.py`) and shows a progress page:
download GRACE, grade the trends, register it, then fetch the NASA POWER variables in the background. The dashboard opens as soon as GRACE is ready; other layers appear when they finish.
It asks for your free Earthdata login once (or reads `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`, `~/.netrc` or `.env`). Wildfire layers and the groundwater anomaly are optional and set in the sidebar ("Background setup").
Finished steps are skipped on later launches. Progress is logged to `output/pipeline.log`. `python pipeline.py` runs the same steps in the terminal. Add `.env` to `.gitignore`.
Before the first launch, freeze `data/benchmark_regions.json` (see below); the app shows a warning if it is not frozen.

---

# Counterpoint: water + wildfire trends (real NASA data only)

Evidence-graded trend maps (A robust, B fragile, C indistinguishable from noise, D possible gap artifact, a caution flag) and a mirror finder for regions that move in opposite directions. Everything shown in the app must come from real data; `validate` and the tests use SYNTHETIC data and never feed the app.

## 0. Setup (once)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a free Earthdata Login at https://urs.earthdata.nasa.gov, then give the credentials to the scripts:

```bash
export EARTHDATA_USERNAME=your_username      # Windows PowerShell: $env:EARTHDATA_USERNAME="your_username"
export EARTHDATA_PASSWORD=your_password      # Windows PowerShell: $env:EARTHDATA_PASSWORD="your_password"
python -c "import earthaccess; print(earthaccess.login(strategy='environment').authenticated)"   # expect True
```

## 1. GRACE/GRACE-FO (REQUIRED: this is the whole project if time runs out)

```bash
python counterpoint.py fetch --short-name TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4   # one NetCDF into data/
ls data/*.nc
python tools/inspect_grace.py data/<FILE>.nc       # check variable names, units, time, mascon layer
```

`tools/inspect_grace.py` ends with a compatibility report. The loader expects the data variable `lwe_thickness`, an optional `land_mask`, and an optional mascon-ID layer (`mascon_ID` or `mascon_id`, case-insensitive). If the real names differ, pass them:

```bash
python counterpoint.py run --grace data/<FILE>.nc --var <DATA_VAR> --mascon-var <MASCON_ID_VAR> --jobs 4
```

If the output says "APPROXIMATE 3-degree blocks", no mascon layer was used: say so in the methods.

Before the first real run, freeze the benchmark: check every box and sign in `data/benchmark_regions.json` against the NASA story, add the sub-Saharan regions it names, set `"frozen": true`, and `git commit`. The run stores the file's SHA-256.

```bash
python counterpoint.py run --grace data/<FILE>.nc --jobs 4                      # first real run, no driver
python features.py register-grace                                                # makes GRACE visible to the app
python counterpoint.py run --grace data/<FILE>.nc --jobs 4 --driver-var PRECTOTCORR --top 10   # adds the precipitation driver check
python counterpoint.py run --grace data/<FILE>.nc --jobs 4 --monthly-check       # optional Hamed-Rao cross-check
python features.py register-grace                                                # run again after any new `run`
streamlit run app.py
```

## 2. MERRA-2 variables via NASA POWER (SHOULD: no login needed, results are cached)

Precipitation, soil wetness, evaporation, temperature, humidity, vapor pressure deficit and wind. Needs the GRACE run first (it reuses its units).

```bash
python features.py power --stride 4      # quick test, about a sixteenth of the points
python features.py power --stride 2      # fuller run; safe to rerun, it resumes from output/cache
```

## 3. Groundwater-style anomaly (OPTIONAL: needs Earthdata login and disk space)

GRACE minus GLDAS-Noah 2.1 monthly soil moisture, snow and canopy water. Download size was not verified; check free disk first.

```bash
python features.py groundwater --fetch   # downloads GLDAS_NOAH025_M v2.1 to data/gldas, then analyses
```

If it says no `GLDAS_NOAH025_M*.nc4` files were found, run `ls data/gldas` and adjust the pattern in `features.groundwater`.

## 4. Wildfire (OPTIONAL)

Get a free MAP_KEY at https://firms.modaps.eosdis.nasa.gov/api/area, then (bbox order is West South East North):

```bash
python features.py fires --map-key YOUR_KEY --bbox -125 30 -110 45 --start 2002 --end 2025
```

This sends about 1,750 requests per bounding box (5-day windows). `MODIS_SP` is a valid source name; check how far it runs with `https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/YOUR_KEY/MODIS_SP`. FIRMS archive CSVs work too: `python features.py fires --csv a.csv b.csv --start 2002 --end 2025`.

Burned area (`python features.py burned --nc FILE.nc --var NAME`) needs a lat/lon/time NetCDF you already have. No source was verified; skip it unless you have one.

## 4b. Independent cross-check (by hand, in the app)

Export one monthly time series for a point from Giovanni, GES DISC Hydrology Time Series or KNMI Climate Explorer, then upload it on the Cross-check page. The same trend test is run on it and compared with our feature at that location; each comparison is saved to `output/crosscheck.csv`. Nothing is fetched automatically (the Hydrology Time Series web service returned an HTML page to scripts, so that route was dropped).

## 5. Checks

```bash
pytest -q                          # synthetic regression tests for the fixes below
python counterpoint.py validate    # SYNTHETIC calibration -> output/validation.json; label it as such
python tools/region_series.py --file data/<FILE>.nc --region india --out out/   # independent single-box cross-check vs Giovanni/KNMI
```

## Changes from the first version

- `annual()` keeps peak-season series (3 months a year); before, `FIRE_SEASON` produced no results.
- Grade D now also needs a raw trend (p < 0.05), so noise series with a chance gap step are graded C, not D.
- Benchmark scoring is grade-aware: "recovered" needs the expected sign and grade A or B, with Benjamini-Hochberg control across the benchmark regions. Grade, q and robustness are shown per region.
- `--mascon-var` names the mascon-ID layer; `grade_frame` no longer crashes on empty input.
- App uses `width="stretch"` (requires streamlit 1.50 or newer); no deprecated `utcnow`.
- `data/benchmark_regions.json` is in the schema the code reads (`lat`/`lon` as [min, max], `expected` = up | down | none). It is a DRAFT with boxes from general knowledge.

## Verified and not verified

Verified: the GRACE short name above exists in the Earthdata catalog (JPL RL06.3Mv04, CRI, 0.5 degree, cm, one NetCDF-4 file from 2002-04-04, with a gridded mascon-ID number) and `MODIS_SP` is a valid FIRMS source. The pipeline, tests and app run end to end on SYNTHETIC data only.
Not verified: variable names and the mascon-ID layer's location in the real file, the GLDAS file pattern and size, the FIRMS end date and rate limits, and every benchmark box and expected sign.

## Limits

GRACE measures total water storage, not groundwater alone, at roughly 3 degrees resolution. The precipitation driver is a single MERRA-2 point at each region's centroid, so it can misrepresent a large region. About two decades can mistake natural cycles for trends. Reanalysis variables are model output constrained by observations. Fire counts are detections, not burned area. Everything is association, not cause.
