from datetime import timedelta

# notification lifecycle per category — all values are rule-based, not LLM-decided
CATEGORY_RULES: dict[str, dict] = {
    "Travel":        {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "Health":        {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "Study":         {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "Work":          {"retry": True,  "retry_interval_minutes": 20,  "expires": False, "expires_delta": None},
    "Finance":       {"retry": True,  "retry_interval_minutes": 120, "expires": True,  "expires_delta": timedelta(hours=12)},
    "Entertainment": {"retry": True,  "retry_interval_minutes": 60,  "expires": True,  "expires_delta": timedelta(hours=2)},
    "Social":        {"retry": True,  "retry_interval_minutes": 60,  "expires": True,  "expires_delta": timedelta(hours=48)},
    "Home":          {"retry": False, "retry_interval_minutes": 0,   "expires": False, "expires_delta": None},
    "Personal":      {"retry": False, "retry_interval_minutes": 0,   "expires": False, "expires_delta": None},
}

DEFAULT_RULES = {"retry": False, "retry_interval_minutes": 0, "expires": False, "expires_delta": None}


def get_rules(category: str) -> dict:
    return CATEGORY_RULES.get(category, DEFAULT_RULES)
