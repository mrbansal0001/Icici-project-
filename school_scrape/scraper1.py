"""
UDISE+ School Scraper — pincode-level extraction via the Know Your School API.
Parallelized with ProcessPoolExecutor for high-speed OCR and extraction.

Usage:
    python scraper.py --test                 # 3 sample pincodes
    python scraper.py --pincodes 110001      # specific pincodes
    python scraper.py --workers 4            # adjust parallel process count
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
from concurrent.futures import ProcessPoolExecutor, as_completed

import requests
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
except ImportError:
    print("[ERROR] pytesseract not installed. Run: pip install pytesseract")
    sys.exit(1)

from config_parallel import (
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
    """Handles an isolated API scraping lifecycle inside a single process worker."""

    def __init__(self, save_captchas=False):
        self.save_captchas = save_captchas
        self.session = requests.Session()
        self.session.headers.update({
            "X-APP-SIGNATURE": APP_SIGNATURE,
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://kys.udiseplus.gov.in/",
        })
        self._setup_tesseract()

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
                return
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            pass

    def _get(self, url, params=None):
        for attempt in range(HTTP_MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except Exception:
                time.sleep(2 ** attempt)
        return None

    def _fetch_captcha_image(self):
        data = self._get(CAPTCHA_ENDPOINT)
        if not data or not data.get("status") or not data.get("data"):
            return None
        try:
            img_bytes = base64.b64decode(data["data"])
            return Image.open(io.BytesIO(img_bytes))
        except Exception:
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

    def search_pincode(self, pincode):
        captcha_attempts = 0
        for _ in range(CAPTCHA_MAX_RETRIES):
            captcha_attempts += 1
            captcha = self.solve_captcha()
            if len(captcha) < 5:
                continue

            result = self._get(SEARCH_ENDPOINT, params={
                "searchType": SEARCH_TYPE_PINCODE,
                "searchParam": pincode,
                "captcha": captcha,
            })
            if result is None:
                continue

            if result.get("status"):
                content = (result.get("data") or {}).get("content") or []
                schools = [self._flatten(s, pincode) for s in content]
                return {"status": "success", "schools": schools, "attempts": captcha_attempts}

            msg = json.dumps(result.get("error") or {}).lower()
            if "captcha" not in msg:
                return {"status": "empty", "schools": [], "attempts": captcha_attempts}

        return {"status": "failed", "schools": None, "attempts": captcha_attempts}

    @staticmethod
    def _flatten(school, pincode):
        row = {k: school.get(k) for k in FIELDNAMES}
        row["pincode"] = school.get("pincode") or pincode
        return row


def _worker_scrape_pincode(pincode, save_captchas):
    """Isolated target execution mapping function for child processes."""
    scraper = UDISEApiScraper(save_captchas=save_captchas)
    res = scraper.search_pincode(pincode)
    time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))
    return pincode, res


class ParallelScraperManager:
    """Manages file interactions, stats tracking, and the process lifecycle orchestration."""

    def __init__(self, save_captchas=False):
        self.save_captchas = save_captchas
        self.stats = {
            "pincodes_processed": 0,
            "pincodes_with_schools": 0,
            "pincodes_empty": 0,
            "pincodes_failed": 0,
            "schools_found": 0,
            "captcha_attempts": 0,
            "captcha_success": 0,
        }

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

    def _load_checkpoint(self, resume):
        if resume and os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                self.stats = cp.get("stats", self.stats)
                processed = set(cp.get("processed_pincodes", []))
                print(f"[FILE] Checkpoint loaded: {len(processed)} pincodes completed.")
                return processed
            except Exception:
                print("[WARN] Checkpoint unreadable. Starting fresh.")
        return set()

    def run(self, pincodes, resume=True, limit=None, max_workers=4):
        processed = self._load_checkpoint(resume)
        remaining = [p for p in pincodes if p not in processed]
        if limit:
            remaining = remaining[:limit]

        total_queue = len(remaining)
        total_all = len(pincodes)

        print(f"\n{'='*60}")
        print("   UDISE+ School Scraper (Parallel Multi-Core Mode)")
        print(f"   Total Pincodes Input : {total_all}")
        print(f"   Already Completed    : {len(processed)}")
        print(f"   To Process Now       : {total_queue}")
        print(f"   Concurrent Workers   : {max_workers}")
        print(f"{'='*60}\n")

        if not remaining:
            print("[OK] All tasks completed. Nothing to do.")
            return

        counter = 0
        try:
            # CPU-bound operations (Tesseract) thrive with ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(_worker_scrape_pincode, pin, self.save_captchas): pin
                    for pin in remaining
                }

                for future in as_completed(futures):
                    counter += 1
                    pin = futures[future]
                    try:
                        pincode, result = future.result()
                        self.stats["pincodes_processed"] += 1
                        self.stats["captcha_attempts"] += result["attempts"]

                        if result["status"] == "success":
                            self.stats["captcha_success"] += 1
                            self.stats["pincodes_with_schools"] += 1
                            self.stats["schools_found"] += len(result["schools"])
                            self._append_rows(result["schools"])
                            tag = f"{len(result['schools']):>3} schools"
                        elif result["status"] == "empty":
                            self.stats["captcha_success"] += 1
                            self.stats["pincodes_empty"] += 1
                            tag = "  0 schools"
                        else:
                            self.stats["pincodes_failed"] += 1
                            tag = "FAIL (Max captcha retries hit)"

                        processed.add(pincode)
                        progress = f"[{len(processed)}/{total_all}]"
                        print(f"{progress} Pin: {pincode} -> {tag}")

                        if counter % BATCH_SIZE == 0:
                            self._save_checkpoint(processed)

                    except Exception as e:
                        print(f"[CRITICAL ERROR] Failed worker processing for {pin}: {e}")

        except KeyboardInterrupt:
            print("\n[WARN] Interrupted. Forcing worker pool cleanup and saving status...")
        finally:
            self._save_checkpoint(processed)
            self.print_stats()

    def print_stats(self):
        s = self.stats
        print(f"\n{'='*60}")
        print("   Final Diagnostics")
        print(f"{'='*60}")
        print(f"   Pincodes Evaluated  : {s['pincodes_processed']}")
        print(f"   With Schools Found  : {s['pincodes_with_schools']}")
        print(f"   Zero Records (Empty): {s['pincodes_empty']}")
        print(f"   Network/OCR Failed  : {s['pincodes_failed']}")
        print(f"   Total Schools Saved : {s['schools_found']}")
        print(f"   Total OCR Attempts  : {s['captcha_attempts']}")
        print(f"   Successful Solves   : {s['captcha_success']}")
        if s["captcha_attempts"]:
            rate = (s["captcha_success"] / s["captcha_attempts"]) * 100
            print(f"   OCR Extraction Rate : {rate:.1f}%")
        print(f"   Destination Log File: {OUTPUT_CSV}")
        print(f"{'='*60}")


def load_pincodes(path):
    with open(path, "r", encoding="utf-8") as f:
        return [row["pincode"].strip() for row in csv.DictReader(f) if row.get("pincode")]


def main():
    parser = argparse.ArgumentParser(description="Parallel Engine UDISE+ Scraper")
    parser.add_argument("--pincodes", nargs="+", help="Specific target arrays")
    parser.add_argument("--file", default=PINCODES_CSV, help="Source mapping CSV path")
    parser.add_argument("--test", action="store_true", help="Quick run verification sampler")
    parser.add_argument("--limit", type=int, help="Truncate chunk configuration profile boundary")
    parser.add_argument("--no-resume", action="store_true", help="Bypass history system checkpoints")
    parser.add_argument("--save-captchas", action="store_true", help="Dump raw imagery debugging sets")
    parser.add_argument("--workers", type=int, default=4, help="Total processes running in parallel threads")
    args = parser.parse_args()

    if args.test:
        pincodes = ["110001", "400001", "560001"]
    elif args.pincodes:
        pincodes = args.pincodes
    else:
        if not os.path.exists(args.file):
            print(f"[ERROR] Pincode target database profile missing: {args.file}")
            sys.exit(1)
        pincodes = load_pincodes(args.file)

    print(f"[START] Enqueuing workload profile mapping arrays: {len(pincodes)} elements.")
    manager = ParallelScraperManager(save_captchas=args.save_captchas)
    manager.run(pincodes, resume=not args.no_resume, limit=args.limit, max_workers=args.workers)


if __name__ == "__main__":
    main()