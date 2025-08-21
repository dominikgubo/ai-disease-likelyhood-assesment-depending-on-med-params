import csv
import json
import os
import sys
import time
import re
from typing import Dict, Tuple, Optional, List
import pandas as pd

try:
    from openai import OpenAI
except Exception:
    raise

SYSTEM_PROMPT = (
    "You are ChatGPT, a board-certified hematology consultant and senior data scientist.\n"
    "You will be given:\n"
    "  • An ICD code and disease name.\n"
    "  • A list of AVAILABLE NHANES FEATURES (measurement names only; NO patient values).\n\n"
    "Your task: Decide whether a *screening/likelihood assessment is possible in principle* using ONLY the listed features.\n"
    "Interpret 'Possible' as: The available features include the key signals typically used to screen/triage or build a probabilistic model "
    "that meaningfully enriches disease prevalence beyond base rate (e.g., a reasonable sensitivity/specificity profile could be achieved). "
    "You do NOT need pathognomonic confirmatory tests; screening suffices. If essential signals are missing (e.g., imaging, genetics, ADAMTS13), "
    "respond 'Not Possible'. Do not assume access to any feature not listed.\n\n"
    "Be strict and evidence-based (hematology PhD level). Cite which features support feasibility vs. which missing features preclude it.\n\n"
    "Output MUST follow this exact two-line format (spelling included):\n"
    "Assesment disease likelyhood: Possible|Not Possible\n"
    "Explanation of assesment possibility: <concise medical reasoning>\n"
)

USER_PROMPT_TEMPLATE = (
    "ICD code: {code}\n"
    "ICD parent code: {parent_code}\n"
    "Disease name: {name}\n\n"
    "AVAILABLE NHANES FEATURES (no patient values):\n"
    "{features_json}\n\n"
    "Decide feasibility strictly based on the features above (names and units only)."
)

POSSIBILITY_RE = re.compile(
    r"Assesment\s+disease\s+likelyhood:\s*(Possible|Not\s+Possible)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
EXPLANATION_RE = re.compile(
    r"Explanation\s+of\s+assesment\s+possibility:\s*(.+)$",
    flags=re.IGNORECASE | re.DOTALL,
)

def parse_response(text: str) -> Tuple[Optional[str], Optional[str]]:
    poss_match = POSSIBILITY_RE.search(text or "")
    expl_match = EXPLANATION_RE.search(text or "")
    possibility = None
    if poss_match:
        raw = poss_match.group(1).strip()
        possibility = "Possible" if raw.lower().startswith("possible") else "Not Possible"
    medical_reasoning = None
    if expl_match:
        medical_reasoning = re.sub(r"\s+", " ", expl_match.group(1).strip())
    return possibility, medical_reasoning

_POSSIBILITY_PATTERNS = [
    re.compile(r"^\s*assessment\s+disease\s+likelihood\s*:\s*(possible|not\s*possible)\b", re.I | re.M),
    re.compile(r"^\s*assesment\s+disease\s+likelyhood\s*:\s*(possible|not\s*possible)\b", re.I | re.M),
    re.compile(r"^\s*(?:feasibility|screening)\s+(?:assessment)?\s*:\s*(possible|not\s*possible)\b", re.I | re.M),
]

_EXPLANATION_PATTERNS = [
    re.compile(r"explanation\s+of\s+assessment\s+possibility\s*:\s*(.+)$", re.I | re.S),
    re.compile(r"explanation\s+of\s+assesment\s+possibility\s*:\s*(.+)$", re.I | re.S),
    re.compile(r"explanation\s*:\s*(.+)$", re.I | re.S),
    re.compile(r"rationale\s*:\s*(.+)$", re.I | re.S),
]

def parse_model_output(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None

    norm = text.replace("\u00A0", " ")
    low = norm.lower().replace("assesment", "assessment").replace("likelyhood", "likelihood")

    # Possibility
    possibility = None
    for pat in _POSSIBILITY_PATTERNS:
        m = pat.search(low)
        if m:
            v = m.group(1).strip().lower().replace(" ", "")
            possibility = "Not Possible" if v.startswith("not") else "Possible"
            break

    # Explanation
    medical_reasoning = None
    for pat in _EXPLANATION_PATTERNS:
        m = pat.search(norm)
        if m:
            medical_reasoning = re.sub(r"\s+", " ", m.group(1).strip())
            break

    if possibility is not None and not medical_reasoning:
        medical_reasoning = re.sub(r"\s+", " ", norm).strip()

    return possibility, medical_reasoning

def call_model(client: OpenAI, model: str, system_prompt: str, user_prompt: str,
               temperature: float = 0.0, max_tokens: int = 300) -> str:
    max_retries = 5
    backoff = 1.5
    delay = 0.6
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content if resp and resp.choices else ""
            time.sleep(delay)
            return content or ""
        except Exception as e:
            last_err = e
            time.sleep((backoff ** (attempt - 1)) + (0.1 * attempt))
    raise RuntimeError(f"Model call failed after {max_retries} attempts: {last_err}")

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
    else:
        for c in df.columns:
            code = (c or "").strip()
            if code:
                features.append({"code": code, "analyte": "", "units": ""})

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

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    NHANES_CSV = os.path.join(script_dir, "nhanes_variables.csv")
    ICD_CSV = os.path.join(script_dir, "icd_codes.csv")
    OUTPUT_DIR = os.path.join(script_dir, "out")

    MODEL = "gpt-4o-mini"
    TEMPERATURE = 0.0
    MAX_TOKENS = 300
    LIMIT = None

    print("🔍 Starting NHANES-informed ICD Likelihood Assessor (feature-availability mode)...")
    print(f"Loading NHANES feature catalog from: {NHANES_CSV}")
    nhanes_features = load_nhanes_features(NHANES_CSV)
    print(f"Loaded {len(nhanes_features)} available NHANES features.")

    print(f"Loading ICD codes from: {ICD_CSV}")
    icd_df = load_icd(ICD_CSV)
    print(f"Loaded {len(icd_df)} ICD entries.")
    if LIMIT is not None:
        icd_df = icd_df.head(LIMIT)
        print(f"⚠ Limiting processing to first {LIMIT} ICD entries.")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY in your environment.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    all_rows, possible_rows, not_possible_rows = [], [], []
    features_json = json.dumps(nhanes_features, ensure_ascii=False, indent=2)

    print("\n🚀 Starting disease feasibility assessment based on AVAILABLE FEATURES only...\n")
    for idx, (_, row) in enumerate(icd_df.iterrows(), start=1):
        code = (row["code"] or "").strip()
        parent_code = (row["parent_code"] or "").strip()
        name = (row["name"] or "").strip()

        print(f"[{idx}/{len(icd_df)}] Assessing ICD {code} — {name} ...")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            code=code, parent_code=parent_code, name=name, features_json=features_json
        )

        try:
            model_text = call_model(client, MODEL, SYSTEM_PROMPT, user_prompt, TEMPERATURE, MAX_TOKENS)

            print("   🩺 GPT raw output:")
            print(model_text.strip(), "\n")

            possibility, medical_reasoning = parse_model_output(model_text)
            print(f"   ↳ Parsed possibility: {possibility}")

            if possibility is None or medical_reasoning is None:
                print("   ⚠ Output not in expected format. Attempting to reformat...")
                repair_prompt = (
                    "Reformat the text below to exactly match:\n"
                    "Assesment disease likelyhood: Possible|Not Possible\n"
                    "Explanation of assesment possibility: <text>\n\n"
                    f"TEXT:\n{model_text}"
                )
                repair_text = call_model(client, MODEL, "You strictly format text.", repair_prompt, 0.0, 200)
                possibility, medical_reasoning = parse_model_output(repair_text)
                if possibility is None or medical_reasoning is None:
                    print("   ❌ Still unparseable. Marking as 'Not Possible'.")
                    possibility = "Not Possible"
                    medical_reasoning = f"Unparseable output. Raw: {model_text[:300]}"

        except Exception as e:
            print(f"   ❌ API error: {e}")
            possibility, medical_reasoning = "Not Possible", f"API error: {e}"

        all_rows.append({
            "code": code,
            "parent_code": parent_code,
            "name": name,
            "possibility": possibility,
            "medical_reasoning": medical_reasoning
        })

        if possibility == "Possible":
            possible_rows.append({
                "code": code,
                "parent_code": parent_code,
                "name": name,
                "medical_reasoning": medical_reasoning
            })
        elif possibility == "Not Possible":
            not_possible_rows.append({
                "code": code,
                "parent_code": parent_code,
                "name": name,
                "medical_reasoning": medical_reasoning
            })

    print("\n💾 Saving results...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_path = os.path.join(OUTPUT_DIR, "results_all.csv")
    poss_path = os.path.join(OUTPUT_DIR, "results_possible.csv")
    not_poss_path = os.path.join(OUTPUT_DIR, "results_not_possible.csv")

    with open(all_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "parent_code", "name", "possibility", "medical_reasoning"])
        writer.writeheader()
        writer.writerows(all_rows)

    with open(poss_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "parent_code", "name", "medical_reasoning"])
        writer.writeheader()
        writer.writerows(possible_rows)

    with open(not_poss_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "parent_code", "name", "medical_reasoning"])
        writer.writeheader()
        writer.writerows(not_possible_rows)

    print(f"✅ Wrote {len(all_rows)} rows to: {all_path}")
    print(f"✅ Wrote {len(possible_rows)} 'Possible' rows to: {poss_path}")
    print(f"✅ Wrote {len(not_possible_rows)} 'Not Possible' rows to: {not_poss_path}")
    print("\n🎯 Assessment completed.")
