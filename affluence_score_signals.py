"""
================================================================================
 PINCODE AFFLUENCE SCORING PIPELINE
================================================================================
Purpose:
    Turns the raw micro-market signal columns (MF distributor counts, retail
    branches, corporate hubs, golf courses, hospitals, vehicles, schools, etc.)
    into a single, explainable 0-100 "Affluence Score" per pincode, plus a
    business-friendly tier (Platinum / Gold / Silver / Standard) that an
    ICICI Prudential agent can act on directly.

Method (see chat discussion for full reasoning):
    1. Group raw signals into 4 interpretable "pillars" so we don't
       double-count correlated columns.
    2. Convert every raw column to a PERCENTILE RANK (0-100) instead of
       min-max or z-score scaling. Percentile rank is robust to the extreme
       outliers and heavy skew we found in columns like
       `distributed_vehicle_count` (max ~600k vs a median in the low
       hundreds), and it maps directly to an agent-friendly sentence like
       "this pincode is in the top 3% for vehicle ownership".
    3. Average percentiles within each pillar -> pillar score (0-100).
    4. Combine the 4 pillar scores with weights -> final Affluence Score.
       Weights start EQUAL (25% each) as a defensible baseline.
    5. Run a quick PCA on the standardized raw columns purely as a SANITY
       CHECK -- to see whether the variance structure of the data roughly
       agrees with equal pillar weighting. This does NOT overwrite your
       business weights; it just tells you whether to reconsider them.
    6. Bucket the final score into tiers for the agent-facing output.
    7. Validate the result against a handful of pincodes we already know
       the real-world affluence of (this list came out of manual research
       earlier in the project) as a face-validity check.

Usage:
    python affluence_score_pipeline.py

Output:
    Writes `final_master_dataset_scored.csv` next to the input file, with
    added columns: pillar scores, Affluence_Score, Affluence_Tier.
================================================================================
"""

import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# ------------------------------------------------------------------------
# CONFIG -- edit these if your file path, column names, or weights change
# ------------------------------------------------------------------------

# Path to your dataset on your local machine.
INPUT_PATH = "/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_v3.csv"

# Output will be saved alongside the input, with a "_scored" suffix.
OUTPUT_PATH = "/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_scored_v2.csv"

# The unique key column identifying each row.
ID_COL = "pincode"

# --- Pillar definitions ---------------------------------------------------
# Each pillar groups raw columns that measure a similar underlying concept.
# This avoids one idea (e.g. "lots of retail") silently getting counted
# 3-4 times just because it happens to have 3-4 correlated columns.
PILLARS = {
    "Financial_Penetration": [
        "MF_Distributor_Count",
        "Investment_Advisor_Count",
    ],
    "Commercial_Vibrancy": [
        "Total_Corporate_Hubs",
        "Total_Retail_Branches",
        "Retail_Private_to_Public_Ratio",
    ],
    "Lifestyle_Premium": [
        "premium_store_count",
        "Golf_Course_Count",
    ],
    "Infrastructure_Scale": [
        "nabh_hospital_count",
        "ev_charging_station_count",
        "distributed_school_count",
        "establishment_count",
    ],
}

# Weight given to each pillar in the final composite score.
# Start equal (25% each) -- simple, defensible, and easy to explain to a
# non-technical stakeholder. Adjust only with a clear business reason
# (the PCA sanity check below will tell you if the data itself suggests
# a different emphasis).
PILLAR_WEIGHTS = {
    "Financial_Penetration": 0.25,
    "Commercial_Vibrancy": 0.25,
    "Lifestyle_Premium": 0.25,
    "Infrastructure_Scale": 0.25,
}

# Tier cutoffs, expressed as the top X% of pincodes by Affluence Score.
# e.g. "Platinum" = top 2% of all pincodes nationally.
TIER_CUTOFFS = [
    ("Platinum", 98),   # top 2%
    ("Gold", 90),       # top 10%
    ("Silver", 70),     # top 30%
    ("Standard", 0),    # everyone else
]

# A handful of pincodes with KNOWN real-world affluence, used purely to
# sanity-check the final score at the end of the script (face validity).
# This list came from manual research earlier in the project, not from
# the model itself, so it's an independent check.
KNOWN_PINCODES = {
    "560001": "Bangalore - MG Road/CBD (expect very high)",
    "122002": "Gurgaon - DLF City (expect very high)",
    "110001": "Delhi - Connaught Place (expect high)",
    "400026": "Mumbai - Worli (expect high)",
    "500034": "Hyderabad - Banjara Hills (expect high)",
    "400006": "Mumbai - Malabar Hill (expect high-ish)",
    "845401": "Rural Bihar, Muzaffarpur district (expect low)",
    "262401": "Rural Uttarakhand/UP border (expect low)",
    "752101": "Rural Odisha (expect low)",
}


# ------------------------------------------------------------------------
# STEP 0 -- Load and validate the data
# ------------------------------------------------------------------------

def load_data(path: str) -> pd.DataFrame:
    """Load the CSV and run basic sanity checks before scoring anything."""
    # Ensure pincode is read as string
    df = pd.read_csv(path, dtype={ID_COL: str})
    
    # Strip any potential '.0' or whitespace
    df[ID_COL] = df[ID_COL].str.replace(r"\.0$", "", regex=True).str.strip()

    # Check every column the pillars need is actually present.
    needed_cols = [ID_COL] + [c for cols in PILLARS.values() for c in cols]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Input file is missing expected columns: {missing}")

    n_dupes = df[ID_COL].duplicated().sum()
    if n_dupes:
        print(f"[WARNING] {n_dupes} duplicate {ID_COL} rows found.")
        df = df.drop_duplicates(subset=ID_COL, keep="first")

    n_nulls = df[needed_cols].isna().sum().sum()
    if n_nulls:
        df[needed_cols] = df[needed_cols].fillna(0)

    return df


# ------------------------------------------------------------------------
# STEP 1-3 -- Percentile-rank every raw column, then average within pillar
# ------------------------------------------------------------------------

def compute_pillar_scores(df: pd.DataFrame) -> pd.DataFrame:
    pillar_scores = pd.DataFrame(index=df.index)

    for pillar_name, cols in PILLARS.items():
        percentile_cols = df[cols].rank(pct=True) * 100
        pillar_scores[pillar_name] = percentile_cols.mean(axis=1)

    return pillar_scores


# ------------------------------------------------------------------------
# STEP 4 -- Combine pillar scores into one final weighted composite
# ------------------------------------------------------------------------

def compute_affluence_score(pillar_scores: pd.DataFrame) -> pd.Series:
    weights = pd.Series(PILLAR_WEIGHTS)
    if not np.isclose(weights.sum(), 1.0):
        raise ValueError(f"PILLAR_WEIGHTS must sum to 1.0, got {weights.sum()}")
    return (pillar_scores[weights.index] * weights).sum(axis=1)


# ------------------------------------------------------------------------
# STEP 5 -- PCA sanity check
# ------------------------------------------------------------------------

def pca_sanity_check(df: pd.DataFrame) -> None:
    all_cols = [c for cols in PILLARS.values() for c in cols]
    X = StandardScaler().fit_transform(df[all_cols])

    pca = PCA(n_components=min(5, len(all_cols)))
    pca.fit(X)

    print("\n--- PCA sanity check (does not affect the score) ---")
    print("Variance explained by first 5 components:",
          np.round(pca.explained_variance_ratio_ * 100, 1), "%")

    top_loadings = pd.Series(pca.components_[0], index=all_cols) \
        .abs().sort_values(ascending=False).head(5)
    print("Columns driving the 1st principal component (by |loading|):")
    print(top_loadings.round(3).to_string())
    print("--- end PCA sanity check ---\n")


# ------------------------------------------------------------------------
# STEP 6 -- Convert numeric score into agent-facing tiers
# ------------------------------------------------------------------------

def assign_tier(score: float, cutoffs: list) -> str:
    for tier_name, threshold in cutoffs:
        if score >= threshold:
            return tier_name
    return cutoffs[-1][0]


def compute_tiers(affluence_score: pd.Series) -> pd.Series:
    score_percentile = affluence_score.rank(pct=True) * 100
    return score_percentile.apply(lambda s: assign_tier(s, TIER_CUTOFFS))


# ------------------------------------------------------------------------
# STEP 7 -- Face-validity check against known real-world pincodes
# ------------------------------------------------------------------------

def print_known_pincode_check(df: pd.DataFrame) -> None:
    print("\n--- Face-validity check on known pincodes ---")
    check_df = df[df[ID_COL].isin(KNOWN_PINCODES)].copy()
    check_df["expectation"] = check_df[ID_COL].map(KNOWN_PINCODES)
    cols_to_show = [ID_COL, "expectation", "Affluence_Score", "Affluence_Tier"]
    if not check_df.empty:
        print(check_df[cols_to_show]
              .sort_values("Affluence_Score", ascending=False)
              .to_string(index=False))
    else:
        print("None of the test pincodes were found in the dataset.")
    print("--- end face-validity check ---\n")


# ------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------

def main():
    df = load_data(INPUT_PATH)

    pillar_scores = compute_pillar_scores(df)
    df = pd.concat([df, pillar_scores], axis=1)

    df["Affluence_Score"] = compute_affluence_score(pillar_scores).round(2)
    df["Affluence_Tier"] = compute_tiers(df["Affluence_Score"])

    pca_sanity_check(df)
    print_known_pincode_check(df)

    df = df.sort_values("Affluence_Score", ascending=False)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Scored {len(df)} pincodes.")
    print("\nTier distribution:")
    print(df["Affluence_Tier"].value_counts())
    print(f"\nSaved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
