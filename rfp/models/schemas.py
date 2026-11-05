from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CriterionEvaluation(BaseModel):
    """An AI-assigned score and its source-document support for one criterion."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: int = Field(gt=0)
    score: float = Field(ge=0)
    justification: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class SupplierEvaluation(BaseModel):
    """Validated AI evaluation for exactly one supplier proposal."""

    model_config = ConfigDict(extra="forbid")

    supplier_name: str = Field(min_length=1)
    criteria: list[CriterionEvaluation] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    overall_summary: str = Field(min_length=1)

    @field_validator("risks")
    @classmethod
    def clean_risks(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
