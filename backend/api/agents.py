from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.agents.manager import AgentManager
from backend.agents.models import AgentStatus
from backend.schemas.agent import AgentExecutionResponse, AgentWorkflowStatusResponse

router = APIRouter(tags=["Agents"])

@router.post("/runs/{run_id}/agents/execute", response_model=AgentWorkflowStatusResponse)
def execute_agent_workflow(run_id: int, db: Session = Depends(get_db)):
    """
    Start the sequential Codex OS Agent Team workflow (Architect -> Builder -> Tester)
    for the specified engineering run.
    """
    run = AgentManager.start_workflow(run_id=run_id, db=db)
    agent_execs = (
        db.query(AgentExecution)
        .filter(AgentExecution.engineering_run_id == run_id)
        .order_by(AgentExecution.id.asc())
        .all()
    )

    active_agent = None
    for ae in agent_execs:
        if ae.status in (AgentStatus.STARTING.value, AgentStatus.RUNNING.value):
            active_agent = ae.agent_name
            break

    return AgentWorkflowStatusResponse(
        run_id=run.id,
        run_status=run.status,
        active_agent=active_agent,
        agents=[AgentExecutionResponse.model_validate(ae) for ae in agent_execs],
    )


@router.get("/runs/{run_id}/agents", response_model=List[AgentExecutionResponse])
def get_run_agents(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all agent executions and their status/output for an engineering run.
    """
    run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engineering run with ID {run_id} not found",
        )

    agent_execs = (
        db.query(AgentExecution)
        .filter(AgentExecution.engineering_run_id == run_id)
        .order_by(AgentExecution.id.asc())
        .all()
    )
    return [AgentExecutionResponse.model_validate(ae) for ae in agent_execs]


@router.get("/agent-executions/{agent_execution_id}", response_model=AgentExecutionResponse)
def get_agent_execution(agent_execution_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details, logs, and output of a specific agent execution.
    """
    agent_exec = (
        db.query(AgentExecution)
        .filter(AgentExecution.id == agent_execution_id)
        .first()
    )
    if not agent_exec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent execution with ID {agent_execution_id} not found",
        )

    return AgentExecutionResponse.model_validate(agent_exec)


@router.post("/runs/{run_id}/agents/cancel", response_model=AgentWorkflowStatusResponse)
def cancel_agent_workflow(run_id: int, db: Session = Depends(get_db)):
    """
    Cancel the active agent workflow and mark uncompleted agents as CANCELLED.
    """
    run = AgentManager.cancel_workflow(run_id=run_id, db=db)
    agent_execs = (
        db.query(AgentExecution)
        .filter(AgentExecution.engineering_run_id == run_id)
        .order_by(AgentExecution.id.asc())
        .all()
    )

    return AgentWorkflowStatusResponse(
        run_id=run.id,
        run_status=run.status,
        active_agent=None,
        agents=[AgentExecutionResponse.model_validate(ae) for ae in agent_execs],
    )
