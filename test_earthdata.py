
import earthaccess
import os

# ==========================================
# CONFIGURATION
# ==========================================

DATASET = "MOD06_L2"
START_DATE = "2026-10-01"
END_DATE = "2026-10-05"

DOWNLOAD = False
DOWNLOAD_DIR = "./data"

# ==========================================
# AUTHENTICATION
# ==========================================

print("Connecting to NASA Earthdata...")

try:
    # First, try saved credentials
    auth = earthaccess.login(strategy="netrc")
    print("Using saved Earthdata credentials.")

except earthaccess.exceptions.LoginStrategyUnavailable:
    # If no saved credentials exist, ask once and save them
    print("No saved credentials found. Logging in...")

    auth = earthaccess.login(
        strategy="interactive",
        persist=True
    )

if not auth.authenticated:
    raise SystemExit("Authentication failed.")

print("Successfully authenticated!")

# ==========================================
# DATA SEARCH
# ==========================================

print("\nSearching NASA Earthdata...")

results = earthaccess.search_data(
    short_name=DATASET,
    temporal=(START_DATE, END_DATE)
)

print(f"\nDatasets found: {len(results)}")

# ==========================================
# PREVIEW RESULTS
# ==========================================

print("\nFirst 5 results:\n")

for i, result in enumerate(results[:5], start=1):
    print(f"--- Result {i} ---")
    print(result)

# ==========================================
# DOWNLOAD
# ==========================================

if DOWNLOAD and results:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print("\nDownloading data...")

    files = earthaccess.download(results, DOWNLOAD_DIR)

    print(f"\nDownloaded files: {len(files)}")

else:
    print("\nDownload skipped.")
    print("Set DOWNLOAD = True to download the results.")

print("\nProcess completed!")
