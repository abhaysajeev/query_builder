# query_builder/utils/join_graph.py

from query_builder.utils.schema_extractor import extract_doctype_schema


def build_join_graph(doctypes: list[str]) -> dict:
    """
    Build adjacency list:
    {
      "Salary Slip": {
          "employee": "Employee"
      },
      "Employee": {
          "department": "Department"
      }
    }
    """
    graph = {}

    for doctype in doctypes:
        schema = extract_doctype_schema(doctype)
        if not schema:
            continue

        edges = {}
        for link in schema.get("links", []):
            field = link.get("fieldname")
            target = link.get("linked_doctype")
            if field and target:
                edges[field] = target

        graph[doctype] = edges

    return graph
