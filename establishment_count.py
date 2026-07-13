from __future__ import annotations

import warnings
from pathlib import Path

import geopandas as gpd
import osmium
import pandas as pd

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PINCODE_FILE = BASE_DIR / "Datagov_Pincode_Boundaries.geojson"
OSM_FILE = BASE_DIR / "india-260603.osm.pbf"
OUTPUT_FILE = BASE_DIR / "pincode_establishment_counts.csv"

# ---------------------------------------------------------
# TARGET TAGS (Updated from Image)
# ---------------------------------------------------------
TARGET_TAGS = {
    "amenity": {
        "atm", "bank", "bar", "bench", "bicycle_parking", "bicycle_rental",
        "cafe", "canteen", "charging_station", "cinema", "clinic", "clock",
        "college", "community_centre", "court_yard", "drinking_water", 
        "fountain", "fuel", "hospital", "ice_cream", "internet_cafe", 
        "kindergarten", "library", "marketplace", "parking", "parking_entrance", 
        "parking_space", "pharmacy", "place_of_worship", "post_box", "post_office",
        "restaurant", "school", "shelter", "shower", "social_facility", 
        "stage", "theatre", "toilets", "university", "vending_machine",
    },
    "shop": {
        "bakery", "books", "department_store", "mall", "mobile_phone", 
        "shopping_centre", "supermarket",
    },
}

class EstablishmentCollector(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, object]] = []
        self.seen_nodes = 0

    def _category(self, obj) -> str | None:
        for key, values in TARGET_TAGS.items():
            value = obj.tags.get(key)
            if value in values:
                return value
        return None

    def node(self, n):
        self.seen_nodes += 1
        if self.seen_nodes % 100000 == 0:
            print(f"Scanned nodes: {self.seen_nodes}, matches: {len(self.records)}")
            
        category = self._category(n)
        if category is None:
            return

        try:
            self.records.append(
                {
                    "category": category,
                    "lon": n.location.lon,
                    "lat": n.location.lat,
                }
            )
        except osmium.InvalidLocationError:
            pass


def load_pincodes() -> gpd.GeoDataFrame:
    if not PINCODE_FILE.exists():
        raise FileNotFoundError(f"Missing boundary file: {PINCODE_FILE}")

    pincodes = gpd.read_file(PINCODE_FILE, engine="pyogrio")
    
    pincodes = pincodes[["Pincode", "geometry"]].copy()
    pincodes = pincodes.rename(columns={"Pincode": "pincode"})
    pincodes["pincode"] = pincodes["pincode"].astype(str).str.strip()
    pincodes = pincodes[pincodes.geometry.notna()].copy()
    
    if pincodes.crs is None:
        pincodes = pincodes.set_crs(4326)
    else:
        pincodes = pincodes.to_crs(4326)
        
    return pincodes


def collect_establishments() -> gpd.GeoDataFrame:
    if not OSM_FILE.exists():
        raise FileNotFoundError(f"Missing OSM file: {OSM_FILE}. Did you run the osmium tags-filter step?")

    collector = EstablishmentCollector()
    collector.apply_file(str(OSM_FILE), locations=True)

    if not collector.records:
        return gpd.GeoDataFrame(columns=["category", "geometry"], geometry="geometry", crs=4326)

    df = pd.DataFrame(collector.records)
    establishments = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.lon, df.lat), 
        crs=4326
    )
    
    establishments["longitude"] = establishments.geometry.x
    establishments["latitude"] = establishments.geometry.y
    return establishments.drop(columns=["lon", "lat"])


def assign_pincodes(
    establishments: gpd.GeoDataFrame,
    pincodes: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    print("Running Spatial Join (Point in Polygon)...")
    joined = gpd.sjoin(
        establishments,
        pincodes[["pincode", "geometry"]],
        how="left",
        predicate="within",
    )

    unmatched = joined["pincode"].isna()
    if unmatched.any():
        print(f"Running Nearest Neighbor fallback for {unmatched.sum()} unmatched points...")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            fallback = gpd.sjoin_nearest(
                joined.loc[unmatched, ["category", "geometry"]],
                pincodes[["pincode", "geometry"]],
                how="left",
                distance_col="distance_to_pincode",
            )
        
        # Drop duplicates if a point is equally distant from two boundaries
        fallback = fallback[~fallback.index.duplicated(keep="first")]
        joined.loc[unmatched, "pincode"] = fallback["pincode"].to_numpy()

    return joined


def build_output(
    pinned_establishments: gpd.GeoDataFrame,
    pincodes: gpd.GeoDataFrame,
) -> pd.DataFrame:
    print("Running aggregations on CPU (Pandas)...")
    
    df_pinned = pinned_establishments.drop(columns=["geometry"]).dropna(subset=["pincode"])
    df_pincodes = pincodes.drop(columns=["geometry"])

    # Total counts
    total_counts = (
        df_pinned
        .groupby("pincode")
        .size()
        .reset_index(name="establishment_count")
    )

    # Category counts
    category_counts = (
        df_pinned
        .groupby(["pincode", "category"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Merge results
    final = df_pincodes.merge(total_counts, on="pincode", how="left")
    final = final.merge(category_counts, on="pincode", how="left")

    count_columns = [col for col in final.columns if col != "pincode"]
    final[count_columns] = final[count_columns].fillna(0)
    
    return final


def main() -> None:
    print("Loading boundaries...")
    pincodes = load_pincodes()
    print(f"Loaded pincodes: {len(pincodes)}")

    print("Parsing OSM File...")
    establishments = collect_establishments()
    print(f"Collected establishments: {len(establishments)}")

    pinned_establishments = assign_pincodes(establishments, pincodes)
    print(f"Matched establishments: {pinned_establishments['pincode'].notna().sum()}")

    final = build_output(pinned_establishments, pincodes)
    final.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rows: {len(final)}")
    print(final.head().to_string(index=False))


if __name__ == "__main__":
    main()