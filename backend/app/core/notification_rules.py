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

# Severity controls how many times and how often retries fire (per PRD)
SEVERITY_CONFIG: dict[str, dict] = {
    "high":   {"max_fires": 5, "retry_interval_minutes": 15},
    "medium": {"max_fires": 3, "retry_interval_minutes": 30},
    "low":    {"max_fires": 1, "retry_interval_minutes": 0},
}


def get_rules(category: str, severity: str = "medium") -> dict:
    base = dict(CATEGORY_RULES.get(category, DEFAULT_RULES))
    sev = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["medium"])

    # Low severity never retries regardless of category
    should_retry = base["retry"] and sev["max_fires"] > 1
    interval = sev["retry_interval_minutes"] if should_retry else 0

    return {
        "retry": should_retry,
        "retry_interval_minutes": interval,
        "max_fires": sev["max_fires"],
        "expires": base["expires"],
        "expires_delta": base["expires_delta"],
    }
