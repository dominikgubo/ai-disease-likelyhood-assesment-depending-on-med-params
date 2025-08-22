import os

# -- Pathing and inner script functionality --
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NHANES_CSV = os.path.join(SCRIPT_DIR, "nhanes_variables.csv")
ICD_CSV = os.path.join(SCRIPT_DIR, "icd_codes.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "out")
# DISEASE_SCOPE_LIMIT if value is present processes first variable value number of ICD diseases
# e.g. DISEASE_SCOPE_LIMIT = 20 would process first 20 ICD diseases in the .csv input file
DISEASE_SCOPE_LIMIT = None
# API_KEY used for accessing OpenAI APi, is stored within system environment variables by default
# if needed this logic can be changed depending on the need, e.g. fetch key from the external service
API_KEY = os.environ.get("OPENAI_API_KEY")


# -- OPEN AI CHAT API specifics --
OPENAI_MODEL = "gpt-4o-mini"
# Temperature controls randomness and creativity of model responses from 0-2;
# 0 - being most deterministic and factual
RESPONSE_TEMPERATURE = 0.0
# Max Tokens represent the maximum amount of tokens used in the output response
# where 300 tokens would suggest approximately 1200 characters upper response limit
MAX_TOKENS = 300
# System Prompt sets behavior, personality and most importantly rules for the model
# TODO; refine this query further on to be more strict
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
    "Assessment disease likelihood: Possible|Not Possible\n"
    "Explanation of assessment possibility: <concise medical reasoning>\n"
)
# User Prompt template is used for appending the specified data, it defines a prompt coming from the user
# TODO; add disease description mapping and remove unnecessary data as e.g. ICD code or parent code
USER_PROMPT_TEMPLATE = (
    "ICD code: {code}\n"
    "ICD parent code: {parent_code}\n"
    "Disease name: {name}\n\n"
    "AVAILABLE NHANES FEATURES (no patient values):\n"
    "{features_json}\n\n"
    "Decide feasibility strictly based on the features above (names and units only)."
)