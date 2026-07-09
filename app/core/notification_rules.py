from datetime import timedelta

# notification lifecycle per category — controls retry on/off and expiry windows
CATEGORY_RULES: dict[str, dict] = {
    "travel":        {"retry": True,  "expires": False, "expires_delta": None},
    "health":        {"retry": True,  "expires": False, "expires_delta": None},
    "learning":      {"retry": True,  "expires": False, "expires_delta": None},
    "work":          {"retry": True,  "expires": False, "expires_delta": None},
    "financial":     {"retry": True,  "expires": True,  "expires_delta": timedelta(hours=12)},
    "entertainment": {"retry": True,  "expires": True,  "expires_delta": timedelta(hours=2)},
    "social":        {"retry": True,  "expires": True,  "expires_delta": timedelta(hours=48)},
    "home":          {"retry": False, "expires": False, "expires_delta": None},
    "shopping":      {"retry": False, "expires": False, "expires_delta": None},
}

DEFAULT_RULES = {"retry": False, "expires": False, "expires_delta": None}

# Priority controls how often retries fire
PRIORITY_INTERVAL: dict[str, int] = {
    "high":   10,
    "medium": 15,
    "low":    20,
}


def get_rules(category: str, priority: str = "medium") -> dict:
    base = dict(CATEGORY_RULES.get(category, DEFAULT_RULES))
    interval = PRIORITY_INTERVAL.get(priority, 15) if base["retry"] else 0
    return {
        "retry": base["retry"],
        "retry_interval_minutes": interval,
        "expires": base["expires"],
        "expires_delta": base["expires_delta"],
    }
