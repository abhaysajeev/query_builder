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
    normalize_operators
)

from query_builder.utils.confidence import require_clarification


@frappe.whitelist()
def extract_intent(query: str):
    res = retrieve_schema(query)
    trimmed_schema = trim_schema(res, query)

    schema_text = build_schema_prompt(trimmed_schema)


    raw = parse_intent(schema_text, query)



    # Preserve metadata before validation
    meta = raw.get("_meta")

    normalizer = IntentNormalizer()
    intent = normalizer.normalize(raw, query)

    clarification = require_clarification(intent)
    if clarification:
        return clarification
    intent = normalize_action(intent)  
    intent = canonicalize_filters(intent) 
    intent = normalize_operators(intent) 
    intent = resolve_filters(intent)
    intent = normalize_aggregate(intent)

    try:
        validated = IntentSchema(**intent).dict()
    except ValidationError as e:
        frappe.throw(f"Invalid intent structure: {e}")

    # Reattach metadata
    if meta:
        validated["_meta"] = meta

    return validated
