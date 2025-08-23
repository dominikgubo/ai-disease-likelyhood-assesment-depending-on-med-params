import os
from typing import List, Dict
import pandas as pd

from config import OUTPUT_DIR


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

    return features

def load_icd(icd_csv: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(icd_csv, dtype=str, on_bad_lines="skip").fillna("")
    except Exception as e:
        raise ValueError(f"Error reading ICD CSV: {e}")

    required = {"code", "parent_code", "name"}
    if not required.issubset(df.columns):
        raise ValueError(f"ICD CSV missing required columns: {required - set(df.columns)}")
    return df

def write_csv_result_file(file_name: str, row_list: list[str]):
    path = os.path.join(OUTPUT_DIR, file_name)
    pd.DataFrame(row_list).to_csv(path, index=False)
    print(f"✅ Wrote {len(row_list)} rows to: {path}")