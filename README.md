# Counterpoint (Mirror Trends + Evidence Grade)
Real data only in the app. Steps:
1. `pip install -r requirements.txt`; set EARTHDATA_USERNAME / EARTHDATA_PASSWORD
2. `python counterpoint.py fetch`  (default short name TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4)
3. Verify boxes in `data/benchmark_regions.json` against the NASA story, set `"frozen": true`, commit BEFORE running
4. `python counterpoint.py run --grace data/<file>.nc --driver-var PRECTOTCORR [--monthly-check] [--jobs N]`
5. `python counterpoint.py validate`   (SYNTHETIC calibration, labelled; optional)
6. `streamlit run app.py`
Other variable (engine is variable-agnostic): `python counterpoint.py power --var T2M --step 10`
NOT verified on real files: GRACE dims/variable names, mascon-id layer (falls back to approximate blocks and says so), POWER JSON shape.
