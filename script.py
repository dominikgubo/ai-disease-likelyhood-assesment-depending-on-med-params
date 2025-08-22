import json
import sys
import pandas as pd
from openai import OpenAI

from config import *
from input_data_loader import load_nhanes_features, load_icd
from open_ai_model_call import query_llm_model, api_refactor_of_invalid_format_on_retry
from response_parser import parse_model_output


if __name__ == "__main__":

    print("🔍 Starting NHANES-informed ICD Likelihood Assessor (feature-availability mode)...")
    print(f"Loading NHANES feature catalog from: {NHANES_CSV}")
    nhanes_features = load_nhanes_features(NHANES_CSV)
    print(f"Loaded {len(nhanes_features)} available NHANES features.")

    print(f"Loading ICD codes from: {ICD_CSV}")
    icd_df = load_icd(ICD_CSV)
    print(f"Loaded {len(icd_df)} ICD entries.")
    if DISEASE_SCOPE_LIMIT is not None:
        icd_df = icd_df.head(DISEASE_SCOPE_LIMIT)
        print(f"⚠ Limiting processing to first {DISEASE_SCOPE_LIMIT} ICD entries.")

    if not API_KEY:
        print("❌ Please set OPENAI_API_KEY in your environment.", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=API_KEY)

    all_rows, possible_rows, not_possible_rows = [], [], []
    features_json = json.dumps(nhanes_features, ensure_ascii=False, indent=2)

    print("\n🚀 Starting disease feasibility assessment based on AVAILABLE FEATURES only...\n")
    for idx, (_, row) in enumerate(icd_df.iterrows(), start=1):
        code = (row["code"]).strip()
        parent_code = (row["parent_code"]).strip()
        name = (row["name"]).strip()

        print(f"[{idx}/{len(icd_df)}] Assessing ICD {code} — {name} ...")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            code=code, parent_code=parent_code, name=name, features_json=features_json
        )

        try:
            model_text = query_llm_model(client, OPENAI_MODEL, SYSTEM_PROMPT, user_prompt, RESPONSE_TEMPERATURE, MAX_TOKENS)
            print("   🩺 GPT raw output:")
            print(model_text.strip(), "\n")

            possibility, medical_reasoning = parse_model_output(model_text)
            print(f"   ↳ Parsed possibility: {possibility}")

            # Retry-refactoring logic using query to the OpenAI API for refactoring
            if possibility is None or medical_reasoning is None:
                possibility, medical_reasoning = api_refactor_of_invalid_format_on_retry(
                    model_text, client, OPENAI_MODEL
                )

        except Exception as e:
            print(f"   ❌ API error: {e}")
            possibility, medical_reasoning = "Not Possible", f"API error: {e}"

        common_columns = {"code": code, "parent_code": parent_code, "name": name, "medical_reasoning": medical_reasoning}
        all_rows.append({**common_columns, "possibility": possibility})
        if possibility == "Possible":
            possible_rows.append(common_columns)
        else:
            not_possible_rows.append(common_columns)

    print("\n💾 Saving results...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_path = os.path.join(OUTPUT_DIR, "results_all.csv")
    possible_path = os.path.join(OUTPUT_DIR, "results_possible.csv")
    not_possible_path = os.path.join(OUTPUT_DIR, "results_not_possible.csv")
    # TODO; decide whether to remove saving output to 3 external files, instead of 1 - as easy to filter with base python
    pd.DataFrame(all_rows).to_csv(all_path, index=False)
    pd.DataFrame(possible_rows).to_csv(possible_path, index=False)
    pd.DataFrame(not_possible_rows).to_csv(not_possible_path, index=False)

    print(f"✅ Wrote {len(all_rows)} rows to: {all_path}")
    print(f"✅ Wrote {len(possible_rows)} 'Possible' rows to: {possible_path}")
    print(f"✅ Wrote {len(not_possible_rows)} 'Not Possible' rows to: {not_possible_path}")
    print("\n🎯 Assessment completed.")
