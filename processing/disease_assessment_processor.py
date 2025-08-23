import json
import sys
from typing import List, Dict

from openai import OpenAI
from pandas import DataFrame

from config import *
from processing.open_ai_model_call import query_llm_model, api_refactor_of_invalid_format_on_retry
from processing.response_parser import parse_model_output

def fetch_disease_possibility_and_reasoning_values(client: OpenAI, user_prompt: str):
    model_response = query_llm_model(client, OPENAI_MODEL, SYSTEM_PROMPT, user_prompt, RESPONSE_TEMPERATURE, MAX_TOKENS)
    print("   🩺 GPT raw output:")
    print(model_response.strip(), "\n")

    possibility, medical_reasoning = parse_model_output(model_response)
    print(f"   ↳ Parsed possibility: {possibility}")

    # Retry-refactoring logic using query to the OpenAI API for refactoring
    if possibility is None or medical_reasoning is None:
        possibility, medical_reasoning = api_refactor_of_invalid_format_on_retry(
            model_response, client, OPENAI_MODEL
        )

    return possibility, medical_reasoning


def append_all_disease_assessment_status(icd_dataframe: DataFrame, nhanes_features: list[dict[str, str]],
                 all_rows: List[Dict[str, str]], possible_rows: List[Dict[str, str]], not_possible_rows: List[Dict[str, str]]):
    if not API_KEY:
        print("❌ Please set OPENAI_API_KEY in your environment.", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=API_KEY)

    medical_parameters_json = json.dumps(nhanes_features, ensure_ascii=False, indent=2)

    print("\n🚀 Starting disease feasibility assessment based on AVAILABLE FEATURES only...\n")
    for idx, (_, row) in enumerate(icd_dataframe.iterrows(), start=1):
        code = (row["code"]).strip()
        parent_code = (row["parent_code"]).strip()
        name = (row["name"]).strip()
    
        print(f"[{idx}/{len(icd_dataframe)}] Assessing ICD {code} — {name} ...")
    
        user_prompt = USER_PROMPT_TEMPLATE.format(
            code=code, parent_code=parent_code, name=name, features_json=medical_parameters_json
        )
    
        try:
            possibility, medical_reasoning = fetch_disease_possibility_and_reasoning_values(client, user_prompt)
    
        except Exception as e:
            print(f"   ❌ API error: {e}")
            possibility, medical_reasoning = "Not Possible", f"API error: {e}"
    
        common_columns = {"code": code, "parent_code": parent_code, "name": name, "medical_reasoning": medical_reasoning}
        all_rows.append({**common_columns, "possibility": possibility})
        if possibility == "Possible":
            possible_rows.append(common_columns)
        else:
            not_possible_rows.append(common_columns)