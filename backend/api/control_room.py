from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.control_room import ControlRoomSnapshotResponse
from backend.services.control_room_service import ControlRoomService

router = APIRouter(tags=["Control Room"])


@router.get("/runs/{run_id}/control-room", response_model=ControlRoomSnapshotResponse)
def get_control_room_snapshot(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve an aggregated, read-only observability snapshot of an engineering run.
    Aggregates run status, orchestration progress, active agents, iteration groups,
    workspaces, sandboxes, findings, evaluation score, events, and sanitized logs.
    """
    return ControlRoomService.get_snapshot(run_id=run_id, db=db)
