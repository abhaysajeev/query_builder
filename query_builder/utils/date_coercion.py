from datetime import datetime


def coerce_between_value(value, field_type):
    if not isinstance(value, list) or len(value) != 2:
        return value

    start, end = value

    if field_type == "Date":
        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()

    return [start, end]
