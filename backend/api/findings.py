from typing import List, Optional
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.run import EngineeringRun
from backend.models.finding import Finding
from backend.schemas.finding import FindingResponse, FindingsSummaryResponse

router = APIRouter(tags=["Findings"])

@router.get("/runs/{run_id}/findings", response_model=List[FindingResponse])
def get_run_findings(
    run_id: int,
    type: Optional[str] = Query(None, description="Filter by finding type (BREAKER or SECURITY)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Retrieve all evidence-backed findings for an engineering run,
    with optional filtering by type, severity, and category.
    """
    run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engineering run with ID {run_id} not found"
        )

    query = db.query(Finding).filter(Finding.engineering_run_id == run_id)

    if type:
        query = query.filter(Finding.type == type.upper())
    if severity:
        query = query.filter(Finding.severity == severity.upper())
    if category:
        query = query.filter(Finding.category == category.upper())

    findings = query.order_by(Finding.id.asc()).all()
    return [FindingResponse.model_validate(f) for f in findings]


@router.get("/runs/{run_id}/findings/summary", response_model=FindingsSummaryResponse)
def get_run_findings_summary(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve aggregated metrics and distribution of findings for an engineering run.
    """
    run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engineering run with ID {run_id} not found"
        )

    findings = db.query(Finding).filter(Finding.engineering_run_id == run_id).all()

    total = len(findings)
    breaker_count = sum(1 for f in findings if f.type == "BREAKER")
    security_count = sum(1 for f in findings if f.type == "SECURITY")

    by_severity = dict(Counter(f.severity for f in findings))
    by_category = dict(Counter(f.category for f in findings))

    return FindingsSummaryResponse(
        total=total,
        breaker_count=breaker_count,
        security_count=security_count,
        by_severity=by_severity,
        by_category=by_category,
    )


@router.get("/runs/{run_id}/findings/{finding_id}", response_model=FindingResponse)
def get_finding(run_id: int, finding_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details, reproduction steps, evidence, and remediation for a specific finding.
    """
    finding = (
        db.query(Finding)
        .filter(Finding.id == finding_id, Finding.engineering_run_id == run_id)
        .first()
    )
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding with ID {finding_id} not found for run {run_id}"
        )

    return FindingResponse.model_validate(finding)
