from typing import List, Dict

from query_builder.utils.normalizer import has_temporal_context
from query_builder.utils.schema_extractor import extract_doctype_schema


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

MAX_FIELDS_PER_DOCTYPE = 12  # soft cap, guards still bypass this

IDENTITY_FIELDS = {
    "name",
    "employee",
    "employee_name",
}

ALWAYS_KEEP_FIELDNAMES = {
    "name",
    "docstatus",
    "status",
}


# ---------------------------------------------------------------------
# QUERY HINTS
# ---------------------------------------------------------------------

def extract_query_hints(query: str) -> Dict[str, bool]:
    q = query.lower()
    return {
        "wants_count": any(x in q for x in ("count", "how many", "number of")),
        "has_temporal": has_temporal_context(query),
        "mentions_active": "active" in q or "inactive" in q,
    }


# ---------------------------------------------------------------------
# FIELD GUARDS (CRITICAL)
# ---------------------------------------------------------------------

def is_always_keep(field: dict, hints: dict) -> bool:
    fname = field["fieldname"]

    # Identity fields must never be trimmed
    if fname in IDENTITY_FIELDS:
        return True

    # Core structural fields
    if fname in ALWAYS_KEEP_FIELDNAMES:
        return True

    # Common filters (status, department, etc.)
    if field.get("commonly_filtered"):
        return True

    # Temporal queries → keep ALL temporal fields
    if hints["has_temporal"] and field["class"] == "temporal":
        return True

    # Aggregates → always keep identifier
    if hints["wants_count"] and fname == "name":
        return True

    return False


# ---------------------------------------------------------------------
# FIELD SCORING (ORDER MATTERS)
# ---------------------------------------------------------------------

def score_field(field: dict, hints: dict) -> int:
    score = 0

    # Strong preference for identity semantics
    if field["fieldname"] == "employee_name":
        score += 10
    elif field["fieldname"] == "first_name":
        score += 3

    if field.get("commonly_filtered"):
        score += 6

    if field["class"] == "temporal" and hints["has_temporal"]:
        score += 5

    if field["class"] == "numeric" and hints["wants_count"]:
        score += 4

    if field["class"] == "reference":
        score += 3

    if field["class"] == "text":
        score += 1

    return score


# ---------------------------------------------------------------------
# CORE TRIMMER
# ---------------------------------------------------------------------

def trim_schema(chroma_result: dict, query: str) -> List[dict]:
    metadatas = chroma_result.get("metadatas", [[]])[0]
    hints = extract_query_hints(query)

    trimmed_schemas = []

    for meta in metadatas:
        schema = extract_doctype_schema(meta["doctype"])
        if not schema:
            continue

        fields = schema["fields"]

        always_keep = []
        candidates = []

        for f in fields:
            if is_always_keep(f, hints):
                always_keep.append(f)
            else:
                candidates.append(f)

        candidates.sort(
            key=lambda f: score_field(f, hints),
            reverse=True,
        )

        remaining_slots = max(
            0,
            MAX_FIELDS_PER_DOCTYPE - len(always_keep)
        )

        selected = candidates[:remaining_slots]
        final_fields = always_keep + selected

        trimmed_schemas.append({
            "doctype": schema["doctype"],
            "description": schema["description"],
            "is_submittable": schema["is_submittable"],
            "fields": final_fields,
        })

    return trimmed_schemas


# ---------------------------------------------------------------------
# PROMPT BUILDER (ENUM-SAFE)
# ---------------------------------------------------------------------

def build_schema_prompt(trimmed_schemas: List[dict]) -> str:
    blocks = []

    for schema in trimmed_schemas:
        lines = [
            f"DocType: {schema['doctype']}",
            f"Description: {schema['description']}",
            "Fields:",
        ]

        for f in schema["fields"]:
            line = f"- {f['fieldname']} ({f['type']}, {f['class']})"

            # 🔑 ENUM PRESERVATION (FIXES status=Open bug)
            if f["type"] == "Select" and f.get("options"):
                line += f" → {f['options']}"

            lines.append(line)

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)
