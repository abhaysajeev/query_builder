# query_builder/utils/normalizer.py

TEMPORAL_KEYWORDS = {
    "today", "yesterday", "last", "this", "current", "date", "shift"
}

PROFILE_FIELDS = {
    "department",
    "designation",
    "company",
    "reports_to",
    "employee_name",
}

MANDATORY_FILTERS = {
    "Employee": [
        {"field": "status", "op": "=", "value": "Active"}
    ],
    "Attendance": [
        {"field": "docstatus", "op": "=", "value": 1}
    ],
    "Leave Application": [
        {"field": "docstatus", "op": "=", "value": 1}
    ],
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def has_temporal_context(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in TEMPORAL_KEYWORDS)


# ---------------------------------------------------------------------
# RULES
# ---------------------------------------------------------------------

def rule_normalize_action(intent):
    action_map = {
        "read": "list",
        "select": "single",
        "count": "aggregate",
        "sum": "aggregate",
    }
    intent["action"] = action_map.get(intent["action"], intent["action"])
    return intent


def rule_prefer_employee_master(intent, query):
    if intent.get("doctype") == "Employee":
        return intent

    fields = intent.get("fields", [])

    def is_profile_field(f):
        base = f.split(".")[0]
        return base in PROFILE_FIELDS

    if (
        any(is_profile_field(f) for f in fields)
        and not has_temporal_context(query)
    ):
        intent["doctype"] = "Employee"
        intent["joins"] = []
        # normalize fields to base field
        intent["fields"] = [f.split(".")[0] for f in fields]

    return intent



def rule_normalize_filters(intent):
    raw = intent.get("filters", {})
    normalized = []

    for field, value in raw.items():
        if isinstance(value, list):
            normalized.append({"field": field, "op": "in", "value": value})
        else:
            normalized.append({"field": field, "op": "=", "value": value})

    intent["filters"] = normalized
    return intent


def rule_add_mandatory_filters(intent):
    intent.setdefault("filters", [])
    required = MANDATORY_FILTERS.get(intent["doctype"], [])

    for f in required:
        if not any(x["field"] == f["field"] for x in intent["filters"]):
            intent["filters"].append(f)

    return intent


def rule_clean_joins(intent):
    """
    Remove joins if not required by selected fields
    """
    required_joins = []
    for j in intent.get("joins", []):
        if any(f.startswith(j.get("field", "") + ".") for f in intent["fields"]):
            required_joins.append(j)

    intent["joins"] = required_joins
    return intent


# ---------------------------------------------------------------------
# RULE REGISTRY (ORDER MATTERS)
# ---------------------------------------------------------------------

NORMALIZATION_RULES = [
    rule_normalize_action,
    rule_prefer_employee_master,
    rule_normalize_filters,
    rule_add_mandatory_filters,
    rule_clean_joins,
]


# ---------------------------------------------------------------------
# NORMALIZATION ENGINE
# ---------------------------------------------------------------------

class IntentNormalizer:
    def normalize(self, intent: dict, query: str) -> dict:
        for rule in NORMALIZATION_RULES:
            try:
                if rule.__code__.co_argcount == 2:
                    intent = rule(intent, query)
                else:
                    intent = rule(intent)
            except Exception:
                # normalization must NEVER break execution
                continue
        return intent
