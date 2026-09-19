from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class ScannerFinding:
    title: str
    severity: str  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    category: str  # SECRET, INJECTION, DEPENDENCY, AUTHENTICATION, AUTHORIZATION, CONFIGURATION, FILESYSTEM, OTHER
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Optional[str] = None
    reproduction: Optional[str] = None
    remediation: Optional[str] = None

@dataclass
class ScannerReport:
    scanner_name: str
    available: bool
    ran: bool
    findings: List[ScannerFinding] = field(default_factory=list)
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    details: Optional[Dict[str, Any]] = None

@dataclass
class AggregatedScanReport:
    scanners_attempted: List[str] = field(default_factory=list)
    scanners_available: List[str] = field(default_factory=list)
    scanners_unavailable: List[str] = field(default_factory=list)
    findings: List[ScannerFinding] = field(default_factory=list)
    duration_seconds: float = 0.0
    reports: Dict[str, ScannerReport] = field(default_factory=dict)
