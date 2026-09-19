import os
import re
import json
import time
import shutil
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional

from backend.security.models import ScannerReport, ScannerFinding
from backend.security.exceptions import ScannerExecutionError

logger = logging.getLogger("codex_os.security.providers")

class BaseScannerProvider(ABC):
    """Abstract base provider for all security scanning engines."""
    name: str

    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        """Check if this scanner's binary or runtime requirements are available."""
        pass

    @abstractmethod
    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        """Execute the security scan against the target directory."""
        pass


class PatternSecretScannerProvider(BaseScannerProvider):
    """
    Built-in, zero-dependency static pattern and secret scanner.
    Analyzes code files for secrets, credentials, command injection, SQL injection,
    and path traversal patterns. Runs reliably offline.
    """
    name = "pattern_scanner"

    PATTERNS = [
        {
            "category": "SECRET",
            "severity": "CRITICAL",
            "regex": re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
            "title": "Hard-coded AWS Access Key ID detected",
            "description": "Found a potential AWS Access Key ID hard-coded in the source code.",
            "remediation": "Move credentials to secure environment variables or a secrets manager.",
        },
        {
            "category": "SECRET",
            "severity": "CRITICAL",
            "regex": re.compile(r"-----BEGIN (?:RSA|EC|PGP|OPENSSH) PRIVATE KEY-----"),
            "title": "Private encryption key embedded in source",
            "description": "An embedded private key was detected in application source code.",
            "remediation": "Remove private key from source control and load from secure key storage.",
        },
        {
            "category": "SECRET",
            "severity": "HIGH",
            "regex": re.compile(r"(?:api[_-]?key|secret[_-]?token|auth[_-]?token)\s*=\s*['\"][a-zA-Z0-9_\-\.]{16,}['\"]", re.IGNORECASE),
            "title": "Hard-coded API key or authorization token detected",
            "description": "A high-entropy secret token was found assigned directly in the code.",
            "remediation": "Extract the API key to environment variables and do not commit secrets.",
        },
        {
            "category": "SECRET",
            "severity": "HIGH",
            "regex": re.compile(r"password\s*=\s*['\"][^'\"]{6,}['\"]", re.IGNORECASE),
            "title": "Hard-coded password detected",
            "description": "A plaintext password string was detected in configuration or source code.",
            "remediation": "Use external environment secrets or hashed secret references.",
        },
        {
            "category": "INJECTION",
            "severity": "CRITICAL",
            "regex": re.compile(r"(?:subprocess\.(?:call|Popen|run)|os\.system)\([^)]*shell\s*=\s*True", re.IGNORECASE),
            "title": "Command injection risk: shell=True in subprocess call",
            "description": "Executing subprocess with shell=True allows arbitrary command execution if user input is passed.",
            "remediation": "Avoid shell=True. Pass command arguments as a list without invoking a shell.",
        },
        {
            "category": "INJECTION",
            "severity": "HIGH",
            "regex": re.compile(r"(?:execute|cursor\.execute)\(\s*f[\"'].*SELECT.*\{", re.IGNORECASE),
            "title": "SQL Injection risk: formatted string in SQL execution",
            "description": "SQL query is formatted dynamically using Python f-strings rather than parameterized queries.",
            "remediation": "Use parameterized queries or ORM abstractions to prevent SQL injection.",
        },
        {
            "category": "FILESYSTEM",
            "severity": "HIGH",
            "regex": re.compile(r"open\(\s*(?:os\.path\.join\([^)]+\)|f[\"'][^\"']*\{[^}]+\}[^\"']*[\"'])\s*,?\s*['\"]r", re.IGNORECASE),
            "title": "Path traversal risk in dynamic file access",
            "description": "File path is dynamically constructed without path normalization or boundary validation.",
            "remediation": "Validate paths using os.path.realpath/resolve and ensure they stay within intended directory.",
        },
    ]

    IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache"}
    SCAN_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".env", ".ini", ".cfg", ".sh"}

    def is_available(self) -> Tuple[bool, str]:
        return True, "PatternSecretScanner is always available (built-in engine)."

    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        start_time = time.time()
        findings: List[ScannerFinding] = []

        if not os.path.exists(target_path):
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message=f"Target path does not exist: {target_path}",
                duration_seconds=round(time.time() - start_time, 3)
            )

        try:
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in self.SCAN_EXTENSIONS:
                        continue

                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, target_path).replace("\\", "/")

                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, start=1):
                                for rule in self.PATTERNS:
                                    match = rule["regex"].search(line)
                                    if match:
                                        matched_str = match.group(0)
                                        # Redact sensitive portions if category is SECRET
                                        if rule["category"] == "SECRET" and len(matched_str) > 8:
                                            evidence_str = line.strip().replace(matched_str, matched_str[:4] + "..." + matched_str[-4:])
                                        else:
                                            evidence_str = line.strip()

                                        finding = ScannerFinding(
                                            title=rule["title"],
                                            severity=rule["severity"],
                                            category=rule["category"],
                                            description=rule["description"],
                                            file_path=rel_path,
                                            line_number=line_num,
                                            evidence=f"Line {line_num}: {evidence_str}",
                                            reproduction=f"Inspect line {line_num} in {rel_path}",
                                            remediation=rule["remediation"],
                                        )
                                        findings.append(finding)
                    except Exception as err:
                        logger.warning(f"Could not read file {full_path} for scanning: {err}")

            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=True,
                findings=findings,
                duration_seconds=round(time.time() - start_time, 3),
                details={"files_scanned_root": target_path, "findings_count": len(findings)}
            )
        except Exception as exc:
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message=str(exc),
                duration_seconds=round(time.time() - start_time, 3)
            )


class BanditScannerProvider(BaseScannerProvider):
    """Bandit security scanner for Python repositories."""
    name = "bandit"

    def is_available(self) -> Tuple[bool, str]:
        path = shutil.which("bandit")
        if path:
            return True, f"Bandit executable found at {path}"
        return False, "Bandit executable is not installed in the environment."

    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        start_time = time.time()
        is_avail, reason = self.is_available()
        if not is_avail:
            return ScannerReport(
                scanner_name=self.name,
                available=False,
                ran=False,
                error_message=reason,
                duration_seconds=0.0
            )

        cmd = ["bandit", "-r", target_path, "-f", "json", "-q"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            findings: List[ScannerFinding] = []
            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    results = data.get("results", [])
                    for item in results:
                        sev_map = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
                        sev = sev_map.get(item.get("issue_severity", "LOW"), "MEDIUM")
                        file_path = os.path.relpath(item.get("filename", ""), target_path).replace("\\", "/")
                        findings.append(ScannerFinding(
                            title=item.get("issue_text", "Bandit Security Issue"),
                            severity=sev,
                            category="INJECTION" if "injection" in item.get("test_name", "").lower() else "OTHER",
                            description=f"Bandit test {item.get('test_name')} ({item.get('test_id')}): {item.get('issue_text')}",
                            file_path=file_path,
                            line_number=item.get("line_number"),
                            evidence=item.get("code", "").strip(),
                            reproduction=f"Run bandit on {file_path}",
                            remediation=item.get("more_info", "Review and remediate according to Bandit guidelines.")
                        ))
                except json.JSONDecodeError:
                    pass

            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=True,
                findings=findings,
                duration_seconds=round(time.time() - start_time, 3),
            )
        except Exception as exc:
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message=str(exc),
                duration_seconds=round(time.time() - start_time, 3)
            )


class PipAuditScannerProvider(BaseScannerProvider):
    """pip-audit dependency vulnerability scanner."""
    name = "pip-audit"

    def is_available(self) -> Tuple[bool, str]:
        path = shutil.which("pip-audit")
        if path:
            return True, f"pip-audit executable found at {path}"
        return False, "pip-audit is not installed in the environment."

    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        start_time = time.time()
        is_avail, reason = self.is_available()
        if not is_avail:
            return ScannerReport(
                scanner_name=self.name,
                available=False,
                ran=False,
                error_message=reason,
                duration_seconds=0.0
            )

        req_file = os.path.join(target_path, "requirements.txt")
        if not os.path.exists(req_file):
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message="No requirements.txt found in target workspace.",
                duration_seconds=0.0
            )

        cmd = ["pip-audit", "-r", req_file, "-f", "json"]
        if not network_enabled:
            # Without network, pip-audit cannot fetch CVE database unless pre-cached
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message="Network access is disabled; pip-audit requires network to query vulnerability database.",
                duration_seconds=0.0
            )

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            findings: List[ScannerFinding] = []
            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    for dep in data.get("dependencies", []):
                        for vuln in dep.get("vulns", []):
                            findings.append(ScannerFinding(
                                title=f"Vulnerable dependency: {dep.get('name')} {dep.get('version')}",
                                severity="HIGH",
                                category="DEPENDENCY",
                                description=vuln.get("description", f"Known vulnerability {vuln.get('id')}"),
                                file_path="requirements.txt",
                                evidence=f"Package {dep.get('name')}=={dep.get('version')} flagged with {vuln.get('id')}",
                                remediation=f"Upgrade {dep.get('name')} to a patched release: {', '.join(vuln.get('fix_versions', [])) or 'latest'}"
                            ))
                except json.JSONDecodeError:
                    pass

            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=True,
                findings=findings,
                duration_seconds=round(time.time() - start_time, 3)
            )
        except Exception as exc:
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message=str(exc),
                duration_seconds=round(time.time() - start_time, 3)
            )


class NpmAuditScannerProvider(BaseScannerProvider):
    """npm audit dependency scanner for Node.js projects."""
    name = "npm-audit"

    def is_available(self) -> Tuple[bool, str]:
        path = shutil.which("npm")
        if path:
            return True, f"npm executable found at {path}"
        return False, "npm is not installed in the environment."

    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        start_time = time.time()
        is_avail, reason = self.is_available()
        if not is_avail:
            return ScannerReport(
                scanner_name=self.name,
                available=False,
                ran=False,
                error_message=reason,
                duration_seconds=0.0
            )

        pkg_json = os.path.join(target_path, "package.json")
        if not os.path.exists(pkg_json):
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message="No package.json found in target directory.",
                duration_seconds=0.0
            )

        if not network_enabled:
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message="Network access is disabled; npm audit requires network access to query npm registry.",
                duration_seconds=0.0
            )

        try:
            proc = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=target_path,
                capture_output=True,
                text=True,
                timeout=60,
                shell=True
            )
            findings: List[ScannerFinding] = []
            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    vulnerabilities = data.get("vulnerabilities", {})
                    for pkg_name, details in vulnerabilities.items():
                        sev_raw = details.get("severity", "moderate").upper()
                        sev = "MEDIUM" if sev_raw == "MODERATE" else (sev_raw if sev_raw in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] else "MEDIUM")
                        findings.append(ScannerFinding(
                            title=f"Vulnerable Node package: {pkg_name}",
                            severity=sev,
                            category="DEPENDENCY",
                            description=f"Vulnerability in {pkg_name}: via {', '.join(str(v) for v in details.get('via', []))}",
                            file_path="package.json",
                            evidence=f"Package {pkg_name} affected range: {details.get('range', 'all')}",
                            remediation=f"Run npm update {pkg_name} or audit fix"
                        ))
                except json.JSONDecodeError:
                    pass

            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=True,
                findings=findings,
                duration_seconds=round(time.time() - start_time, 3)
            )
        except Exception as exc:
            return ScannerReport(
                scanner_name=self.name,
                available=True,
                ran=False,
                error_message=str(exc),
                duration_seconds=round(time.time() - start_time, 3)
            )


class SemgrepScannerProvider(BaseScannerProvider):
    """Semgrep static analysis scanner."""
    name = "semgrep"

    def is_available(self) -> Tuple[bool, str]:
        path = shutil.which("semgrep")
        if path:
            return True, f"Semgrep executable found at {path}"
        return False, "Semgrep is not installed in the environment."

    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        is_avail, reason = self.is_available()
        return ScannerReport(
            scanner_name=self.name,
            available=is_avail,
            ran=False,
            error_message=reason if not is_avail else "Semgrep rules require offline rulepack.",
            duration_seconds=0.0
        )


class GitleaksScannerProvider(BaseScannerProvider):
    """Gitleaks secret scanner."""
    name = "gitleaks"

    def is_available(self) -> Tuple[bool, str]:
        path = shutil.which("gitleaks")
        if path:
            return True, f"Gitleaks executable found at {path}"
        return False, "Gitleaks is not installed in the environment."

    def scan(self, target_path: str, network_enabled: bool = False) -> ScannerReport:
        is_avail, reason = self.is_available()
        return ScannerReport(
            scanner_name=self.name,
            available=is_avail,
            ran=False,
            error_message=reason if not is_avail else "Gitleaks directory scanning not configured.",
            duration_seconds=0.0
        )
