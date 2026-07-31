import os, json, requests, time
from typing import Optional

OMNIROUTE_BASE = os.environ.get("OMNIROUTE_BASE", "http://localhost:20128/v1")
OMNIROUTE_KEY = os.environ.get("OMNIROUTE_API_KEY", "")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "omniroute_config.json")

TIERS = {
    "cheap":    {"priority": 0, "label": "Fast & cheap"},
    "balanced": {"priority": 1, "label": "Balanced"},
    "quality":  {"priority": 2, "label": "Best quality"},
}

DEFAULT_TIER = "cheap"

def _load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            return json.load(open(CONFIG_PATH))
    except: pass
    return {"tier": DEFAULT_TIER, "model": "auto"}

def _save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    json.dump(cfg, open(CONFIG_PATH, "w"), indent=2)

def set_key(key):
    global OMNIROUTE_KEY
    OMNIROUTE_KEY = key
    os.environ["OMNIROUTE_API_KEY"] = key
    cfg = _load_config()
    cfg["api_key"] = key
    _save_config(cfg)

def _load_key():
    cfg = _load_config()
    key = cfg.get("api_key", "") or os.environ.get("OMNIROUTE_API_KEY", "")
    if key:
        global OMNIROUTE_KEY
        OMNIROUTE_KEY = key
    return key

_load_key()

def set_tier(tier):
    if tier in TIERS:
        cfg = _load_config()
        cfg["tier"] = tier
        _save_config(cfg)
        return True
    return False

def is_available():
    return bool(OMNIROUTE_KEY)

def chat(messages, model=None, max_tokens=2048, temperature=0.7):
    if not OMNIROUTE_KEY:
        return None
    cfg = _load_config()
    payload = {
        "model": model or cfg.get("model", "auto"),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    try:
        resp = requests.post(
            f"{OMNIROUTE_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {OMNIROUTE_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return {
            "text": data["choices"][0]["message"]["content"],
            "model": data.get("model", model or "auto"),
            "cost": (usage.get("prompt_tokens", 0) * 0.00015 + usage.get("completion_tokens", 0) * 0.0006),
        }
    except Exception as e:
        print(f"[OmniRoute] Error: {e}")
        return {"text": f"[OmniRoute Error: {e}]", "model": "error", "cost": 0}
