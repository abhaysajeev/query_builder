from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, field_validator


class Filter(BaseModel):
    field: str
    op: Literal["=", "!=", ">", "<", ">=", "<=", "in", "between"]
    value: Any


class Join(BaseModel):
    doctype: str
    field: str
    condition: str


class Aggregate(BaseModel):
    function: Literal["count", "sum", "avg", "min", "max"]
    field: str


class IntentSchema(BaseModel):
    # ---------------- CORE ----------------
    action: Literal["single", "list", "aggregate"]
    doctype: str

    # ---------------- READ ----------------
    fields: List[str] = []

    # ---------------- FILTERING ----------------
    filters: List[Filter] = []

    # ---------------- RELATIONS ----------------
    joins: List[Join] = []

    # ---------------- AGGREGATION ----------------
    aggregate: Optional[Aggregate] = None
    group_by: List[str] = []  # ✅ NEW

    # ---------------- CONFIDENCE ----------------
    confidence: float = Field(..., ge=0.0, le=1.0)

    # 👇 metadata passthrough (NOT validated)
    _meta: Optional[Dict[str, Any]] = None

    # ---------------- VALIDATORS ----------------
    @field_validator("fields", mode="after")
    @classmethod
    def validate_fields_for_read(cls, v, info):
        if info.data.get("action") in {"single", "list"} and not v:
            raise ValueError("fields are required for single/list actions")
        return v

    @field_validator("aggregate", mode="after")
    @classmethod
    def validate_aggregate_for_action(cls, v, info):
        if info.data.get("action") == "aggregate" and v is None:
            raise ValueError("aggregate definition required")
        return v

    @field_validator("group_by", mode="after")
    @classmethod
    def validate_group_by_usage(cls, v, info):
        if v and info.data.get("action") != "aggregate":
            raise ValueError("group_by is only allowed with aggregate action")
        return v

    class Config:
        extra = "ignore"  # 🔒 prevents hallucinated fields
