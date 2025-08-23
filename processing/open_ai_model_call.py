import time

from processing.response_parser import parse_model_output

try:
    from openai import OpenAI
except Exception:
    raise


def query_llm_model(client: OpenAI, model: str, system_prompt: str, user_prompt: str,
                    temperature: float = 0.0, max_tokens: int = 300) -> str:
    max_retries = 5
    backoff = 1.5
    delay = 0.6
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                # TODO; investigate addition of some parameters e.g.reasoning_effort, top_p (over temperature), web_search_options (model specific)
                # param full list - https://platform.openai.com/docs/api-reference/chat/create
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

def api_refactor_of_invalid_format_on_retry(model_text: str, client: OpenAI, openai_model: str):
    print("   ⚠ Output not in expected format. Attempting to reformat...")
    repair_prompt = (
        "Reformat the text below to exactly match:\n"
        "Assessment disease likelihood: Possible|Not Possible\n"
        "Explanation of assessment possibility: <text>\n\n"
        f"TEXT:\n{model_text}"
    )
    repair_text = query_llm_model(client, openai_model, "You strictly format text.", repair_prompt, 0.0, 200)
    possibility, medical_reasoning = parse_model_output(repair_text)
    if possibility is None or medical_reasoning is None:
        print("   ❌ Still unparseable. Marking as 'Not Possible'.")
        possibility = "Not Possible"
        medical_reasoning = f"Unparseable output. Raw: {model_text[:300]}"
    return possibility, medical_reasoning