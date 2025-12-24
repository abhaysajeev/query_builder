# schema_extractor.py

import frappe

# =============================================================================
# FIELD FILTERING
# =============================================================================

def is_query_relevant_field(fieldname, fieldtype):
    system_fields = {
        "owner", "modified_by", "creation", "modified",
        "_user_tags", "_comments", "_assign", "_liked_by",
        "naming_series", "amended_from", "idx", "doctype"
    }
    if fieldname in system_fields:
        return False

    non_query_types = {
        "Column Break", "Section Break", "Tab Break",
        "HTML", "Heading", "Button", "Image", "Fold",
        "Attach", "Attach Image", "Signature",
        "Password", "Barcode", "Color", "Icon", "Rating",
        "Code", "JSON", "Geolocation",
        "Table", "Table MultiSelect",
    }
    if fieldtype in non_query_types:
        return False

    query_types = {
        "Data", "Small Text", "Text Editor", "Long Text", "Text",
        "Int", "Float", "Currency", "Percent",
        "Date", "Datetime", "Time",
        "Link", "Dynamic Link",
        "Select", "Check",
    }

    return fieldtype in query_types


# =============================================================================
# FIELD CLASSIFICATION
# =============================================================================

def classify_fieldtype(fieldtype):
    if fieldtype in {"Int", "Float", "Currency", "Percent"}:
        return "numeric"
    if fieldtype in {"Date", "Datetime", "Time"}:
        return "temporal"
    if fieldtype in {"Data", "Text", "Small Text", "Long Text", "Text Editor"}:
        return "text"
    if fieldtype in {"Link", "Dynamic Link"}:
        return "reference"
    if fieldtype in {"Select", "Check"}:
        return "categorical"
    return "other"


def is_commonly_filtered(fieldname, fieldtype):
    fname = fieldname.lower()
    patterns = [
        "status", "state", "enabled",
        "date", "from", "to", "posting",
        "employee", "company", "department", "designation",
        "docstatus", "workflow", "name",
        "type", "category", "group",
    ]
    if any(p in fname for p in patterns):
        return True
    if fieldtype in {"Date", "Datetime", "Select"}:
        return True
    return False


# =============================================================================
# FIELD DESCRIPTION
# =============================================================================

def generate_field_description(fieldname, label, description):
    if description:
        return description.strip()

    lname = fieldname.lower()
    if "date" in lname:
        return "Date-related field"
    if "qty" in lname or "quantity" in lname:
        return "Quantity field"
    if "total" in lname or "amount" in lname:
        return "Monetary amount field"
    if "status" in lname:
        return "Status indicator field"

    if label:
        return f"{label} field"
    return f"{fieldname.replace('_', ' ').lower()} field"


# =============================================================================
# MAIN SCHEMA EXTRACTION
# =============================================================================

def extract_doctype_schema(doctype: str):
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return None

    fields = []
    links = []
    child_tables = []

    for df in meta.fields:
        if not is_query_relevant_field(df.fieldname, df.fieldtype):
            continue

        field = {
            "fieldname": df.fieldname,
            "label": df.label,
            "type": df.fieldtype,
            "class": classify_fieldtype(df.fieldtype),
            "description": generate_field_description(
                df.fieldname, df.label, df.description
            ),
            "commonly_filtered": is_commonly_filtered(df.fieldname, df.fieldtype),
        }

        if df.fieldtype in {"Link", "Select"} and df.options:
            field["options"] = df.options

        fields.append(field)

        # 🔴 NEW: explicit link capture (already existed, preserved)
        if df.fieldtype == "Link" and df.options:
            links.append({
                "fieldname": df.fieldname,
                "label": df.label,
                "linked_doctype": df.options,
            })

        if df.fieldtype == "Table" and df.options:
            child_tables.append({
                "fieldname": df.fieldname,
                "label": df.label,
                "child_doctype": df.options,
            })

    # Ensure name
    if not any(f["fieldname"] == "name" for f in fields):
        fields.insert(0, {
            "fieldname": "name",
            "label": "ID",
            "type": "Data",
            "class": "text",
            "description": "Unique identifier",
            "commonly_filtered": True,
        })

    # Ensure docstatus
    if meta.is_submittable and not any(f["fieldname"] == "docstatus" for f in fields):
        fields.insert(1, {
            "fieldname": "docstatus",
            "label": "Status",
            "type": "Int",
            "class": "categorical",
            "description": "Document status",
            "commonly_filtered": True,
            "options": "0=Draft,1=Submitted,2=Cancelled",
        })

    schema = {
        "doctype": doctype,
        "module": meta.module,
        "description": meta.description or f"Manages {doctype} records",
        "is_submittable": bool(meta.is_submittable),
        "fields": fields,
        "links": links,
        "child_tables": child_tables,
    }

    # 🔴 NEW: richer embedding text (append-only)
    schema["embedding_text"] = build_embedding_text(schema)

    return schema


# =============================================================================
# EMBEDDING TEXT (EXTENDED, SAFE)
# =============================================================================

def build_embedding_text(schema: dict) -> str:
    lines = [
        f"DocType: {schema['doctype']}",
        f"Description: {schema['description']}",
        "Fields:",
    ]

    for f in schema["fields"]:
        line = f"- {f['fieldname']} ({f['type']}, {f['class']})"
        if f.get("options"):
            line += f" → {f['options']}"
        lines.append(line)

    # 🔴 NEW: relationships (for joins)
    if schema.get("links"):
        lines.append("Relationships:")
        for l in schema["links"]:
            lines.append(
                f"- {schema['doctype']}.{l['fieldname']} → {l['linked_doctype']}"
            )

    # 🔴 NEW: child tables
    if schema.get("child_tables"):
        lines.append("Child Tables:")
        for ct in schema["child_tables"]:
            lines.append(
                f"- {schema['doctype']}.{ct['fieldname']} → {ct['child_doctype']}"
            )

    return "\n".join(lines)


# =============================================================================
# MULTI-DOCTYPE BUILDER
# =============================================================================

def build_metadata(doctype_list: list):
    return [
        schema for dt in doctype_list
        if (schema := extract_doctype_schema(dt))
    ]
