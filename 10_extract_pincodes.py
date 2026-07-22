"""
Extract the unique list of pincodes from the Datagov pincode-boundaries GeoJSON.

The GeoJSON is large (~90 MB) but every feature carries a "Pincode" property, so
we stream the file line-by-line and pull them out with a regex instead of loading
the whole thing into memory.

Usage:
    python extract_pincodes.py
    python extract_pincodes.py --geojson path/to/file.geojson --out pincodes.csv
"""

import argparse
import csv
import os
import re
import sys

from config import GEOJSON_FILE, PINCODES_CSV

PINCODE_RE = re.compile(r'"Pincode"\s*:\s*"?(\d{6})"?')


def extract_pincodes(geojson_path):
    """Return a sorted list of unique 6-digit pincodes found in the GeoJSON."""
    seen = set()
    with open(geojson_path, "r", encoding="utf-8") as f:
        for line in f:
            for pin in PINCODE_RE.findall(line):
                seen.add(pin)
    return sorted(seen)


def main():
    parser = argparse.ArgumentParser(description="Extract pincodes from GeoJSON")
    parser.add_argument("--geojson", default=GEOJSON_FILE, help="Input GeoJSON path")
    parser.add_argument("--out", default=PINCODES_CSV, help="Output CSV path")
    args = parser.parse_args()

    if not os.path.exists(args.geojson):
        print(f"[ERROR] GeoJSON not found: {args.geojson}")
        sys.exit(1)

    print(f"[..] Scanning {args.geojson} ...")
    pincodes = extract_pincodes(args.geojson)

    if not pincodes:
        print("[ERROR] No pincodes found. Is the 'Pincode' property present?")
        sys.exit(1)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pincode"])
        for pin in pincodes:
            writer.writerow([pin])

    print(f"[OK] {len(pincodes)} unique pincodes written to {args.out}")


if __name__ == "__main__":
    main()
