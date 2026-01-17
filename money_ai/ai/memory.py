import json
import os
import re
from typing import Optional, Dict, Any

BASE_DIR = os.path.dirname(__file__)
MEMORY_PATH = os.path.join(BASE_DIR, "memory.json")
SUGGESTIONS_PATH = os.path.join(BASE_DIR, "suggestions.json")

def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.upper()
    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== Memoria global (aprobada) =====
def get_memory_category(description: str) -> Optional[str]:
    mem = _load(MEMORY_PATH)
    key = normalize(description)
    return mem.get(key)

def set_memory_category(description: str, category: str) -> None:
    mem = _load(MEMORY_PATH)
    key = normalize(description)
    mem[key] = category
    _save(MEMORY_PATH, mem)

# ===== Sugerencias (pendientes) =====
def add_suggestion(description: str, category: str, user_tag: str = "beta") -> None:
    sug = _load(SUGGESTIONS_PATH)
    key = normalize(description)

    if key not in sug:
        sug[key] = {"description": description, "votes": {}, "last_user_tag": user_tag}

    votes = sug[key]["votes"]
    votes[category] = votes.get(category, 0) + 1
    sug[key]["last_user_tag"] = user_tag

    _save(SUGGESTIONS_PATH, sug)

def list_suggestions() -> Dict[str, Any]:
    return _load(SUGGESTIONS_PATH)

def approve_suggestion(description: str, category: str) -> str:
    key = normalize(description)

    mem = _load(MEMORY_PATH)
    mem[key] = category
    _save(MEMORY_PATH, mem)

    sug = _load(SUGGESTIONS_PATH)
    if key in sug:
        del sug[key]
        _save(SUGGESTIONS_PATH, sug)

    return key

