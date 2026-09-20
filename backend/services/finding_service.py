import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models.finding import Finding
from backend.agents.models import AgentType

logger = logging.getLogger("codex_os.services.finding_service")


class FindingService:
    """
    Evidence-based finding lifecycle management and reconciliation service.
    Ensures findings transition between OPEN and RESOLVED deterministically
    based on subsequent validation agent execution outcomes.
    """

    @staticmethod
    def normalize_title(title: Optional[str]) -> str:
        if not title:
            return ""
        t = title.strip().lower()
        # Remove common agent title prefixes
        t = re.sub(r"^(breaker finding|adversarial finding|security finding|vulnerability|issue):\s*", "", t)
        # Collapse multiple spaces
        t = re.sub(r"\s+", " ", t)
        return t

    @staticmethod
    def normalize_path(path: Optional[str]) -> str:
        if not path:
            return ""
        p = path.replace("\\", "/").strip()
        p = re.sub(r"^(\./)+", "", p)
        return p.strip("/").lower()

    @staticmethod
    def normalize_category(category: Optional[str]) -> str:
        if not category:
            return ""
        return category.strip().upper()

    @classmethod
    def matches(cls, existing: Finding, candidate: Dict[str, Any]) -> bool:
        """
        Determines whether a candidate finding from a new scan corresponds
        to an existing finding record using stable identity attributes.
        """
        candidate_type = (candidate.get("type") or "").strip().upper()
        existing_type = (existing.type or "").strip().upper()
        if candidate_type and existing_type and candidate_type != existing_type:
            return False

        exist_path = cls.normalize_path(existing.file_path)
        cand_path = cls.normalize_path(candidate.get("file_path"))

        # If both specify paths, verify they point to the same file
        if exist_path and cand_path:
            if exist_path != cand_path and not exist_path.endswith(cand_path) and not cand_path.endswith(exist_path):
                return False

        exist_title = cls.normalize_title(existing.title)
        cand_title = cls.normalize_title(candidate.get("title", ""))
        exist_cat = cls.normalize_category(existing.category)
        cand_cat = cls.normalize_category(candidate.get("category"))

        # Exact title match
        if exist_title and cand_title and exist_title == cand_title:
            return True

        # Substring containment
        if exist_title and cand_title:
            if (exist_title in cand_title or cand_title in exist_title) and min(len(exist_title), len(cand_title)) >= 8:
                return True

        # Token overlap / Jaccard similarity on title words
        tokens_exist = set(re.findall(r"\w{3,}", exist_title))
        tokens_cand = set(re.findall(r"\w{3,}", cand_title))
        if tokens_exist and tokens_cand:
            overlap = len(tokens_exist & tokens_cand) / len(tokens_exist | tokens_cand)
            if overlap >= 0.55:
                return True
            if overlap >= 0.35 and (exist_cat == cand_cat or (exist_path and exist_path == cand_path)):
                return True

        # If both file path and category match exactly, and line number is close
        if exist_path and cand_path and exist_path == cand_path:
            if exist_cat and cand_cat and exist_cat == cand_cat:
                cand_line = candidate.get("line_number")
                exist_line = existing.line_number
                if cand_line is not None and exist_line is not None:
                    if abs(cand_line - exist_line) <= 25:
                        return True

        return False

    @classmethod
    def reconcile_findings(
        cls,
        db: Session,
        run_id: int,
        agent_execution_id: Optional[int],
        agent_type: Any,
        iteration: int,
        reported_findings: List[Dict[str, Any]],
    ) -> List[Finding]:
        """
        Reconciles incoming findings from a successful validation agent run
        against existing findings in the database.

        - If an issue is reported again: remains OPEN (no duplicate record).
        - If an issue is newly discovered: inserted as OPEN for the current iteration.
        - If a previously OPEN issue of this agent type is NO LONGER reported:
          transitions to RESOLVED with evidence from this validation iteration.
        """
        agent_type_str = agent_type.value if hasattr(agent_type, "value") else str(agent_type)
        agent_upper = agent_type_str.upper()

        if "BREAKER" in agent_upper:
            target_type = "BREAKER"
        elif "SECURITY" in agent_upper:
            target_type = "SECURITY"
        else:
            logger.warning(f"Reconcile findings called for unsupported agent type: {agent_type_str}")
            return []

        # Query all existing findings for this run and type
        existing_findings = (
            db.query(Finding)
            .filter(
                Finding.engineering_run_id == run_id,
                Finding.type == target_type,
            )
            .order_by(Finding.id.asc())
            .all()
        )

        open_findings = [f for f in existing_findings if (f.status or "OPEN").upper() != "RESOLVED"]
        matched_open_ids = set()
        persisted_or_updated: List[Finding] = []

        now = datetime.now(timezone.utc)

        for item in reported_findings:
            f_dict = dict(item)
            f_dict["type"] = target_type

            # Search for match in currently OPEN findings
            matched_finding: Optional[Finding] = None
            for candidate in open_findings:
                if candidate.id not in matched_open_ids and cls.matches(candidate, f_dict):
                    matched_finding = candidate
                    break

            if matched_finding is not None:
                # Existing issue remains present -> keep OPEN, update details if provided
                matched_open_ids.add(matched_finding.id)
                matched_finding.status = "OPEN"
                matched_finding.updated_at = now
                if f_dict.get("line_number") is not None:
                    matched_finding.line_number = f_dict.get("line_number")
                if f_dict.get("evidence"):
                    matched_finding.evidence = f_dict.get("evidence")
                if f_dict.get("reproduction"):
                    matched_finding.reproduction = f_dict.get("reproduction")
                if f_dict.get("remediation"):
                    matched_finding.remediation = f_dict.get("remediation")
                persisted_or_updated.append(matched_finding)
                logger.info(
                    f"Finding #{matched_finding.id} ('{matched_finding.title}') re-confirmed "
                    f"by {target_type} in iteration {iteration}; remains OPEN."
                )
            else:
                # New finding discovered
                new_finding = Finding(
                    engineering_run_id=run_id,
                    agent_execution_id=agent_execution_id,
                    iteration=iteration,
                    type=target_type,
                    severity=str(f_dict.get("severity", "MEDIUM")).upper(),
                    category=str(f_dict.get("category", "OTHER")).upper(),
                    title=f_dict.get("title", f"{target_type.title()} Finding"),
                    description=f_dict.get("description", ""),
                    file_path=f_dict.get("file_path"),
                    line_number=f_dict.get("line_number"),
                    evidence=f_dict.get("evidence"),
                    reproduction=f_dict.get("reproduction"),
                    remediation=f_dict.get("remediation"),
                    status="OPEN",
                )
                db.add(new_finding)
                persisted_or_updated.append(new_finding)
                logger.info(
                    f"New finding detected by {target_type} in iteration {iteration}: "
                    f"'{new_finding.title}' (severity: {new_finding.severity})."
                )

        # Reconcile absent findings:
        # Previously OPEN findings of this type that are NO LONGER detected transition to RESOLVED
        for candidate in open_findings:
            if candidate.id not in matched_open_ids:
                candidate.status = "RESOLVED"
                candidate.resolved_iteration = iteration
                candidate.resolved_at = now
                candidate.updated_at = now
                logger.info(
                    f"Evidence-based resolution: Finding #{candidate.id} ('{candidate.title}') "
                    f"transitioned to RESOLVED in iteration {iteration} (validated by clean {target_type} scan)."
                )

        db.commit()
        return persisted_or_updated
