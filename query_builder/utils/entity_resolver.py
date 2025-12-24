# query_builder/utils/entity_resolver.py

import re
import frappe


EMPLOYEE_NAME_PATTERN = re.compile(
    r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b"
)


def resolve_entities(query: str) -> dict:
    """
    Resolve employee names before LLM call.
    """
    candidates = EMPLOYEE_NAME_PATTERN.findall(query)

    for name in candidates:
        matches = frappe.get_all(
            "Employee",
            filters={"employee_name": ["like", f"%{name}%"]},
            fields=["name", "employee_name"],
        )

        if len(matches) > 1:
            return {
                "clarification_required": True,
                "entity": "Employee",
                "matches": matches,
            }

        if len(matches) == 1:
            query = query.replace(name, matches[0]["name"])

    return {"query": query}
