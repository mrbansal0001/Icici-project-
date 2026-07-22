"""
UDISE+ School Scraper — pincode-level extraction via the Know Your School API.

Instead of driving a browser, this talks directly to the JSON API that the
UDISE+ "Know Your School" site uses under the hood:

    GET  /web-app/api/getCaptcha
         -> {"status": true, "data": "<base64 png>"}
    GET  /web-app/api/search-schools?searchType=4&searchParam=<pincode>&captcha=<text>
         -> {"status": true, "data": {"content": [ {school}, ... ], ...}}

The captcha is server-side state keyed to the caller's IP and is single-use:
each successful search consumes the last captcha issued to that IP. So the loop
per pincode is: fetch a captcha -> OCR it with Tesseract -> search. On an
"Invalid Captcha" response we simply fetch a fresh captcha and try again.

Usage:
    python scraper.py --test                     # 3 sample pincodes
    python scraper.py --pincodes 110001 400001   # specific pincodes
    python scraper.py                            # all pincodes from pincodes.csv
    python scraper.py --limit 100                # only first 100 unprocessed pincodes
    python scraper.py --no-resume                # ignore existing checkpoint
    python scraper.py --save-captchas            # dump captcha images for debugging
"""

import argparse
import base64
import csv
import io
import json
import os
import random
import re
import sys
import time
from datetime import datetime

import requests
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
except ImportError:
    print("[ERROR] pytesseract not installed. Run: pip install pytesseract")
    sys.exit(1)

from config import (
    APP_SIGNATURE,
    BATCH_SIZE,
    CAPTCHA_DIR,
    CAPTCHA_ENDPOINT,
    CAPTCHA_MAX_RETRIES,
    CAPTCHA_PREPROCESSING,
    CHECKPOINT_FILE,
    DELAY_BETWEEN_REQUESTS,
    HTTP_MAX_RETRIES,
    OUTPUT_CSV,
    OUTPUT_DIR,
    PINCODES_CSV,
    REQUEST_TIMEOUT,
    SEARCH_ENDPOINT,
    SEARCH_TYPE_PINCODE,
    TESSERACT_CMD,
    USER_AGENT,
)

# Canonical CSV columns (every field the school records carry). Anything the API
# adds beyond this is ignored so the CSV header stays stable across appends.
FIELDNAMES = [
    "pincode", "udiseschCode", "schoolName", "schoolId",
    "schCategoryId", "schCatDesc", "schCategoryType",
    "schType", "schTypeDesc",
    "schMgmtId", "schMgmtDesc", "schMgmtDescSt", "schMgmtType", "schMgmtParentId",
    "schmgmtparentId", "schMgmNationalDesc", "schBroadMgmtId",
    "classFrm", "classTo",
    "schoolStatus", "schoolStatusName",
    "stateName", "districtName", "blockName", "clusterName", "villageName",
    "schLocRuralUrban", "schLocDesc",
    "email", "address", "latitude", "longitude",
    "lgdurbanlocalbodyId", "lgdurbanlocalbodyName", "lgdwardId", "lgdwardName",
    "lgdvillageId", "lgdvillName", "lgdpanchayatId", "lgdvillpanchayatName",
    "lgdblockId", "lgdblockName",
    "yearId", "yearDesc", "sessionYear", "lastmodifiedTime",
    "keyFlag", "pmShriYn", "isnewCy",
]


class UDISEApiScraper:
    """Scrapes school data from the UDISE+ JSON API by pincode."""

    def __init__(self, save_captchas=False):
        self.save_captchas = save_captchas
        self.session = requests.Session()
        self.session.headers.update({
            "X-APP-SIGNATURE": APP_SIGNATURE,
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://kys.udiseplus.gov.in/",
        })
        self.stats = {
            "pincodes_processed": 0,
            "pincodes_with_schools": 0,
            "pincodes_empty": 0,
            "pincodes_failed": 0,
            "schools_found": 0,
            "captcha_attempts": 0,
            "captcha_success": 0,
        }
        self._setup_tesseract()

    # ─── Tesseract ────────────────────────────────────────────────────────────
    def _setup_tesseract(self):
        paths = [
            TESSERACT_CMD,
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\ProgramData\chocolatey\bin\tesseract.exe",
            r"C:\tools\Tesseract-OCR\tesseract.exe",
        ]
        for path in paths:
            if path and os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"[OK] Tesseract found at: {path}")
                return
        try:
            pytesseract.get_tesseract_version()
            print("[OK] Tesseract found on system PATH")
            return
        except Exception:
            print("[WARN] Tesseract OCR not found. Captcha solving will fail.")
            print("       Install: https://github.com/UB-Mannheim/tesseract/wiki")
            print("       Or set TESSERACT_CMD in your environment / config.py")

    # ─── HTTP with backoff ───────────────────────────────────────────────────
    def _get(self, url, params=None):
        last_err = None
        for attempt in range(HTTP_MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                time.sleep(2 ** attempt)
        print(f"   [ERROR] HTTP failed after {HTTP_MAX_RETRIES} tries: {str(last_err)[:120]}")
        return None

    # ─── Captcha ─────────────────────────────────────────────────────────────
    def _fetch_captcha_image(self):
        data = self._get(CAPTCHA_ENDPOINT)
        if not data or not data.get("status") or not data.get("data"):
            return None
        try:
            img_bytes = base64.b64decode(data["data"])
            return Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            print(f"   [ERROR] Could not decode captcha: {e}")
            return None

    def _preprocess(self, image):
        cfg = CAPTCHA_PREPROCESSING
        if cfg.get("grayscale", True):
            image = ImageOps.grayscale(image)
        scale = cfg.get("scale_factor", 4)
        if scale > 1:
            image = image.resize((image.width * scale, image.height * scale), Image.LANCZOS)
        threshold = cfg.get("threshold", 140)
        image = image.point(lambda x: 255 if x > threshold else 0)
        if cfg.get("denoise", True):
            image = image.filter(ImageFilter.MedianFilter(size=3))
        return image

    def _ocr(self, image):
        whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        for psm in (7, 8, 6):
            try:
                text = pytesseract.image_to_string(
                    image, config=f"--psm {psm} --oem 3 -c tessedit_char_whitelist={whitelist}"
                )
                text = re.sub(r"[^A-Za-z0-9]", "", text)
                if len(text) >= 5:
                    return text
            except Exception:
                continue
        return ""

    def solve_captcha(self):
        """Fetch a fresh captcha and return the OCR'd text (or '' on failure)."""
        image = self._fetch_captcha_image()
        if image is None:
            return ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if self.save_captchas:
            os.makedirs(CAPTCHA_DIR, exist_ok=True)
            image.save(os.path.join(CAPTCHA_DIR, f"raw_{ts}.png"))
        processed = self._preprocess(image)
        if self.save_captchas:
            processed.save(os.path.join(CAPTCHA_DIR, f"proc_{ts}.png"))
        return self._ocr(processed)

    # ─── Search ──────────────────────────────────────────────────────────────
    def search_pincode(self, pincode):
        """
        Returns a list of school dicts (possibly empty) on success,
        or None if all captcha attempts were exhausted.
        """
        self.stats["pincodes_processed"] += 1

        for _ in range(CAPTCHA_MAX_RETRIES):
            self.stats["captcha_attempts"] += 1
            captcha = self.solve_captcha()
            if len(captcha) < 5:
                continue  # bad OCR, get a fresh captcha

            result = self._get(SEARCH_ENDPOINT, params={
                "searchType": SEARCH_TYPE_PINCODE,
                "searchParam": pincode,
                "captcha": captcha,
            })
            if result is None:
                continue  # network error, already backed off

            if result.get("status"):
                self.stats["captcha_success"] += 1
                content = (result.get("data") or {}).get("content") or []
                schools = [self._flatten(s, pincode) for s in content]
                if schools:
                    self.stats["pincodes_with_schools"] += 1
                    self.stats["schools_found"] += len(schools)
                else:
                    self.stats["pincodes_empty"] += 1
                return schools

            # status == False: distinguish captcha errors (retry) from real "no data"
            msg = json.dumps(result.get("error") or {}).lower()
            if "captcha" in msg:
                continue  # wrong/expired captcha -> fetch a new one and retry
            # Genuine non-captcha rejection (e.g. no records): treat as empty, stop.
            self.stats["pincodes_empty"] += 1
            return []

        self.stats["pincodes_failed"] += 1
        return None

    @staticmethod
    def _flatten(school, pincode):
        row = {k: school.get(k) for k in FIELDNAMES}
        row["pincode"] = school.get("pincode") or pincode
        return row

    # ─── Output ──────────────────────────────────────────────────────────────
    def _append_rows(self, rows):
        if not rows:
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        write_header = not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0
        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

    def _save_checkpoint(self, processed):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "processed_pincodes": sorted(processed),
                "stats": self.stats,
            }, f, indent=2)

    def _load_checkpoint(self):
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                cp = json.load(f)
            self.stats = cp.get("stats", self.stats)
            processed = set(cp.get("processed_pincodes", []))
            print(f"[FILE] Checkpoint: {len(processed)} pincodes already processed")
            return processed
        return set()

    # ─── Main loop ───────────────────────────────────────────────────────────
    def run(self, pincodes, resume=True, limit=None):
        processed = self._load_checkpoint() if resume else set()
        remaining = [p for p in pincodes if p not in processed]
        if limit:
            remaining = remaining[:limit]

        total = len(pincodes)
        print(f"\n{'='*60}")
        print("  UDISE+ School Scraper (API mode)")
        print(f"  Total pincodes:     {total}")
        print(f"  Already processed:  {len(processed)}")
        print(f"  To process now:     {len(remaining)}")
        print(f"{'='*60}\n")

        if not remaining:
            print("[OK] Nothing to do.")
            return

        try:
            for i, pincode in enumerate(remaining, 1):
                schools = self.search_pincode(pincode)
                if schools is None:
                    tag = "FAIL (captcha retries exhausted)"
                elif schools:
                    tag = f"{len(schools):>3} schools"
                else:
                    tag = "  0 schools"
                print(f"[{len(processed) + i}/{total}] {pincode}  {tag}")

                if schools:
                    self._append_rows(schools)
                processed.add(pincode)

                if i % BATCH_SIZE == 0:
                    self._save_checkpoint(processed)
                    print(f"   [SAVE] checkpoint @ {len(processed)} pincodes")

                time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))
        except KeyboardInterrupt:
            print("\n[WARN] Interrupted — saving checkpoint...")
        finally:
            self._save_checkpoint(processed)
            self.print_stats()

    def print_stats(self):
        s = self.stats
        print(f"\n{'='*60}")
        print("  Statistics")
        print(f"{'='*60}")
        print(f"  Pincodes processed:   {s['pincodes_processed']}")
        print(f"  With schools:         {s['pincodes_with_schools']}")
        print(f"  Empty (no schools):   {s['pincodes_empty']}")
        print(f"  Failed:               {s['pincodes_failed']}")
        print(f"  Schools found:        {s['schools_found']}")
        print(f"  Captcha attempts:     {s['captcha_attempts']}")
        print(f"  Captcha success:      {s['captcha_success']}")
        if s["captcha_attempts"]:
            rate = s["captcha_success"] / s["captcha_attempts"] * 100
            print(f"  Captcha OCR hit-rate: {rate:.1f}%")
        print(f"  Output CSV:           {OUTPUT_CSV}")
        print(f"{'='*60}")


def load_pincodes(path):
    with open(path, "r", encoding="utf-8") as f:
        return [row["pincode"].strip() for row in csv.DictReader(f) if row.get("pincode")]


def main():
    parser = argparse.ArgumentParser(description="UDISE+ School Scraper by Pincode (API mode)")
    parser.add_argument("--pincodes", nargs="+", help="Specific pincodes to scrape")
    parser.add_argument("--file", default=PINCODES_CSV, help="CSV of pincodes (column: pincode)")
    parser.add_argument("--test", action="store_true", help="Test with 3 sample pincodes")
    parser.add_argument("--limit", type=int, help="Process at most N unprocessed pincodes")
    parser.add_argument("--no-resume", action="store_true", help="Ignore existing checkpoint")
    parser.add_argument("--save-captchas", action="store_true", help="Save captcha images")
    args = parser.parse_args()

    if args.test:
        pincodes = ["110001", "400001", "560001"]
    elif args.pincodes:
        pincodes = args.pincodes
    else:
        if not os.path.exists(args.file):
            print(f"[ERROR] Pincode file not found: {args.file}")
            print("        Run: python extract_pincodes.py")
            sys.exit(1)
        pincodes = load_pincodes(args.file)

    print(f"[PIN] {len(pincodes)} pincode(s) queued")
    scraper = UDISEApiScraper(save_captchas=args.save_captchas)
    scraper.run(pincodes, resume=not args.no_resume, limit=args.limit)


if __name__ == "__main__":
    main()
