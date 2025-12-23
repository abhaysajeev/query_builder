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
    action: Literal["single", "list", "aggregate"]
    doctype: str
    fields: List[str] = []
    filters: List[Filter] = []
    joins: List[Join] = []
    aggregate: Optional[Aggregate] = None
    confidence: float = Field(..., ge=0.0, le=1.0)

    # 👇 metadata passthrough (NOT validated)
    _meta: Optional[Dict[str, Any]] = None

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

    class Config:
        extra = "ignore"  # 👈 important
