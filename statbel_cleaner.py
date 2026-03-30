import os
import re
import glob
import pandas as pd

# === Settings ===
INPUT_DIR = "data/raw"     # path to input files
OUTPUT_DIR = "data/processed"  # save path for processed data
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Data patterns
PATTERNS = [
    os.path.join(INPUT_DIR, "TF_ENTREP_NACE_*.xlsx"),
    os.path.join(INPUT_DIR, "VF_ENTREP_NACE_*.xlsx"),
]

# Rename map
RENAME = {
    "CD_NACE": "sector_code",
    "TX_NACE_EN_LVL1": "sector_name_en",
    "CD_RGN_REFNIS": "region_code",
    "TX_RGN_DESCR_EN": "region_name_en",
    "CD_GENDER": "gender_code",
    "TX_GENDER_DESCR_EN": "gender_name_en",
    "CD_AGE_RANGE": "age_code",
    "AGE_RANGE_DESCR_EN": "age_group_en",
    "MS_ENTREP_NUM": "entrepreneurs",
}

# Drop language-specific columns by prefix
DROP_LANG_PREFIXES = (
    "TX_NACE_FR", "TX_NACE_NL",
    "TX_RGN_DESCR_FR", "TX_RGN_DESCR_NL",
    "TX_GENDER_DESCR_FR", "TX_GENDER_DESCR_NL",
    "AGE_RANGE_DESCR_FR", "AGE_RANGE_DESCR_NL"
)

YEAR_RE = re.compile(r"(\d{4})")

def extract_year(path: str) -> int | None:
    m = YEAR_RE.search(os.path.basename(path))
    return int(m.group(1)) if m else None

def pick_sheet(xls: pd.ExcelFile, year: int | None) -> str:
    if year:
        name = f"VF_ENTREP_NACE_{year}"
        if name in xls.sheet_names:
            return name
    if "Table" in xls.sheet_names:
        return "Table"
    if "VF_ENTREP_NACE" in xls.sheet_names:
        return "VF_ENTREP_NACE"
    return xls.sheet_names[0]

def read_one(path: str) -> pd.DataFrame:
    year = extract_year(path)

    xls = pd.ExcelFile(path, engine="openpyxl")
    sheet = pick_sheet(xls, year)
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")

    # drop language-specific cols
    cols_to_drop = [c for c in df.columns if any(c.startswith(pref) for pref in DROP_LANG_PREFIXES)]
    df = df.drop(columns=cols_to_drop, errors="ignore")

    # keep & rename
    keep_src = [c for c in RENAME if c in df.columns]
    df = df[keep_src].rename(columns=RENAME)

    # add year if absent
    if "year" not in df.columns:
        df["year"] = year

    # types
    if "region_code" in df.columns:
        df["region_code"] = pd.to_numeric(df["region_code"], errors="coerce").astype("Int64")
    if "entrepreneurs" in df.columns:
        df["entrepreneurs"] = pd.to_numeric(df["entrepreneurs"], errors="coerce")

    for c in ("sector_name_en", "region_name_en", "gender_name_en", "age_group_en"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    order = [
        "year",
        "region_code", "region_name_en",
        "sector_code", "sector_name_en",
        "gender_code", "gender_name_en",
        "age_code", "age_group_en",
        "entrepreneurs",
    ]
    df = df[[c for c in order if c in df.columns]]

    df = df.dropna(subset=["entrepreneurs"])
    return df

def save_dimensions(df: pd.DataFrame):
    if {"sector_code","sector_name_en"} <= set(df.columns):
        dim = (df[["sector_code","sector_name_en"]]
               .dropna().drop_duplicates()
               .sort_values(["sector_code","sector_name_en"]))
        dim.to_csv(os.path.join(OUTPUT_DIR, "dim_sector.csv"), index=False, encoding="utf-8-sig")
    if {"region_code","region_name_en"} <= set(df.columns):
        dim = (df[["region_code","region_name_en"]]
               .dropna().drop_duplicates()
               .sort_values(["region_code","region_name_en"]))
        dim.to_csv(os.path.join(OUTPUT_DIR, "dim_region.csv"), index=False, encoding="utf-8-sig")
    if {"gender_code","gender_name_en"} <= set(df.columns):
        dim = (df[["gender_code","gender_name_en"]]
               .dropna().drop_duplicates()
               .sort_values(["gender_code","gender_name_en"]))
        dim.to_csv(os.path.join(OUTPUT_DIR, "dim_gender.csv"), index=False, encoding="utf-8-sig")
    if {"age_code","age_group_en"} <= set(df.columns):
        dim = (df[["age_code","age_group_en"]]
               .dropna().drop_duplicates()
               .sort_values(["age_code","age_group_en"]))
        dim.to_csv(os.path.join(OUTPUT_DIR, "dim_age.csv"), index=False, encoding="utf-8-sig")

def main():
    files = []
    for pat in PATTERNS:
        files.extend(glob.glob(pat))
    files = sorted(files)
    if not files:
        raise SystemExit(f"No input files found in {INPUT_DIR}. Expected TF/VF_ENTREP_NACE_YYYY.xlsx")

    frames = []
    for f in files:
        try:
            print("Reading:", f)
            frames.append(read_one(f))
        except Exception as e:
            print("  -> skipped:", f, "|", e)

    if not frames:
        raise SystemExit("No data parsed.")

    all_df = pd.concat(frames, ignore_index=True)

    if "year" in all_df.columns:
        all_df["year"] = pd.to_numeric(all_df["year"], errors="coerce").astype("Int64")
    all_df["entrepreneurs"] = pd.to_numeric(all_df["entrepreneurs"], errors="coerce")

    out_fact = os.path.join(OUTPUT_DIR, "self_employed_entrepreneurs_BE_2017_2025.csv")
    all_df.to_csv(out_fact, index=False, encoding="utf-8-sig")
    print("Saved fact:", out_fact, "| rows:", len(all_df))

    save_dimensions(all_df)
    print("Saved dimensions in:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
