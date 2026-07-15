"""
Central configuration for the UDISE+ pincode school scraper.

The scraper talks directly to the UDISE+ Know Your School JSON API
(discovered by inspecting the site), so no browser/Selenium is needed.
"""

import os

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

GEOJSON_FILE = os.path.join(BASE_DIR, "Datagov_Pincode_Boundaries.geojson")
PINCODES_CSV = os.path.join(BASE_DIR, "pincodes.csv")

OUTPUT_CSV = os.path.join(OUTPUT_DIR, "schools.csv")
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")
CAPTCHA_DIR = os.path.join(OUTPUT_DIR, "captchas")  # only used with --save-captchas

# ─── API ─────────────────────────────────────────────────────────────────────
API_BASE = "https://kys.udiseplus.gov.in/web-app/api/"
CAPTCHA_ENDPOINT = API_BASE + "getCaptcha"
SEARCH_ENDPOINT = API_BASE + "search-schools"

# searchType=4 is "PIN Code" search (2=state, 3=keyword, 4=pincode).
SEARCH_TYPE_PINCODE = 4

# Static header the SPA sends on every API call; the API rejects requests without it.
APP_SIGNATURE = "9f2c7a4b8e1d6c3f5a9b0e2d4f6a7c8b"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ─── Timing / retries ────────────────────────────────────────────────────────
# One captcha is consumed per successful search, so most "retries" are just
# OCR misreads that get a fresh captcha. Keep the delay polite to the server.
DELAY_BETWEEN_REQUESTS = (0.8, 1.8)   # random.uniform range, seconds, between pincodes
CAPTCHA_MAX_RETRIES = 12              # fresh-captcha attempts per pincode before giving up
REQUEST_TIMEOUT = 30                  # seconds per HTTP request
HTTP_MAX_RETRIES = 4                  # network-error retries (backoff) per request

BATCH_SIZE = 25                       # save checkpoint every N pincodes

# ─── Tesseract OCR ───────────────────────────────────────────────────────────
# First existing path wins; otherwise the system PATH is used.
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")

CAPTCHA_PREPROCESSING = {
    "grayscale": True,
    "scale_factor": 4,
    "threshold": 140,
    "denoise": True,
}
