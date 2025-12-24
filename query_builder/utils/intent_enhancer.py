from datetime import datetime
from query_builder.utils.date_literals import resolve_date_literal
from query_builder.utils.schema_extractor import extract_doctype_schema


# ---------------------------------------------------------------------
# FILTER RESOLUTION (DATE + TYPE SAFE)
# ---------------------------------------------------------------------

def resolve_filters(intent):
    resolved = []

    doctype = intent.get("doctype")
    schema = extract_doctype_schema(doctype) if doctype else None

    field_type_map = {}
    if schema:
        field_type_map = {
            f["fieldname"]: f["type"]
            for f in schema.get("fields", [])
        }

    for f in intent.get("filters", []):

        if not isinstance(f, dict):
            resolved.append(f)
            continue

        field = f.get("field")
        op = f.get("op")
        value = f.get("value")

        # ---------------- Date literals ----------------
        if isinstance(value, str):
            literal = resolve_date_literal(value)
            if literal:
                op = literal[0]
                value = literal[1:]

        # ---------------- Type coercion ----------------
        if op == "between" and field in field_type_map:
            if field_type_map[field] == "Date" and isinstance(value, list):
                start, end = value
                if isinstance(start, datetime):
                    start = start.date()
                if isinstance(end, datetime):
                    end = end.date()
                value = [start, end]

        resolved.append({"field": field, "op": op, "value": value})

    intent["filters"] = resolved
    return intent


# ---------------------------------------------------------------------
# AGGREGATE NORMALIZATION
# ---------------------------------------------------------------------

def normalize_aggregate(intent):
    if intent.get("action") != "aggregate":
        return intent

    if not intent.get("aggregate"):
        intent["aggregate"] = {
            "function": "count",
            "field": "name",
        }

    return intent


# ---------------------------------------------------------------------
# GROUP BY NORMALIZATION (NEW)
# ---------------------------------------------------------------------

def normalize_group_by(intent):
    if intent.get("action") != "aggregate":
        intent["group_by"] = []
        return intent

    gb = intent.get("group_by") or []
    intent["group_by"] = [g for g in gb if isinstance(g, str)]
    return intent


# ---------------------------------------------------------------------
# FILTER CANONICALIZATION
# ---------------------------------------------------------------------

def canonicalize_filters(intent):
    canonical = []

    for f in intent.get("filters", []):
        if isinstance(f, dict):
            canonical.append(f)
        elif isinstance(f, (list, tuple)) and len(f) == 3:
            canonical.append({"field": f[0], "op": f[1], "value": f[2]})

    intent["filters"] = canonical
    return intent


# ---------------------------------------------------------------------
# ACTION NORMALIZATION
# ---------------------------------------------------------------------

def normalize_action(intent):
    action_map = {
        "search": "list",
        "find": "list",
        "show": "list",
        "lookup": "single",
        "get": "single",
        "fetch": "single",
        "count": "aggregate",
        "sum": "aggregate",
        "average": "aggregate",
        "avg": "aggregate",
    }

    if intent.get("action") in action_map:
        intent["action"] = action_map[intent["action"]]

    return intent


# ---------------------------------------------------------------------
# OPERATOR NORMALIZATION
# ---------------------------------------------------------------------

def normalize_operators(intent):
    op_map = {
        "like": "=",
        "equals": "=",
        "is": "=",
        "contains": "=",
        "matches": "=",
        "not like": "!=",
    }

    for f in intent.get("filters", []):
        if isinstance(f, dict) and f.get("op") in op_map:
            f["op"] = op_map[f["op"]]

    return intent
