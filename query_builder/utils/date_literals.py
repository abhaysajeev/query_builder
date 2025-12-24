from datetime import timedelta, datetime, time
import re
import frappe


def user_now():
    """
    Returns timezone-aware datetime in USER timezone.
    """
    return frappe.utils.get_datetime()


# --------------------------------------------------
# TIME PATTERN
# --------------------------------------------------
# Matches:
#   after 8:30 am
#   before 9 am
#   after 18:00
TIME_REGEX = re.compile(
    r"(after|before)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
    re.IGNORECASE,
)


def _parse_clock(hour, minute, meridian):
    hour = int(hour)
    minute = int(minute or 0)

    if meridian:
        meridian = meridian.lower()
        if meridian == "pm" and hour != 12:
            hour += 12
        if meridian == "am" and hour == 12:
            hour = 0

    return time(hour, minute)


# --------------------------------------------------
# MAIN RESOLVER
# --------------------------------------------------

def resolve_date_literal(value: str):
    """
    Converts explicit date / time expressions to:
        ["between", start_datetime, end_datetime]

    NEVER infers policy-based meaning (late, early, etc.)
    """

    if not isinstance(value, str):
        return None

    v = value.lower().strip()
    now = user_now()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1, microseconds=-1)

    # ---------------- DATE ONLY ----------------

    if v == "today":
        return ["between", today_start, today_end]

    if v == "yesterday":
        start = today_start - timedelta(days=1)
        end = today_start - timedelta(microseconds=1)
        return ["between", start, end]

    if v == "this_week":
        monday = today_start - timedelta(days=today_start.weekday())
        sunday = monday + timedelta(days=7, microseconds=-1)
        return ["between", monday, sunday]

    if v == "last_week":
        monday = today_start - timedelta(days=today_start.weekday() + 7)
        sunday = monday + timedelta(days=7, microseconds=-1)
        return ["between", monday, sunday]

    if v == "this_month":
        first = today_start.replace(day=1)
        if first.month == 12:
            next_month = first.replace(year=first.year + 1, month=1)
        else:
            next_month = first.replace(month=first.month + 1)
        return ["between", first, next_month - timedelta(microseconds=1)]

    # ---------------- TIME MODIFIERS ----------------
    # after 8:30 am / before 9 am
    m = TIME_REGEX.search(v)
    if m:
        direction, h, mnt, meridian = m.groups()
        t = _parse_clock(h, mnt, meridian)

        start = today_start
        end = today_end

        if direction == "after":
            start = datetime.combine(today_start.date(), t)
        else:
            end = datetime.combine(today_start.date(), t)

        return ["between", start, end]

    return None
