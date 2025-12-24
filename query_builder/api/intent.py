import frappe
from pydantic import ValidationError

from query_builder.utils.vector_store import retrieve_schema
from query_builder.utils.intent_parser import parse_intent
from query_builder.utils.normalizer import IntentNormalizer
from query_builder.utils.intent_schema import IntentSchema
from query_builder.utils.schema_trimmer import trim_schema, build_schema_prompt

from query_builder.utils.intent_enhancer import (
    normalize_action,
    canonicalize_filters,
    resolve_filters,
    normalize_aggregate,
    normalize_operators,
    normalize_group_by,
)

from query_builder.utils.confidence import require_clarification

# ---------- LOGIC LAYERS ----------
from query_builder.utils.entity_resolver import resolve_entities
from query_builder.utils.join_graph import build_join_graph
from query_builder.utils.join_planner import build_joins
from query_builder.utils.child_table_resolver import resolve_child_table


@frappe.whitelist()
def extract_intent(query: str):

    original_query = query.lower()

    # --------------------------------------------------
    # STEP 0: ENTITY RESOLUTION (BLOCKING, PRE-LLM)
    # --------------------------------------------------
    entity_result = resolve_entities(query)
    if entity_result.get("clarification_required"):
        return entity_result

    rewritten_query = entity_result.get("query", query)

    # --------------------------------------------------
    # STEP 0.5: PRE-LLM CHECK-IN SEMANTIC HINT (NEW)
    # --------------------------------------------------
    # Helps schema retrieval + LLM pick correct doctype
    checkin_semantic = any(
        k in original_query
        for k in ["check in", "checked in", "check-in"]
    )

    # --------------------------------------------------
    # STEP 1: SCHEMA RETRIEVAL (VECTOR)
    # --------------------------------------------------
    res = retrieve_schema(rewritten_query)
    trimmed_schema = trim_schema(res, rewritten_query)
    schema_text = build_schema_prompt(trimmed_schema)

    # --------------------------------------------------
    # STEP 2: LLM INTENT EXTRACTION (WHAT)
    # --------------------------------------------------
    raw = parse_intent(schema_text, rewritten_query)
    meta = raw.get("_meta")

    # --------------------------------------------------
    # STEP 3: NORMALIZATION (SAFE, DETERMINISTIC)
    # --------------------------------------------------
    normalizer = IntentNormalizer()
    intent = normalizer.normalize(raw, rewritten_query)

    clarification = require_clarification(intent)
    if clarification:
        return clarification

    intent = normalize_action(intent)
    intent = canonicalize_filters(intent)
    intent = normalize_operators(intent)
    intent = resolve_filters(intent)
    intent = normalize_aggregate(intent)
    intent = normalize_group_by(intent)

    # --------------------------------------------------
    # STEP 3.5: POST-LLM CHECK-IN DOCTYPE ENFORCEMENT (NEW)
    # --------------------------------------------------
    if checkin_semantic:
        intent["doctype"] = "Employee Checkin"

    # --------------------------------------------------
    # STEP 4: HARD SAFETY GUARDS
    # --------------------------------------------------
    if intent.get("action") not in {"single", "list", "aggregate"}:
        frappe.throw("Unsupported action type")

    # Reset joins – rebuilt deterministically later
    intent["joins"] = []

    # --------------------------------------------------
    # STEP 4.5: AUTO ADD log_type = IN FOR CHECK-IN (NEW)
    # --------------------------------------------------
    if intent.get("doctype") == "Employee Checkin" and checkin_semantic:
        if not any(
            f.get("field") == "log_type"
            for f in intent.get("filters", [])
        ):
            intent["filters"].append({
                "field": "log_type",
                "op": "=",
                "value": "IN"
            })

    # --------------------------------------------------
    # STEP 5: JOIN + CHILD TABLE PLANNING (HOW)
    # --------------------------------------------------
    base_doctype = intent.get("doctype")
    required_doctypes = set()

    # ---- From filters ----
    for f in intent.get("filters", []):
        field = f.get("field")
        if not field:
            continue

        child = resolve_child_table(base_doctype, field)
        if child:
            required_doctypes.add(child)

    # ---- From aggregate ----
    agg = intent.get("aggregate")
    if agg:
        child = resolve_child_table(base_doctype, agg.get("field"))
        if child:
            required_doctypes.add(child)

    # ---- From group_by ----
    for gb in intent.get("group_by", []):
        child = resolve_child_table(base_doctype, gb)
        if child:
            required_doctypes.add(child)

    # ---- Build join graph ----
    all_doctypes = {base_doctype} | required_doctypes
    join_graph = build_join_graph(list(all_doctypes))

    join_result = build_joins(
        base_doctype=base_doctype,
        required_doctypes=required_doctypes,
        graph=join_graph,
    )

    if isinstance(join_result, dict) and join_result.get("clarification_required"):
        return join_result

    intent["joins"] = join_result

    # --------------------------------------------------
    # STEP 6: FINAL VALIDATION
    # --------------------------------------------------
    try:
        validated = IntentSchema(**intent).dict()
    except ValidationError as e:
        frappe.throw(f"Invalid intent structure: {e}")

    if meta:
        validated["_meta"] = meta

    return validated
