from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

class EvaluationDimensionType(str, Enum):
    CORRECTNESS = "CORRECTNESS"
    TEST_COVERAGE = "TEST_COVERAGE"
    SECURITY = "SECURITY"
    MAINTAINABILITY = "MAINTAINABILITY"
    PERFORMANCE = "PERFORMANCE"
    REGRESSION_RISK = "REGRESSION_RISK"

class EvaluationStatus(str, Enum):
    PENDING = "PENDING"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DimensionStatus(str, Enum):
    STRONG = "STRONG"
    ADEQUATE = "ADEQUATE"
    WEAK = "WEAK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class EvidenceSourceType(str, Enum):
    TEST = "TEST"
    BREAKER = "BREAKER"
    SECURITY = "SECURITY"
    LINTER = "LINTER"
    COVERAGE = "COVERAGE"
    BENCHMARK = "BENCHMARK"
    AGENT_EXECUTION = "AGENT_EXECUTION"
    ORCHESTRATION = "ORCHESTRATION"
    STATIC_ANALYSIS = "STATIC_ANALYSIS"

@dataclass
class MetricItem:
    name: str
    value: Any
    unit: Optional[str] = None
    source: Optional[str] = None
    available: bool = True
    evidence: Optional[str] = None
    description: Optional[str] = None

@dataclass
class EvidenceItem:
    dimension: str
    source_type: str
    metric_name: str
    metric_value: Optional[str] = None
    unit: Optional[str] = None
    description: str = ""
    evidence_text: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    source_id: Optional[str] = None

@dataclass
class DimensionResult:
    dimension: EvaluationDimensionType
    score: Optional[float]
    status: DimensionStatus
    weight: float
    weighted_score: Optional[float]
    explanation: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    limitations: Optional[str] = None

@dataclass
class OverallScoreResult:
    overall_score: Optional[float]
    status_label: DimensionStatus
    score_version: str
    weights: Dict[str, float]
    formula: str
    dimension_results: List[DimensionResult]

@dataclass
class JudgeOutput:
    summary: str
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    dimension_notes: Dict[str, str] = field(default_factory=dict)
