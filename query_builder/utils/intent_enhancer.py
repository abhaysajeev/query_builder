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

        # Safety: skip invalid shapes
        if not isinstance(f, dict):
            resolved.append(f)
            continue

        field = f.get("field")
        op = f.get("op")
        value = f.get("value")

        # --------------------------------------------------
        # STEP 1: Resolve date literals (today, this_week)
        # --------------------------------------------------
        if isinstance(value, str):
            literal = resolve_date_literal(value)
            if literal:
                op = literal[0]
                value = literal[1:]

        # --------------------------------------------------
        # STEP 2: Coerce based on schema field type
        # --------------------------------------------------
        if op == "between" and field in field_type_map:
            field_type = field_type_map[field]

            if (
                field_type == "Date"
                and isinstance(value, list)
                and len(value) == 2
            ):
                start, end = value

                if isinstance(start, datetime):
                    start = start.date()
                if isinstance(end, datetime):
                    end = end.date()

                value = [start, end]

        resolved.append({
            "field": field,
            "op": op,
            "value": value
        })

    intent["filters"] = resolved
    return intent


# ---------------------------------------------------------------------
# AGGREGATE NORMALIZATION
# ---------------------------------------------------------------------

def normalize_aggregate(intent):
    """
    Ensure aggregate structure exists and is valid
    """
    if intent.get("action") != "aggregate":
        return intent

    # Default aggregate fallback
    if "aggregate" not in intent or not intent["aggregate"]:
        intent["aggregate"] = {
            "function": "count",
            "field": "name"
        }

    return intent


# ---------------------------------------------------------------------
# FILTER CANONICALIZATION
# ---------------------------------------------------------------------

def canonicalize_filters(intent):
    """
    Ensure all filters are dicts:
    {field, op, value}
    """
    canonical = []

    for f in intent.get("filters", []):

        # Already correct
        if isinstance(f, dict):
            canonical.append(f)
            continue

        # List / tuple form: [field, op, value]
        if isinstance(f, (list, tuple)) and len(f) == 3:
            canonical.append({
                "field": f[0],
                "op": f[1],
                "value": f[2],
            })
            continue

        # Unknown shape → drop safely
        continue

    intent["filters"] = canonical
    return intent


# ---------------------------------------------------------------------
# ACTION NORMALIZATION
# ---------------------------------------------------------------------

def normalize_action(intent):
    """
    Map LLM-style actions to canonical actions
    """
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

    action = intent.get("action")
    if action in action_map:
        intent["action"] = action_map[action]

    return intent


# ---------------------------------------------------------------------
# OPERATOR NORMALIZATION
# ---------------------------------------------------------------------

def normalize_operators(intent):
    """
    Normalize LLM-style operators to canonical operators
    """
    op_map = {
        "like": "=",
        "equals": "=",
        "is": "=",
        "contains": "=",
        "matches": "=",
        "not like": "!=",
    }

    normalized = []

    for f in intent.get("filters", []):
        if not isinstance(f, dict):
            normalized.append(f)
            continue

        op = f.get("op")
        if op in op_map:
            f["op"] = op_map[op]

        normalized.append(f)

    intent["filters"] = normalized
    return intent
