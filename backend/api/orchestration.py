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
    Orchestrates Architect -> Builder -> Tester -> Breaker -> Security -> Decision loop.
    """
    orch_state = OrchestratorManager.start_autonomous_run(
        run_id=run_id,
        max_iterations=payload.max_iterations,
        db=db,
    )
    return OrchestrationResponse.from_orm_model(orch_state)


@router.get("/runs/{run_id}/orchestration", response_model=OrchestrationResponse)
def get_orchestration_status(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve current workflow state, iteration counter, latest decision, and event log.
    """
    orch_state = OrchestratorManager.get_orchestration_state(run_id=run_id, db=db)
    if not orch_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No orchestration record found for run {run_id}",
        )
    return OrchestrationResponse.from_orm_model(orch_state)


@router.post("/runs/{run_id}/pause", response_model=OrchestrationResponse)
def pause_autonomous_run(run_id: int, db: Session = Depends(get_db)):
    """
    Request boundary-safe pause. The currently executing agent finishes its step
    before the orchestrator pauses transition to the next agent.
    """
    orch_state = OrchestratorManager.pause_run(run_id=run_id, db=db)
    return OrchestrationResponse.from_orm_model(orch_state)


@router.post("/runs/{run_id}/resume", response_model=OrchestrationResponse)
def resume_autonomous_run(run_id: int, db: Session = Depends(get_db)):
    """
    Resume an autonomous run from the PAUSED state.
    """
    orch_state = OrchestratorManager.resume_run(run_id=run_id, db=db)
    return OrchestrationResponse.from_orm_model(orch_state)


@router.post("/runs/{run_id}/orchestration/cancel", response_model=OrchestrationResponse)
def cancel_autonomous_run(run_id: int, db: Session = Depends(get_db)):
    """
    Cancel an active autonomous run.
    """
    orch_state = OrchestratorManager.cancel_run(run_id=run_id, db=db)
    return OrchestrationResponse.from_orm_model(orch_state)
