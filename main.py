from config import *
from processing.disease_assessment_processor import append_all_disease_assessment_status
from processing.io_file_processor import load_nhanes_features, load_icd, write_csv_result_file


if __name__ == "__main__":
    print("🔍 Starting NHANES-informed ICD Likelihood Assessor (feature-availability mode)...")

    nhanes_features = load_nhanes_features(NHANES_CSV_PATH)
    icd_df = load_icd(ICD_CSV_PATH)

    if DISEASE_SCOPE_LIMIT is not None:
        icd_df = icd_df.head(DISEASE_SCOPE_LIMIT)
        print(f"⚠ Limiting processing to first {DISEASE_SCOPE_LIMIT} ICD entries.")

    all_rows, possible_rows, not_possible_rows = [], [], []

    append_all_disease_assessment_status(icd_df, nhanes_features, all_rows, possible_rows, not_possible_rows)

    print("\n💾 Saving results...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    write_csv_result_file("results_all.csv", all_rows)
    write_csv_result_file("results_possible.csv", possible_rows)
    write_csv_result_file("results_not_possible.csv", not_possible_rows)

    print("\n🎯 Assessment completed.")