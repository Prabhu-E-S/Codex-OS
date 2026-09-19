from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class EvaluationEvidenceResponse(BaseModel):
    id: int
    evaluation_id: int
    dimension: str
    source_type: str
    source_id: Optional[str] = None
    metric_name: str
    metric_value: Optional[str] = None
    unit: Optional[str] = None
    description: str
    evidence_text: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationDimensionResponse(BaseModel):
    id: int
    evaluation_id: int
    dimension: str
    score: Optional[float] = None
    status: str
    weight: float
    weighted_score: Optional[float] = None
    explanation: str
    metrics: Dict[str, Any] = {}
    limitations: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, model) -> "EvaluationDimensionResponse":
        return cls(
            id=model.id,
            evaluation_id=model.evaluation_id,
            dimension=model.dimension,
            score=model.score,
            status=model.status,
            weight=model.weight,
            weighted_score=model.weighted_score,
            explanation=model.explanation,
            metrics=model.metrics,
            limitations=model.limitations,
            created_at=model.created_at,
        )


class EvaluationResponse(BaseModel):
    id: int
    engineering_run_id: int
    status: str
    overall_score: Optional[float] = None
    status_label: str
    score_version: str
    weights: Dict[str, float] = {}
    formula: Optional[str] = None
    summary: Optional[str] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    limitations: List[str] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    dimensions: Optional[List[EvaluationDimensionResponse]] = None
    evidence_items: Optional[List[EvaluationEvidenceResponse]] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, model, include_children: bool = True) -> "EvaluationResponse":
        dims = None
        evidence = None
        if include_children:
            if hasattr(model, "dimensions") and model.dimensions:
                dims = [EvaluationDimensionResponse.from_orm_model(d) for d in model.dimensions]
            if hasattr(model, "evidence_items") and model.evidence_items:
                evidence = [EvaluationEvidenceResponse.model_validate(e) for e in model.evidence_items]

        return cls(
            id=model.id,
            engineering_run_id=model.engineering_run_id,
            status=model.status,
            overall_score=model.overall_score,
            status_label=model.status_label,
            score_version=model.score_version,
            weights=model.weights,
            formula=model.formula,
            summary=model.summary,
            strengths=model.strengths,
            weaknesses=model.weaknesses,
            limitations=model.limitations,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
            dimensions=dims,
            evidence_items=evidence,
        )


class EvaluateRunRequest(BaseModel):
    weights: Optional[Dict[str, float]] = None
