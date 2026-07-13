from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "vahan-vehicle-registrations-by-vehicle-category.csv"
PDF_FILE = BASE_DIR / "Know-Your-RTO.pdf"
OUTPUT_RTO_LOOKUP = BASE_DIR / "rto_pincode_lookup.csv"
OUTPUT_BY_RTO = BASE_DIR / "vehicle_counts_by_rto.csv"
OUTPUT_BY_RTO_AND_TYPE = BASE_DIR / "vehicle_counts_by_rto_and_type.csv"
OUTPUT_BY_PINCODE = BASE_DIR / "vehicle_counts_by_pincode.csv"
OUTPUT_BY_PINCODE_AND_TYPE = BASE_DIR / "vehicle_counts_by_pincode_and_type.csv"
CHUNK_SIZE = 200_000
ROW_PATTERN = re.compile(
    r"^(?P<area>.+?)\s+(?P<pincode>\d{6})\s+(?P<taluka>.+?)\s+(?P<district>.+?)\s+(?P<rto_code>[A-Z]{2}\d{1,3})\s+(?P<rto_name>.+)$"
)


def _normalize_pincode(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
    )


def _extract_rto_pincode_lookup() -> pd.DataFrame:
    if not PDF_FILE.exists():
        raise FileNotFoundError(f"Missing PDF mapping file: {PDF_FILE}")

    reader = PdfReader(str(PDF_FILE))
    records: list[dict[str, str | int]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").encode("ascii", "ignore").decode("ascii")
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            match = ROW_PATTERN.match(line)
            if not match:
                continue

            record = match.groupdict()
            record["page_number"] = page_number
            records.append(record)

    if not records:
        raise ValueError(f"Could not extract any RTO/pincode rows from {PDF_FILE}")

    lookup = pd.DataFrame(records)
    lookup["pincode"] = _normalize_pincode(lookup["pincode"])
    lookup["rto_code"] = lookup["rto_code"].astype(str).str.strip()
    lookup["district"] = lookup["district"].astype(str).str.strip()
    lookup["taluka"] = lookup["taluka"].astype(str).str.strip()
    lookup["area"] = lookup["area"].astype(str).str.strip()
    lookup["rto_name"] = lookup["rto_name"].astype(str).str.strip()
    lookup = lookup.dropna(subset=["pincode", "rto_code"])
    lookup = lookup.drop_duplicates(subset=["pincode", "rto_code"], keep="first")

    return lookup


def _aggregate_chunks() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    office_parts: list[pd.DataFrame] = []
    office_type_parts: list[pd.DataFrame] = []

    reader = pd.read_csv(
        INPUT_FILE,
        usecols=["state_name", "office_name", "office_code", "vehicle_type", "registrations"],
        chunksize=CHUNK_SIZE,
    )

    for chunk in reader:
        chunk = chunk.copy()
        chunk["state_name"] = chunk["state_name"].astype(str).str.strip()
        chunk["office_name"] = chunk["office_name"].astype(str).str.strip()
        chunk["office_code"] = chunk["office_code"].astype(str).str.strip()
        chunk["vehicle_type"] = chunk["vehicle_type"].astype(str).str.strip()
        chunk["registrations"] = pd.to_numeric(chunk["registrations"], errors="coerce").fillna(0)

        office_parts.append(
            chunk.groupby(["state_name", "office_name", "office_code"], as_index=False)["registrations"].sum()
        )
        office_type_parts.append(
            chunk.groupby(["state_name", "office_name", "office_code", "vehicle_type"], as_index=False)["registrations"].sum()
        )

    total_by_rto = (
        pd.concat(office_parts, ignore_index=True)
        .groupby(["state_name", "office_name", "office_code"], as_index=False)["registrations"]
        .sum()
        .sort_values(["state_name", "registrations"], ascending=[True, False])
        .rename(columns={"registrations": "vehicle_count"})
    )

    total_by_rto_and_type = (
        pd.concat(office_type_parts, ignore_index=True)
        .groupby(["state_name", "office_name", "office_code", "vehicle_type"], as_index=False)["registrations"]
        .sum()
        .sort_values(["state_name", "office_code", "registrations"], ascending=[True, True, False])
        .rename(columns={"registrations": "vehicle_count"})
    )

    return total_by_rto, total_by_rto_and_type


def _map_to_pincodes(
    rto_counts: pd.DataFrame,
    rto_type_counts: pd.DataFrame,
    lookup: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mapped_counts = lookup.merge(
        rto_counts,
        left_on="rto_code",
        right_on="office_code",
        how="left",
    )

    mapped_type_counts = lookup.merge(
        rto_type_counts,
        left_on="rto_code",
        right_on="office_code",
        how="left",
        suffixes=("", "_rto"),
    )

    pincode_counts = (
        mapped_counts
        .groupby(["pincode", "area", "taluka", "district", "rto_code", "rto_name"], as_index=False)["vehicle_count"]
        .sum()
        .sort_values(["district", "vehicle_count", "pincode"], ascending=[True, False, True])
    )

    pincode_type_counts = (
        mapped_type_counts
        .groupby(["pincode", "area", "taluka", "district", "rto_code", "rto_name", "vehicle_type"], as_index=False)["vehicle_count"]
        .sum()
        .sort_values(["district", "pincode", "vehicle_count"], ascending=[True, True, False])
    )

    return pincode_counts, pincode_type_counts


def main() -> None:
    print("Extracting RTO-to-pincode lookup from PDF...")
    lookup = _extract_rto_pincode_lookup()
    lookup.to_csv(OUTPUT_RTO_LOOKUP, index=False)

    print("Aggregating vehicle registrations at RTO level...")
    total_by_rto, total_by_rto_and_type = _aggregate_chunks()
    total_by_rto.to_csv(OUTPUT_BY_RTO, index=False)
    total_by_rto_and_type.to_csv(OUTPUT_BY_RTO_AND_TYPE, index=False)

    print("Mapping RTO counts to pincodes...")
    total_by_pincode, total_by_pincode_and_type = _map_to_pincodes(total_by_rto, total_by_rto_and_type, lookup)

    total_by_pincode.to_csv(OUTPUT_BY_PINCODE, index=False)
    total_by_pincode_and_type.to_csv(OUTPUT_BY_PINCODE_AND_TYPE, index=False)

    pincode_with_counts = total_by_pincode[total_by_pincode["vehicle_count"] > 0]

    print(f"Saved RTO lookup to: {OUTPUT_RTO_LOOKUP}")
    print(f"Saved vehicle counts by RTO to: {OUTPUT_BY_RTO}")
    print(f"Saved vehicle counts by RTO and type to: {OUTPUT_BY_RTO_AND_TYPE}")
    print(f"Saved vehicle counts by pincode to: {OUTPUT_BY_PINCODE}")
    print(f"Saved vehicle counts by pincode and type to: {OUTPUT_BY_PINCODE_AND_TYPE}")
    print(f"Total RTO rows: {len(total_by_rto)}")
    print(f"Total pincode rows: {len(total_by_pincode)}")
    print(f"Pincodes with counts: {len(pincode_with_counts)}")
    print(f"Total pincode/type rows: {len(total_by_pincode_and_type)}")
    print("\nTop pincode rows:")
    print(pincode_with_counts.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
