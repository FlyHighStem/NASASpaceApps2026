Create a login at https://urs.earthdata.nasa.gov.

Then set

export EARTHDATA_USERNAME=username

export EARTHDATA_PASSWORD=mypass

Then to access GRACE/GRACE-FO data

python counterpoint.py fetch --short-name TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4

python counterpoint.py run --grace data/GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc --driver-var PRECTOTCORR

To access POWER data

python counterpoint.py power --bbox -35 35 -75 95 --step 5 --var PRECTOTCORR --driver-var T2M
