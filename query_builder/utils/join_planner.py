# query_builder/utils/join_planner.py

from collections import deque


MAX_JOIN_DEPTH = 2


def find_join_path(base_doctype: str, target_doctype: str, graph: dict):
    """
    BFS search for join path.
    Returns list of (from_doctype, field, to_doctype)
    """
    if base_doctype == target_doctype:
        return []

    queue = deque([(base_doctype, [])])
    visited = {base_doctype}

    while queue:
        current, path = queue.popleft()

        if len(path) >= MAX_JOIN_DEPTH:
            continue

        for field, next_dt in graph.get(current, {}).items():
            if next_dt in visited:
                continue

            new_path = path + [(current, field, next_dt)]
            if next_dt == target_doctype:
                return new_path

            visited.add(next_dt)
            queue.append((next_dt, new_path))

    return None


def build_joins(base_doctype: str, required_doctypes: set, graph: dict):
    """
    Build join definitions for all required doctypes.
    """
    joins = []
    seen = set()

    for target in required_doctypes:
        if target == base_doctype:
            continue

        path = find_join_path(base_doctype, target, graph)
        if not path:
            return {
                "clarification_required": True,
                "message": f"Cannot determine join path from {base_doctype} to {target}"
            }

        for frm, field, to in path:
            key = (frm, field, to)
            if key in seen:
                continue

            joins.append({
                "doctype": to,
                "field": field,
                "condition": f"{frm}.{field} = {to}.name"
            })
            seen.add(key)

    return joins
