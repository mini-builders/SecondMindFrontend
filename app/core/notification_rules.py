from datetime import timedelta

# notification lifecycle per category — all values are rule-based, not LLM-decided
CATEGORY_RULES: dict[str, dict] = {
    "travel":        {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "health":        {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "learning":      {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "work":          {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "financial":     {"retry": True,  "retry_interval_minutes": 120, "expires": True,  "expires_delta": timedelta(hours=12)},
    "entertainment": {"retry": True,  "retry_interval_minutes": 60,  "expires": True,  "expires_delta": timedelta(hours=2)},
    "social":        {"retry": True,  "retry_interval_minutes": 60,  "expires": True,  "expires_delta": timedelta(hours=48)},
    "home":          {"retry": False, "retry_interval_minutes": 0,   "expires": False, "expires_delta": None},
    "shopping":      {"retry": False, "retry_interval_minutes": 0,   "expires": False, "expires_delta": None},
}

DEFAULT_RULES = {"retry": False, "retry_interval_minutes": 0, "expires": False, "expires_delta": None}


def get_rules(category: str) -> dict:
    return CATEGORY_RULES.get(category, DEFAULT_RULES)
