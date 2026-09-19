from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.evaluation.manager import EvaluationManager
from backend.models.evaluation import Evaluation, EvaluationDimension, EvaluationEvidence
from backend.schemas.evaluation import (
    EvaluationResponse,
    EvaluationDimensionResponse,
    EvaluationEvidenceResponse,
    EvaluateRunRequest,
)

router = APIRouter(tags=["Evaluation & Engineering Score"])

@router.post("/runs/{run_id}/evaluate", response_model=EvaluationResponse)
def evaluate_run(
    run_id: int,
    payload: EvaluateRunRequest = EvaluateRunRequest(),
    db: Session = Depends(get_db),
):
    """
    Trigger evaluation of a completed engineering run.
    Produces deterministic Engineering Score, dimension breakdown, evidence, and Judge synthesis.
    """
    evaluation = EvaluationManager.evaluate_run(
        run_id=run_id,
        db=db,
        custom_weights=payload.weights,
    )
    # Reload with full dimensions and evidence
    detailed = EvaluationManager.get_evaluation_details(evaluation.id, db)
    return EvaluationResponse.from_orm_model(detailed or evaluation)


@router.get("/runs/{run_id}/evaluations", response_model=List[EvaluationResponse])
def get_run_evaluations(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all historical evaluations for an engineering run.
    """
    evaluations = EvaluationManager.get_run_evaluations(run_id=run_id, db=db)
    return [EvaluationResponse.from_orm_model(e, include_children=True) for e in evaluations]


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db)):
    """
    Retrieve full details of an evaluation including dimension breakdown and evidence items.
    """
    evaluation = EvaluationManager.get_evaluation_details(evaluation_id=evaluation_id, db=db)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found",
        )
    return EvaluationResponse.from_orm_model(evaluation, include_children=True)


@router.get("/evaluations/{evaluation_id}/dimensions", response_model=List[EvaluationDimensionResponse])
def get_evaluation_dimensions(evaluation_id: int, db: Session = Depends(get_db)):
    """
    Retrieve dimension breakdown for a specific evaluation.
    """
    dimensions = (
        db.query(EvaluationDimension)
        .filter(EvaluationDimension.evaluation_id == evaluation_id)
        .order_by(EvaluationDimension.id.asc())
        .all()
    )
    return [EvaluationDimensionResponse.from_orm_model(d) for d in dimensions]


@router.get("/evaluations/{evaluation_id}/evidence", response_model=List[EvaluationEvidenceResponse])
def get_evaluation_evidence(evaluation_id: int, db: Session = Depends(get_db)):
    """
    Retrieve evidence items for a specific evaluation.
    """
    evidence = (
        db.query(EvaluationEvidence)
        .filter(EvaluationEvidence.evaluation_id == evaluation_id)
        .order_by(EvaluationEvidence.id.asc())
        .all()
    )
    return [EvaluationEvidenceResponse.model_validate(e) for e in evidence]


@router.get("/projects/{project_id}/evaluations", response_model=List[EvaluationResponse])
def get_project_evaluations(project_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all evaluations across all engineering runs for a given project.
    """
    evaluations = EvaluationManager.get_project_evaluations(project_id=project_id, db=db)
    return [EvaluationResponse.from_orm_model(e, include_children=True) for e in evaluations]
