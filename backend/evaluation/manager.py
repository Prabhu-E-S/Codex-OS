import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from backend.config import settings
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.models.evaluation import Evaluation, EvaluationDimension, EvaluationEvidence
from backend.evaluation.models import (
    EvaluationDimensionType,
    EvaluationStatus,
    DimensionStatus,
    DimensionResult,
)
from backend.evaluation.metrics import MetricCollector
from backend.evaluation.policies import ScoringPolicy
from backend.evaluation.judge import JudgeAgent
from backend.evaluation.exceptions import EvaluationError, InvalidScoreWeightsError, EvaluationNotFoundError

logger = logging.getLogger("codex_os.evaluation.manager")

class EvaluationManager:
    """
    Coordinates the full Phase 8 Evaluation & Engineering Score lifecycle:
    1. Collects measurable evidence and metrics across run lifecycle
    2. Executes deterministic scoring policies across 6 dimensions
    3. Synthesizes qualitative insights via JudgeAgent without numerical bias
    4. Computes transparent, mathematically reproducible overall Engineering Score
    5. Persists historical immutable evaluation records
    """

    @classmethod
    def evaluate_run(
        cls,
        run_id: int,
        db: Session,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Evaluation:
        """
        Evaluate a completed or terminated EngineeringRun.
        Creates an immutable, versioned Evaluation record with full dimension breakdown and evidence.
        """
        # 1. Resolve and validate weights
        if custom_weights:
            weights = custom_weights
            total_w = sum(weights.values())
            if abs(total_w - 1.0) > 1e-5:
                raise InvalidScoreWeightsError(f"Custom evaluation weights must sum to 1.0; got {total_w:.4f}")
        else:
            try:
                weights = settings.get_evaluation_weights()
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Engineering run {run_id} not found",
            )

        score_version = settings.EVALUATION_SCORE_VERSION
        started_at = datetime.now(timezone.utc)

        # 2. Create initial Evaluation record
        eval_record = Evaluation(
            engineering_run_id=run_id,
            status=EvaluationStatus.COLLECTING_EVIDENCE.value,
            score_version=score_version,
            weights_json=json.dumps(weights),
            started_at=started_at,
        )
        db.add(eval_record)
        db.commit()
        db.refresh(eval_record)

        try:
            # 3. Collect run entities
            agent_executions = (
                db.query(AgentExecution)
                .filter(AgentExecution.engineering_run_id == run_id)
                .order_by(AgentExecution.id.asc())
                .all()
            )
            findings = (
                db.query(Finding)
                .filter(Finding.engineering_run_id == run_id)
                .order_by(Finding.id.asc())
                .all()
            )
            orch_state = (
                db.query(OrchestrationState)
                .filter(OrchestrationState.engineering_run_id == run_id)
                .first()
            )

            # 4. Extract measurable metrics
            metrics = MetricCollector.collect_run_metrics(
                run=run,
                agent_executions=agent_executions,
                findings=findings,
                orchestration_state=orch_state,
            )

            # Transition to EVALUATING
            eval_record.status = EvaluationStatus.EVALUATING.value
            db.commit()

            # 5. Evaluate all 6 dimensions deterministically
            w_corr = weights.get("CORRECTNESS", 0.30)
            w_cov = weights.get("TEST_COVERAGE", 0.15)
            w_sec = weights.get("SECURITY", 0.20)
            w_maint = weights.get("MAINTAINABILITY", 0.15)
            w_perf = weights.get("PERFORMANCE", 0.10)
            w_risk = weights.get("REGRESSION_RISK", 0.10)

            dim_results: List[DimensionResult] = [
                ScoringPolicy.evaluate_correctness(metrics, w_corr),
                ScoringPolicy.evaluate_test_coverage(metrics, w_cov),
                ScoringPolicy.evaluate_security(metrics, w_sec),
                ScoringPolicy.evaluate_maintainability(metrics, w_maint),
                ScoringPolicy.evaluate_performance(metrics, w_perf),
                ScoringPolicy.evaluate_regression_risk(metrics, w_risk),
            ]

            # 6. Calculate overall Engineering Score
            overall_res = ScoringPolicy.calculate_overall_engineering_score(
                dimension_results=dim_results,
                weights=weights,
                score_version=score_version,
            )

            # 7. Invoke Judge Agent for qualitative synthesis
            judge_agent = JudgeAgent()
            working_dir = run.workspace.path if run.workspace else None
            judge_output = judge_agent.synthesize(
                engineering_goal=run.goal,
                metrics=metrics,
                dimension_results=dim_results,
                findings=findings,
                working_dir=working_dir,
            )

            # 8. Persist dimension and evidence records
            for dim_res in dim_results:
                dim_model = EvaluationDimension(
                    evaluation_id=eval_record.id,
                    dimension=dim_res.dimension.value,
                    score=dim_res.score,
                    status=dim_res.status.value,
                    weight=dim_res.weight,
                    weighted_score=dim_res.weighted_score,
                    explanation=dim_res.explanation,
                    metrics_json=json.dumps(dim_res.metrics),
                    limitations=dim_res.limitations,
                )
                db.add(dim_model)

                for ev in dim_res.evidence_items:
                    ev_model = EvaluationEvidence(
                        evaluation_id=eval_record.id,
                        dimension=ev.dimension,
                        source_type=ev.source_type,
                        source_id=ev.source_id,
                        metric_name=ev.metric_name,
                        metric_value=ev.metric_value,
                        unit=ev.unit,
                        description=ev.description,
                        evidence_text=ev.evidence_text,
                        file_path=ev.file_path,
                        line_number=ev.line_number,
                    )
                    db.add(ev_model)

            # 9. Update top-level Evaluation record
            eval_record.overall_score = overall_res.overall_score
            eval_record.status_label = overall_res.status_label.value
            eval_record.formula = overall_res.formula
            eval_record.summary = judge_output.summary
            eval_record.strengths_json = json.dumps(judge_output.strengths)
            eval_record.weaknesses_json = json.dumps(judge_output.weaknesses)
            eval_record.limitations_json = json.dumps(judge_output.limitations)
            eval_record.status = EvaluationStatus.COMPLETED.value
            eval_record.completed_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(eval_record)
            logger.info(
                f"Evaluation completed for run {run_id}: score={eval_record.overall_score}, "
                f"status={eval_record.status_label}"
            )
            return eval_record

        except Exception as exc:
            db.rollback()
            eval_record.status = EvaluationStatus.FAILED.value
            eval_record.error_message = str(exc)
            eval_record.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"Evaluation failed for run {run_id}: {exc}", exc_info=True)
            raise

    @classmethod
    def get_run_evaluations(cls, run_id: int, db: Session) -> List[Evaluation]:
        """Retrieve all historical evaluations for an engineering run."""
        return (
            db.query(Evaluation)
            .filter(Evaluation.engineering_run_id == run_id)
            .order_by(Evaluation.id.desc())
            .all()
        )

    @classmethod
    def get_evaluation_details(cls, evaluation_id: int, db: Session) -> Optional[Evaluation]:
        """Retrieve full details of an evaluation including dimensions and evidence."""
        return (
            db.query(Evaluation)
            .options(
                joinedload(Evaluation.dimensions),
                joinedload(Evaluation.evidence_items),
            )
            .filter(Evaluation.id == evaluation_id)
            .first()
        )

    @classmethod
    def get_project_evaluations(cls, project_id: int, db: Session) -> List[Evaluation]:
        """Retrieve all evaluations across all runs for a given project."""
        return (
            db.query(Evaluation)
            .join(EngineeringRun, Evaluation.engineering_run_id == EngineeringRun.id)
            .filter(EngineeringRun.project_id == project_id)
            .order_by(Evaluation.id.desc())
            .all()
        )
