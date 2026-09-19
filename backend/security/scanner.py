import time
import logging
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.security.models import AggregatedScanReport, ScannerReport, ScannerFinding
from backend.security.providers import (
    BaseScannerProvider,
    PatternSecretScannerProvider,
    BanditScannerProvider,
    PipAuditScannerProvider,
    NpmAuditScannerProvider,
    SemgrepScannerProvider,
    GitleaksScannerProvider,
)

logger = logging.getLogger("codex_os.security.scanner")

class SecurityScannerManager:
    """
    Orchestrates security scanning providers for Codex OS.
    Checks tool availability honestly, runs enabled scanners, and aggregates findings.
    Never fabricates vulnerability findings or claims unavailable tools succeeded.
    """

    _providers: Dict[str, BaseScannerProvider] = {
        "pattern_scanner": PatternSecretScannerProvider(),
        "bandit": BanditScannerProvider(),
        "pip-audit": PipAuditScannerProvider(),
        "npm-audit": NpmAuditScannerProvider(),
        "semgrep": SemgrepScannerProvider(),
        "gitleaks": GitleaksScannerProvider(),
    }

    @classmethod
    def register_provider(cls, name: str, provider: BaseScannerProvider) -> None:
        cls._providers[name] = provider

    @classmethod
    def get_provider(cls, name: str) -> Optional[BaseScannerProvider]:
        return cls._providers.get(name)

    @classmethod
    def get_configured_provider_names(cls) -> List[str]:
        configured = getattr(settings, "SECURITY_SCANNERS", "pattern_scanner,bandit,pip-audit,npm-audit,semgrep,gitleaks")
        names = [name.strip() for name in configured.split(",") if name.strip()]
        # Always ensure pattern_scanner is checked
        if "pattern_scanner" not in names:
            names.insert(0, "pattern_scanner")
        return names

    @classmethod
    def check_availability(cls) -> Dict[str, Dict[str, Any]]:
        """Return availability status for all known scanners."""
        results = {}
        for name, provider in cls._providers.items():
            avail, reason = provider.is_available()
            results[name] = {
                "available": avail,
                "reason": reason,
            }
        return results

    @classmethod
    def run_scans(
        cls,
        target_path: str,
        network_enabled: Optional[bool] = None,
        scanner_names: Optional[List[str]] = None
    ) -> AggregatedScanReport:
        """
        Execute configured scanners against target_path.
        Captures unavailable tools honestly without raising unhandled errors.
        """
        start_time = time.time()
        names_to_run = scanner_names or cls.get_configured_provider_names()
        is_net = network_enabled if network_enabled is not None else getattr(settings, "SECURITY_SCAN_NETWORK", False)

        attempted: List[str] = []
        available: List[str] = []
        unavailable: List[str] = []
        all_findings: List[ScannerFinding] = []
        reports: Dict[str, ScannerReport] = {}

        logger.info(f"Starting security scans on {target_path} (network_enabled={is_net})")

        for name in names_to_run:
            provider = cls._providers.get(name)
            if not provider:
                logger.warning(f"Unknown security scanner requested: {name}")
                attempted.append(name)
                unavailable.append(name)
                reports[name] = ScannerReport(
                    scanner_name=name,
                    available=False,
                    ran=False,
                    error_message=f"Scanner provider '{name}' is not registered."
                )
                continue

            attempted.append(name)
            is_avail, avail_reason = provider.is_available()

            if not is_avail:
                logger.info(f"Scanner '{name}' is unavailable: {avail_reason}")
                unavailable.append(name)
                reports[name] = ScannerReport(
                    scanner_name=name,
                    available=False,
                    ran=False,
                    error_message=avail_reason
                )
                continue

            available.append(name)
            try:
                report = provider.scan(target_path=target_path, network_enabled=is_net)
                reports[name] = report
                if report.ran:
                    all_findings.extend(report.findings)
                    logger.info(f"Scanner '{name}' completed with {len(report.findings)} findings.")
                else:
                    logger.info(f"Scanner '{name}' was skipped or produced error: {report.error_message}")
            except Exception as exc:
                logger.exception(f"Exception while executing scanner '{name}': {exc}")
                reports[name] = ScannerReport(
                    scanner_name=name,
                    available=True,
                    ran=False,
                    error_message=str(exc)
                )

        duration = round(time.time() - start_time, 3)

        # Deduplicate findings by title, file_path, line_number
        deduped_findings: List[ScannerFinding] = []
        seen = set()
        for f in all_findings:
            key = (f.title, f.file_path, f.line_number)
            if key not in seen:
                seen.add(key)
                deduped_findings.append(f)

        logger.info(
            f"Security scan completed in {duration}s: "
            f"{len(available)} available, {len(unavailable)} unavailable, "
            f"{len(deduped_findings)} total unique findings."
        )

        return AggregatedScanReport(
            scanners_attempted=attempted,
            scanners_available=available,
            scanners_unavailable=unavailable,
            findings=deduped_findings,
            duration_seconds=duration,
            reports=reports
        )
