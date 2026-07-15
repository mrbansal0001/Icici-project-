# UDISE+ School Scraper — Pincode Level

Extracts school-level data from the UDISE+ **Know Your School** portal
(<https://kys.udiseplus.gov.in>) for every Indian pincode.

## How it works (important — this replaces the Selenium plan)

The site is an Angular SPA backed by a plain JSON API. Rather than driving a
headless browser and OCR-ing the on-screen captcha (the original
`implementation_plan.md` approach), this scraper calls that API directly:

| Step | Request |
|------|---------|
| Get captcha | `GET /web-app/api/getCaptcha` → `{"data": "<base64 png>"}` |
| Search      | `GET /web-app/api/search-schools?searchType=4&searchParam=<pincode>&captcha=<text>` |

Key facts discovered by inspecting the live site:

- The API requires a static header `X-APP-SIGNATURE` (in `config.py`).
- The captcha is **server-side state keyed to your IP** and is **single-use** —
  each successful search consumes the captcha last issued to your IP. There is
  no token/cookie; you just fetch a captcha, solve it, and search.
- `search-schools` returns the **complete** school list for a pincode in one
  response (no pagination), including UDISE code, name, management, category,
  class range, status, full geography, address and lat/long.

The captcha still has to be solved, so the scraper OCRs it with **Tesseract**.
On an `Invalid Captcha` response it just grabs a fresh captcha and retries — a
cheap operation, so OCR misreads are not fatal.

Compared to the Selenium plan this is dramatically faster (no browser),
returns clean structured JSON (no HTML table scraping), and is far more robust.

## Setup

```bash
pip install -r requirements.txt
```

Install the Tesseract OCR **engine** (the `pytesseract` pip package is only a
wrapper):

- Windows: <https://github.com/UB-Mannheim/tesseract/wiki> (or `winget install UB-Mannheim.TesseractOCR`)
- If it is not on your PATH, set `TESSERACT_CMD` in `config.py` or as an env var.

## Usage

```bash
# 1. Build the pincode list from the GeoJSON (~19,300 unique pincodes)
python extract_pincodes.py

# 2. Smoke-test with 3 sample pincodes
python scraper.py --test

# 3. Try a small batch
python scraper.py --limit 100

# 4. Full run (resumes automatically from output/checkpoint.json)
python scraper.py
```

Other flags:

- `--pincodes 110001 400001` — scrape specific pincodes
- `--limit N` — process at most N unprocessed pincodes
- `--no-resume` — ignore the existing checkpoint
- `--save-captchas` — dump raw + preprocessed captcha images to `output/captchas/`

## Output

- `output/schools.csv` — one row per school, appended as the run progresses.
- `output/checkpoint.json` — processed pincodes + stats, for resume.

Interrupting with `Ctrl+C` saves a checkpoint; rerunning continues where it
stopped.

## Files

| File | Purpose |
|------|---------|
| `config.py` | Endpoints, header, timing, retry and OCR settings |
| `extract_pincodes.py` | Streams the GeoJSON and writes `pincodes.csv` |
| `scraper.py` | The API scraper (captcha OCR, search, checkpoint, CSV) |
| `scraper (1).py` | Original Selenium+OCR draft — superseded, kept for reference |

## Notes

- **Throughput** is bounded by the captcha: one solved captcha per pincode.
  With OCR retries expect a few seconds per pincode; ~19,300 pincodes is a
  multi-hour run. Use `--limit` to work in chunks; the checkpoint makes this safe.
- **Be considerate.** This hits a government server; keep the delays in
  `config.py` polite and avoid parallel hammering. Intended for
  educational/research use — confirm you are authorised before running at scale.
