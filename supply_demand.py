import os
import pandas as pd


STATBEL_SUPPLY = "data/processed/self_employed_entrepreneurs_BE_2017_2025.csv"
EURES_2022 = "data/external/eures/ShortagesSurpluses_2022.xlsx"
EURES_2023 = "data/external/eures/ShortagesSurpluses_2023.xlsx"
EURES_2024 = "data/external/eures/ShortagesSurpluses_2024.xlsx"

OUT_DIR = "data/processed"
os.makedirs(OUT_DIR, exist_ok=True)


def load_statbel_supply(path: str):
    df = pd.read_csv(path)
    # national
    nat = (df.groupby(["year","sector_code","sector_name_en"], as_index=False)["entrepreneurs"]
             .sum()
             .rename(columns={"entrepreneurs":"supply_self_employed"}))
    # regional
    reg = (df.groupby(["year","region_name_en","sector_code","sector_name_en"], as_index=False)["entrepreneurs"]
             .sum()
             .rename(columns={"entrepreneurs":"supply_self_employed"}))
    return nat, reg

def read_eures_sheet(path: str, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    # drop language-specific cols
    rename = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc.startswith("year"): rename[c] = "Year"
        elif lc in ("iso","country","country_code"): rename[c] = "ISO"
        elif ("isco" in lc and "title" in lc): rename[c] = "ISCO4 title"
        elif ("isco" in lc and "code" in lc): rename[c] = "ISCO4 code"
        elif "imbalance" in lc: rename[c] = "Imbalance"
    df = df.rename(columns=rename)
    keep = [c for c in ["Year","ISO","ISCO4 title","ISCO4 code","Imbalance"] if c in df.columns]
    return df[keep]

def load_eures(*paths: str) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            sh = read_eures_sheet(p, "Shortage")
        except Exception:
            sh = pd.DataFrame()
        try:
            su = read_eures_sheet(p, "Surplus")
        except Exception:
            su = pd.DataFrame()
        frames += [sh, su]
    df = pd.concat(frames, ignore_index=True)
    df = df[df["ISO"].astype(str).str.upper() == "BE"].copy()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    return df.dropna(subset=["Year"])

def imbalance_to_score(x: str) -> float:
    t = str(x).strip().lower()
    if t == "shortage": return 1.0
    if t == "surplus": return -1.0
    if "both shortage and surplus" in t: return 0.5
    return 0.0

# actual cleaning function for Statbel data
def isco_title_to_nace(title: str):
    t = str(title).lower()
    if any(k in t for k in ["nurse","medical","health","care worker","paramedical","doctor","physician","midwife","social work"]): return "Q"
    if any(k in t for k in ["plumber","electrician","bricklayer","roofer","carpenter","builder","construction","insulation","glazier","painter","tiler"]): return "F"
    if any(k in t for k in ["welder","machinist","metal","machinery","industrial","process","assembly","manufacturing"]): return "C"
    if any(k in t for k in ["driver","truck","bus","transport","logistics","postal","courier","delivery","warehouse","forklift"]): return "H"
    if any(k in t for k in ["software","developer","programmer","ict"," it","data ","systems","network","cyber","ai ","cloud","devops"]): return "J"
    if "teacher" in t or "teaching" in t: return "P"
    if any(k in t for k in ["sales","cashier","shop","retail"]): return "G"
    if any(k in t for k in ["cook","chef","waiter","waitress","kitchen","restaurant","hotel","hospitality","barista"]): return "I"
    if any(k in t for k in ["cleaner","cleaning","housekeeper","janitor"]): return "N"
    if any(k in t for k in ["hairdresser","beautician","cosmetician","massage","launderer","shoemaker","tailor","seamstress"]): return "S"
    if any(k in t for k in ["farmer","agricultur","crop","livestock","dairy","forestry","fishing"]): return "A"
    if "real estate" in t or "property manager" in t: return "L"
    if any(k in t for k in ["accountant","auditor","bank","finance","financial","insur"]): return "K"
    if any(k in t for k in ["architect","engineer","lawyer","consultant","scientist","laboratory","lab technician","marketing manager","hr manager","r&d manager"]): return "M"
    if any(k in t for k in ["artist","musician","recreation","sports","fitness trainer"]): return "R"
    if any(k in t for k in ["police","fire-fighter","public administration","customs"]): return "O"
    return None

def build():
    # 1) supply
    sup_nat, sup_reg = load_statbel_supply(STATBEL_SUPPLY)

    # 2) demand (EURES)
    eures = load_eures(EURES_2022, EURES_2023, EURES_2024)
    eures["demand_score"] = eures["Imbalance"].map(imbalance_to_score)
    eures["sector_code"] = eures["ISCO4 title"].map(isco_title_to_nace)

    # agregate demand by year and sector
    demand = (eures.dropna(subset=["sector_code"])
                   .groupby(["Year","sector_code"], as_index=False)["demand_score"]
                   .mean()
                   .rename(columns={"Year":"year"}))
    demand["sector_code"] = demand["sector_code"].str.upper()

    # 3) join: national
    nat = sup_nat.merge(demand, on=["year","sector_code"], how="left")
    nat["demand_score"] = nat["demand_score"].fillna(0.0)

    # 4) join: regional
    reg = sup_reg.merge(demand, on=["year","sector_code"], how="left")
    reg["demand_score"] = reg["demand_score"].fillna(0.0)

    # 5) save
    nat_out = os.path.join(OUT_DIR, "supply_demand_BE_2017_2025.csv")
    reg_out = os.path.join(OUT_DIR, "supply_demand_BE_by_region_2017_2025.csv")
    nat.to_csv(nat_out, index=False, encoding="utf-8-sig")
    reg.to_csv(reg_out, index=False, encoding="utf-8-sig")
    print("✓ Saved:", nat_out)
    print("✓ Saved:", reg_out)

if __name__ == "__main__":
    build()
