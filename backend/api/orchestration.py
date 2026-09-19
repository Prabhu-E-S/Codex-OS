from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.orchestration import OrchestrationState
from backend.orchestrator.manager import OrchestratorManager
from backend.schemas.orchestration import StartAutonomousRunRequest, OrchestrationResponse

router = APIRouter(tags=["Autonomous Orchestrator"])

@router.post("/runs/{run_id}/start-autonomous", response_model=OrchestrationResponse)
def start_autonomous_run(
    run_id: int,
    payload: StartAutonomousRunRequest = StartAutonomousRunRequest(),
    db: Session = Depends(get_db),
):
    """
    Start autonomous multi-iteration agent workflow for an engineering run.
    """
    try:
        orch_state = OrchestratorManager.start_autonomous_run(
            run_id=run_id,
            max_iterations=payload.max_iterations,
            db=db,
        )
        return OrchestrationResponse.from_orm_model(orch_state)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting the autonomous run."
        )


@router.get("/runs/{run_id}/orchestration", response_model=OrchestrationResponse)
def get_orchestration_status(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve current workflow state, iteration counter, latest decision, and event log.
    """
    try:
        orch_state = OrchestratorManager.get_orchestration_state(run_id=run_id, db=db)
        if not orch_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No orchestration record found for run {run_id}",
            )
        return OrchestrationResponse.from_orm_model(orch_state)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching orchestration status."
        )


@router.post("/runs/{run_id}/pause", response_model=OrchestrationResponse)
def pause_autonomous_run(run_id: int, db: Session = Depends(get_db)):
    """
    Request boundary-safe pause.
    """
    try:
        orch_state = OrchestratorManager.pause_run(run_id=run_id, db=db)
        return OrchestrationResponse.from_orm_model(orch_state)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while pausing the run."
        )


@router.post("/runs/{run_id}/resume", response_model=OrchestrationResponse)
def resume_autonomous_run(run_id: int, db: Session = Depends(get_db)):
    """
    Resume an autonomous run from the PAUSED state.
    """
    try:
        orch_state = OrchestratorManager.resume_run(run_id=run_id, db=db)
        return OrchestrationResponse.from_orm_model(orch_state)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while resuming the run."
        )


@router.post("/runs/{run_id}/orchestration/cancel", response_model=OrchestrationResponse)
def cancel_autonomous_run(run_id: int, db: Session = Depends(get_db)):
    """
    Cancel an active autonomous run.
    """
    try:
        orch_state = OrchestratorManager.cancel_run(run_id=run_id, db=db)
        return OrchestrationResponse.from_orm_model(orch_state)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while cancelling the run."
        )
