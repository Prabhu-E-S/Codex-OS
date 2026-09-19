from datetime import datetime, timezone
import json
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    engineering_run_id = Column(
        Integer,
        ForeignKey("engineering_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Lifecycle status: PENDING, COLLECTING_EVIDENCE, EVALUATING, COMPLETED, FAILED
    status = Column(String(50), nullable=False, default="PENDING", index=True)

    # Overall numerical Engineering Score (0.0 - 100.0)
    overall_score = Column(Float, nullable=True)

    # Status classification: STRONG, ADEQUATE, WEAK, INSUFFICIENT_EVIDENCE
    status_label = Column(String(50), nullable=False, default="PENDING")

    # Scoring engine versioning
    score_version = Column(String(50), nullable=False, default="v1")

    # Weights configuration used for this evaluation (JSON dictionary)
    weights_json = Column(Text, nullable=False, default="{}")

    # Explicit calculation formula text
    formula = Column(Text, nullable=True)

    # Judge qualitative interpretation
    summary = Column(Text, nullable=True)
    strengths_json = Column(Text, nullable=False, default="[]")
    weaknesses_json = Column(Text, nullable=False, default="[]")
    limitations_json = Column(Text, nullable=False, default="[]")

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    engineering_run = relationship("EngineeringRun", back_populates="evaluations")
    dimensions = relationship(
        "EvaluationDimension",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationDimension.id"
    )
    evidence_items = relationship(
        "EvaluationEvidence",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationEvidence.id"
    )

    @property
    def weights(self) -> dict:
        try:
            return json.loads(self.weights_json)
        except Exception:
            return {}

    @property
    def strengths(self) -> list:
        try:
            return json.loads(self.strengths_json)
        except Exception:
            return []

    @property
    def weaknesses(self) -> list:
        try:
            return json.loads(self.weaknesses_json)
        except Exception:
            return []

    @property
    def limitations(self) -> list:
        try:
            return json.loads(self.limitations_json)
        except Exception:
            return []


class EvaluationDimension(Base):
    __tablename__ = "evaluation_dimensions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    evaluation_id = Column(
        Integer,
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Dimension type: CORRECTNESS, TEST_COVERAGE, SECURITY, MAINTAINABILITY, PERFORMANCE, REGRESSION_RISK
    dimension = Column(String(50), nullable=False, index=True)

    # Dimension score: 0.0 - 100.0 or None if INSUFFICIENT_EVIDENCE
    score = Column(Float, nullable=True)

    # Status: STRONG, ADEQUATE, WEAK, INSUFFICIENT_EVIDENCE
    status = Column(String(50), nullable=False, default="INSUFFICIENT_EVIDENCE")

    # Configured weight in overall score calculation
    weight = Column(Float, nullable=False, default=0.0)

    # Weighted score contribution (score * weight or None)
    weighted_score = Column(Float, nullable=True)

    # Detailed human-readable explanation
    explanation = Column(Text, nullable=False, default="")

    # JSON serialized dictionary of metrics backing this dimension
    metrics_json = Column(Text, nullable=False, default="{}")

    # Limitations or tool unavailability notes for this dimension
    limitations = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    evaluation = relationship("Evaluation", back_populates="dimensions")

    @property
    def metrics(self) -> dict:
        try:
            return json.loads(self.metrics_json)
        except Exception:
            return {}


class EvaluationEvidence(Base):
    __tablename__ = "evaluation_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    evaluation_id = Column(
        Integer,
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    dimension = Column(String(50), nullable=False, index=True)

    # Source type: TEST, BREAKER, SECURITY, LINTER, COVERAGE, BENCHMARK, AGENT_EXECUTION, ORCHESTRATION, STATIC_ANALYSIS
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(100), nullable=True)

    metric_name = Column(String(100), nullable=False)
    metric_value = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)

    description = Column(Text, nullable=False)

    # Concrete evidence snippet (with all sensitive tokens/keys redacted)
    evidence_text = Column(Text, nullable=True)

    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    evaluation = relationship("Evaluation", back_populates="evidence_items")
