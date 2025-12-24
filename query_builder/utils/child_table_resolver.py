# query_builder/utils/child_table_resolver.py

from query_builder.utils.schema_extractor import extract_doctype_schema


def resolve_child_table(parent_doctype: str, fieldname: str):
    """
    If field belongs to a child table of parent_doctype,
    return child doctype name.
    """
    parent_schema = extract_doctype_schema(parent_doctype)
    if not parent_schema:
        return None

    for ct in parent_schema.get("child_tables", []):
        child_doctype = ct.get("child_doctype")
        if not child_doctype:
            continue

        child_schema = extract_doctype_schema(child_doctype)
        if not child_schema:
            continue

        for f in child_schema.get("fields", []):
            if f.get("fieldname") == fieldname:
                return child_doctype

    return None
