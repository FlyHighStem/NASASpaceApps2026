# Counterpoint: water + wildfire trends (real NASA data only)
1. GRACE (done):  python counterpoint.py run --grace data/<file>.nc
2. python features.py register-grace
3. python features.py power --stride 2                    # precip, soil wetness, evaporation, T2M, RH2M, VPD, wind
4. Wildfire (free MAP_KEY: firms.modaps.eosdis.nasa.gov/api/area):
   python features.py fires --map-key KEY --bbox -125 30 -110 45 --start 2002 --end 2025    # example: California -> counts, intensity (FRP), peak-season
5. python features.py groundwater --fetch               # needs Earthdata login env vars; downloads GLDAS-Noah monthly
6. optional: python features.py burned --nc FILE.nc --var NAME
7. streamlit run app.py