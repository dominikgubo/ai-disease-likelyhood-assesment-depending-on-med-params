import os
from typing import List, Dict
import pandas as pd

from config import OUTPUT_DIR, ICD_CSV_PATH, NHANES_CSV_PATH, USE_DISEASE_DESCRIPTION


def load_nhanes_features(nhanes_csv: str) -> List[Dict[str, str]]:
    df = pd.read_csv(nhanes_csv, dtype=str, on_bad_lines="skip").fillna("")
    features: List[Dict[str, str]] = []

    if "Variable name" in df.columns:
        for _, r in df.iterrows():
            code = (r.get("Variable name") or "").strip()
            analyte = (r.get("Analyte") or "").strip()
            units = (r.get("Units") or "").strip()
            if code:
                features.append({"code": code, "analyte": analyte, "units": units})

    if not features:
        raise ValueError("No NHANES features found in the provided CSV.")

    print(f"Loaded {len(features)} NHANES parameters, from: {NHANES_CSV_PATH}")

    return features

def load_icd(icd_csv: str):
    try:
        df = pd.read_csv(icd_csv, dtype=str, on_bad_lines="skip").fillna("")
    except Exception as e:
        raise ValueError(f"Error reading ICD CSV: {e}")

    required = {"code", "parent_code", "name"}
    required = {"code", "parent_code", "name","disease_description"} if USE_DISEASE_DESCRIPTION == True else required

    if not required.issubset(df.columns):
        raise ValueError(f"ICD CSV missing required columns: {required - set(df.columns)}")

    print(f"Loaded {len(df)} ICD entries, from: {ICD_CSV_PATH}")

    return df

def write_csv_result_file(file_name: str, row_list: list[str]):
    path = os.path.join(OUTPUT_DIR, file_name)
    pd.DataFrame(row_list).to_csv(path, index=False)
    print(f"✅ Wrote {len(row_list)} rows to: {path}")