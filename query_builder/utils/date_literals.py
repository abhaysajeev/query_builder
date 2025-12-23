from datetime import timedelta
import frappe


def user_now():
    """
    Returns timezone-aware datetime in USER timezone (not server timezone).
    Works across all Frappe versions.
    """
    return frappe.utils.get_datetime()


def resolve_date_literal(value):
    now = user_now()

    today_start = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_end = today_start + timedelta(days=1, microseconds=-1)

    if value == "today":
        return ["between", today_start, today_end]

    if value == "yesterday":
        y_start = today_start - timedelta(days=1)
        y_end = today_start - timedelta(microseconds=1)
        return ["between", y_start, y_end]

    if value == "this_week":
        # week starts Monday
        monday = today_start - timedelta(days=today_start.weekday())
        sunday = monday + timedelta(days=7, microseconds=-1)
        return ["between", monday, sunday]

    if value == "last_week":
        last_monday = today_start - timedelta(days=today_start.weekday() + 7)
        last_sunday = last_monday + timedelta(days=7, microseconds=-1)
        return ["between", last_monday, last_sunday]

    if value == "this_month":
        first = today_start.replace(day=1)
        if first.month == 12:
            next_month = first.replace(year=first.year + 1, month=1)
        else:
            next_month = first.replace(month=first.month + 1)
        return ["between", first, next_month - timedelta(microseconds=1)]

    return None
