import re
from typing import Tuple, Optional


_POSSIBILITY_PATTERNS = [
    re.compile(r"^\s*assessment\s+disease\s+likelihood\s*:\s*(possible|not\s*possible)\b", re.I | re.M),
    re.compile(r"^\s*(?:feasibility|screening)\s+(?:assessment)?\s*:\s*(possible|not\s*possible)\b", re.I | re.M),
]

_EXPLANATION_PATTERNS = [
    re.compile(r"explanation\s+of\s+assessment\s+possibility\s*:\s*(.+)$", re.I | re.S),
    re.compile(r"explanation\s*:\s*(.+)$", re.I | re.S),
    re.compile(r"rationale\s*:\s*(.+)$", re.I | re.S),
]

def parse_model_output(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None

    norm = text.replace("\u00A0", " ")

    # Possibility response section parsing
    possibility = None
    for pattern in _POSSIBILITY_PATTERNS:
        m = pattern.search(norm)
        if m:
            v = m.group(1).strip().lower().replace(" ", "")
            possibility = "Not Possible" if v.startswith("not") else "Possible"
            break

    # Explanation response section parsing
    medical_reasoning = None
    for pattern in _EXPLANATION_PATTERNS:
        m = pattern.search(norm)
        if m:
            medical_reasoning = re.sub(r"\s+", " ", m.group(1).strip())
            break

    if possibility is not None and not medical_reasoning:
        medical_reasoning = re.sub(r"\s+", " ", norm).strip()

    return possibility, medical_reasoning