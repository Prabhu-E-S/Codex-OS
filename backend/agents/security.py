import re
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.agents.base import BaseAgent
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_security_prompt
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus
from backend.security.scanner import SecurityScannerManager
from backend.security.models import AggregatedScanReport

logger = logging.getLogger("codex_os.agents.security")

class SecurityAgent(BaseAgent):
    """
    Security Agent is responsible for analyzing the implementation for vulnerabilities,
    secrets, misconfigurations, and unsafe code patterns.
    Executes automated security scanners honestly and performs static security inspection
    without modifying production code and without executing Git commands.
    """
    agent_type = AgentType.SECURITY
    name = "Security Agent"
    role = "Security Vulnerability & Static Analysis"
    description = (
        "Inspects the implementation for security weaknesses, executes configured scanners "
        "honestly, and produces evidence-backed findings without modifying code."
    )

    def run(self, context: AgentContext) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        logger.info(f"Security Agent starting for run {context.engineering_run_id}")

        # Ingest upstream results
        architect_res = context.get_previous_result(AgentType.ARCHITECT)
        builder_res = context.get_previous_result(AgentType.BUILDER)
        tester_res = context.get_previous_result(AgentType.TESTER)
        breaker_res = context.get_previous_result(AgentType.BREAKER)

        if not builder_res or builder_res.status != AgentStatus.COMPLETED:
            err_msg = "Cannot start Security Agent: Builder implementation is missing or was not completed successfully."
            logger.error(err_msg)
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output="",
                error_message=err_msg,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                input_summary="Builder output unavailable."
            )

        architect_plan = architect_res.output if architect_res else "No plan provided."
        builder_summary = builder_res.output
        target_path = context.get_target_path()

        # 1. Execute Security Scanner abstraction honestly
        scan_report: AggregatedScanReport = SecurityScannerManager.run_scans(
            target_path=target_path,
            network_enabled=context.config.get("network_enabled", False)
        )

        scanner_summary = (
            f"Scanners Attempted: {', '.join(scan_report.scanners_attempted) or 'None'}\n"
            f"Scanners Available: {', '.join(scan_report.scanners_available) or 'None'}\n"
            f"Scanners Unavailable: {', '.join(scan_report.scanners_unavailable) or 'None'}\n"
            f"Automated Findings Count: {len(scan_report.findings)}\n"
        )
        for f in scan_report.findings:
            scanner_summary += f"- [{f.severity}] {f.title} in {f.file_path or 'unknown'}: {f.evidence or ''}\n"

        # 2. Execute static security analysis via Phase 2 CodexRunner
        prompt = build_security_prompt(context, architect_plan, builder_summary, scanner_summary)

        execution_result = CodexRunner.execute(
            run_id=context.engineering_run_id,
            goal=prompt,
            repository_path=target_path,
            project_name=context.project_name,
            timeout_seconds=context.timeout_seconds
        )

        completed_at = datetime.now(timezone.utc)

        if execution_result.status == RunStatus.COMPLETED:
            output = execution_result.stdout.strip() if execution_result.stdout else "Security analysis completed."

            # Parse findings from Codex output
            codex_findings = self._extract_findings(output)

            # Convert scanner findings to standardized dicts
            scanner_finding_dicts: List[Dict[str, Any]] = []
            for sf in scan_report.findings:
                scanner_finding_dicts.append({
                    "type": "SECURITY",
                    "severity": sf.severity,
                    "category": sf.category,
                    "title": sf.title,
                    "description": sf.description,
                    "file_path": sf.file_path,
                    "line_number": sf.line_number,
                    "evidence": sf.evidence,
                    "reproduction": sf.reproduction or f"Inspect {sf.file_path}",
                    "remediation": sf.remediation,
                })

            # Merge and deduplicate findings
            all_findings: List[Dict[str, Any]] = []
            seen = set()
            for item in scanner_finding_dicts + codex_findings:
                key = (item.get("title"), item.get("file_path"), item.get("line_number"))
                if key not in seen:
                    seen.add(key)
                    all_findings.append(item)

            logger.info(
                f"Security Agent finished for run {context.engineering_run_id} with "
                f"{len(all_findings)} total findings ({len(scanner_finding_dicts)} from scanners, "
                f"{len(codex_findings)} from static analysis)."
            )

            metadata: Dict[str, Any] = {
                "working_directory": target_path,
                "scanners_attempted": scan_report.scanners_attempted,
                "scanners_available": scan_report.scanners_available,
                "scanners_unavailable": scan_report.scanners_unavailable,
                "scanner_findings_count": len(scanner_finding_dicts),
                "codex_findings_count": len(codex_findings),
                "findings": all_findings,
                "findings_count": len(all_findings),
            }

            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                output=output,
                exit_code=execution_result.exit_code,
                error_message=None,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=(
                    f"Scanners: {len(scan_report.scanners_available)} available, "
                    f"{len(scan_report.scanners_unavailable)} unavailable. "
                    f"Builder implementation: {len(builder_summary)} chars."
                ),
                metadata=metadata
            )
        else:
            error_msg = execution_result.error_message or execution_result.stderr or "Security execution failed"
            logger.error(f"Security Agent failed for run {context.engineering_run_id}: {error_msg}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=execution_result.stdout or "",
                error_message=error_msg,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Analyzed Builder implementation ({len(builder_summary)} chars)",
                metadata={"working_directory": target_path, "findings": []}
            )

    def _extract_findings(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured finding objects from text or JSON blocks."""
        findings: List[Dict[str, Any]] = []

        json_matches = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
        for block in json_matches:
            try:
                data = json.loads(block)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "title" in item:
                            sev = str(item.get("severity", "MEDIUM")).upper()
                            if sev not in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                                sev = "MEDIUM"
                            cat = str(item.get("category", "OTHER")).upper()
                            findings.append({
                                "type": "SECURITY",
                                "severity": sev,
                                "category": cat,
                                "title": item.get("title", "Security finding"),
                                "description": item.get("description", "Discovered potential security vulnerability."),
                                "file_path": item.get("file_path"),
                                "line_number": item.get("line_number"),
                                "evidence": item.get("evidence"),
                                "reproduction": item.get("reproduction"),
                                "remediation": item.get("remediation"),
                            })
            except json.JSONDecodeError:
                pass

        return findings
