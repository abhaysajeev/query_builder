import frappe
from query_builder.utils.vector_store import (
    rebuild_vector_store,
    retrieve_schema,
)

@frappe.whitelist()
def rebuild_embeddings():
    frappe.only_for("System Manager")

    doctypes = [
        "Employee",
        "Department",
        "Designation",
        "Shift Type",
        "Shift Assignment",
        "Leave Application",
        "Leave Type",
        "Leave Policy Assignment",
        "Attendance",
        "Employee Checkin",
        "Salary Slip",
        "Payroll Entry",
        "Salary Structure Assignment",
        "Payroll Period",
        "Holiday List",
    ]

    return rebuild_vector_store(doctypes)


@frappe.whitelist()
def search_schema(query):
    if not query or not query.strip():
        return {"error": "Query cannot be empty"}

    return retrieve_schema(query.strip())
