"""
Verification Script for Autonomous Multi-Agent Finding Lifecycle in Codex OS.
Tests real finding lifecycle against the demo-project ('Task Forge AI', Project 349).
"""
import sys
from datetime import datetime, timezone

from backend.database import SessionLocal
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.services.finding_service import FindingService
from backend.services.control_room_service import ControlRoomService
from backend.orchestrator.policy import OrchestratorPolicy
from backend.orchestrator.models import OrchestratorDecision
from backend.orchestrator.feedback import IterationFeedbackCollector
from backend.evaluation.metrics import MetricCollector
from backend.evaluation.policies import ScoringPolicy
from backend.evaluation.models import MetricItem


def run_controlled_autonomous_demo():
    db = SessionLocal()
    try:
        # 1. Look up Task Forge AI demo project
        project = db.query(Project).filter(Project.id == 349).first()
        if not project:
            project = db.query(Project).filter(Project.repository_path.ilike("%demo-project%")).first()
        
        assert project is not None, "Demo project 'Task Forge AI' not found in database!"
        print(f"\n[DEMO] Found Demo Project: ID={project.id}, Name='{project.name}', Path='{project.repository_path}'")

        # =========================================================================
        # RUN 1: Controlled Resolution Run (Issue Detected in Iter 1 -> Fixed in Iter 2)
        # =========================================================================
        print("\n" + "="*80)
        print("SCENARIO 1: Evidence-Based Finding Resolution (Iter 1: OPEN -> Iter 2: RESOLVED)")
        print("="*80)

        run = EngineeringRun(
            project_id=project.id,
            goal="Harden Task Forge AI task pagination against boundary conditions",
            status="RUNNING",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
        print(f"[RUN 1] Created Engineering Run #{run_id}")

        orch_state = OrchestrationState(
            engineering_run_id=run_id,
            state="BUILDING",
            iteration=1,
            max_iterations=3,
        )
        db.add(orch_state)
        db.commit()

        # --- ITERATION 1 ---
        print("\n--- Iteration 1 ---")
        # 1A. Builder executes
        build_exec_1 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="BUILDER",
            agent_name="Builder Agent",
            status="COMPLETED",
            iteration=1,
            output="Implemented pagination parameters in TaskService.list_tasks.",
        )
        db.add(build_exec_1)
        db.commit()

        # 1B. Tester executes
        test_exec_1 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="TESTER",
            agent_name="Tester Agent",
            status="COMPLETED",
            iteration=1,
            output="31 passed in 0.58s",
        )
        db.add(test_exec_1)
        db.commit()

        # 1C. Breaker executes -> Discovers boundary failure
        breaker_exec_1 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="BREAKER",
            agent_name="Breaker Agent",
            status="COMPLETED",
            iteration=1,
            output="Discovered negative limit boundary crash in TaskService.list_tasks.",
        )
        db.add(breaker_exec_1)
        db.commit()

        breaker_finding_iter1 = {
            "type": "BREAKER",
            "severity": "HIGH",
            "category": "INPUT_VALIDATION",
            "title": "Negative limit crash in task pagination",
            "description": "Passing limit < 0 causes an uncaught SQLAlchemy DataError or negative slice exception.",
            "file_path": "app/services/task_service.py",
            "line_number": 48,
            "evidence": "DataError: LIMIT must not be negative",
            "reproduction": "client.get('/api/tasks?limit=-1')",
            "remediation": "Validate limit >= 1 and clamp to maximum 100.",
        }

        FindingService.reconcile_findings(
            db=db,
            run_id=run_id,
            agent_execution_id=breaker_exec_1.id,
            agent_type=AgentType.BREAKER,
            iteration=1,
            reported_findings=[breaker_finding_iter1],
        )

        # 1D. Security executes -> clean
        sec_exec_1 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="SECURITY",
            agent_name="Security Agent",
            status="COMPLETED",
            iteration=1,
            output="No hardcoded secrets or injection patterns detected.",
        )
        db.add(sec_exec_1)
        db.commit()

        FindingService.reconcile_findings(
            db=db,
            run_id=run_id,
            agent_execution_id=sec_exec_1.id,
            agent_type=AgentType.SECURITY,
            iteration=1,
            reported_findings=[],
        )

        # 1E. Verify DB & Control Room snapshot after Iteration 1
        db_findings_1 = db.query(Finding).filter(Finding.engineering_run_id == run_id).all()
        assert len(db_findings_1) == 1
        f1 = db_findings_1[0]
        assert f1.status == "OPEN"
        assert f1.iteration == 1
        assert f1.resolved_iteration is None
        print(f"[DB Verification - Iter 1] Finding #{f1.id}: status='{f1.status}', iteration={f1.iteration}, resolved_iteration={f1.resolved_iteration}")

        cr_snapshot_1 = ControlRoomService.get_snapshot(run_id, db)
        assert cr_snapshot_1 is not None
        assert cr_snapshot_1.findings_summary.total == 1
        assert cr_snapshot_1.findings_summary.open == 1
        assert cr_snapshot_1.findings_summary.resolved == 0
        print(f"[Control Room Verification - Iter 1] Total: {cr_snapshot_1.findings_summary.total}, Open: {cr_snapshot_1.findings_summary.open}, Resolved: {cr_snapshot_1.findings_summary.resolved}")

        # 1F. Orchestrator Decision
        open_findings_1 = db.query(Finding).filter(Finding.engineering_run_id == run_id, Finding.status == "OPEN").all()
        decision_1 = OrchestratorPolicy.evaluate(
            iteration=1,
            max_iterations=3,
            builder_result=AgentResult(AgentType.BUILDER, "", AgentStatus.COMPLETED, build_exec_1.output),
            tester_result=AgentResult(AgentType.TESTER, "", AgentStatus.COMPLETED, test_exec_1.output),
            breaker_findings=[{"severity": f.severity, "title": f.title} for f in open_findings_1 if f.type == "BREAKER"],
            security_findings=[],
        )
        assert decision_1.decision == OrchestratorDecision.RETRY_BUILDER
        print(f"[Orchestrator Decision - Iter 1] Decision: {decision_1.decision.value} -> {decision_1.reason}")

        # Prepare feedback for Iteration 2
        feedback_dict = IterationFeedbackCollector.extract_feedback(
            iteration=1,
            decision_reason=decision_1.reason,
            breaker_findings=[{"severity": f.severity, "title": f.title, "remediation": f.remediation} for f in open_findings_1 if f.type == "BREAKER"],
        )
        assert len(feedback_dict["breaker_findings"]) == 1
        print(f"[Feedback Collector] Injected {len(feedback_dict['breaker_findings'])} finding(s) into Builder Iteration 2 context.")

        # --- ITERATION 2 ---
        print("\n--- Iteration 2 ---")
        # 2A. Builder receives feedback and fixes the boundary validation
        build_exec_2 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="BUILDER",
            agent_name="Builder Agent",
            status="COMPLETED",
            iteration=2,
            output="Added input validation in TaskService.list_tasks: clamp skip >= 0 and 1 <= limit <= 100.",
        )
        db.add(build_exec_2)
        db.commit()

        # 2B. Tester verifies tests
        test_exec_2 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="TESTER",
            agent_name="Tester Agent",
            status="COMPLETED",
            iteration=2,
            output="31 passed in 0.60s",
        )
        db.add(test_exec_2)
        db.commit()

        # 2C. Breaker validates the fix: runs adversarial checks again -> 0 findings reported!
        breaker_exec_2 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="BREAKER",
            agent_name="Breaker Agent",
            status="COMPLETED",
            iteration=2,
            output="Verified input boundary handling: negative limit is now safely rejected. 0 findings.",
        )
        db.add(breaker_exec_2)
        db.commit()

        FindingService.reconcile_findings(
            db=db,
            run_id=run_id,
            agent_execution_id=breaker_exec_2.id,
            agent_type=AgentType.BREAKER,
            iteration=2,
            reported_findings=[],  # Clean!
        )

        # 2D. Security scans again -> 0 findings
        sec_exec_2 = AgentExecution(
            engineering_run_id=run_id,
            agent_type="SECURITY",
            agent_name="Security Agent",
            status="COMPLETED",
            iteration=2,
            output="Clean scan.",
        )
        db.add(sec_exec_2)
        db.commit()

        FindingService.reconcile_findings(
            db=db,
            run_id=run_id,
            agent_execution_id=sec_exec_2.id,
            agent_type=AgentType.SECURITY,
            iteration=2,
            reported_findings=[],
        )

        # 2E. Verify DB & Control Room snapshot after Iteration 2
        db.refresh(f1)
        assert f1.status == "RESOLVED"
        assert f1.iteration == 1  # Originally detected in Iteration 1
        assert f1.resolved_iteration == 2  # Resolved in Iteration 2
        assert f1.resolved_at is not None
        print(f"[DB Verification - Iter 2] Finding #{f1.id}: status='{f1.status}', detected_iteration={f1.iteration}, resolved_iteration={f1.resolved_iteration}, resolved_at={f1.resolved_at}")

        cr_snapshot_2 = ControlRoomService.get_snapshot(run_id, db)
        assert cr_snapshot_2 is not None
        assert cr_snapshot_2.findings_summary.total == 1
        assert cr_snapshot_2.findings_summary.open == 0
        assert cr_snapshot_2.findings_summary.resolved == 1
        print(f"[Control Room Verification - Iter 2] Total: {cr_snapshot_2.findings_summary.total}, Open: {cr_snapshot_2.findings_summary.open}, Resolved: {cr_snapshot_2.findings_summary.resolved}")

        # 2F. Orchestrator Decision: No open blocking findings -> STOP_SUCCESS!
        open_findings_2 = db.query(Finding).filter(Finding.engineering_run_id == run_id, Finding.status == "OPEN").all()
        decision_2 = OrchestratorPolicy.evaluate(
            iteration=2,
            max_iterations=3,
            builder_result=AgentResult(AgentType.BUILDER, "", AgentStatus.COMPLETED, build_exec_2.output),
            tester_result=AgentResult(AgentType.TESTER, "", AgentStatus.COMPLETED, test_exec_2.output),
            breaker_findings=[{"severity": f.severity, "title": f.title} for f in open_findings_2 if f.type == "BREAKER"],
            security_findings=[],
        )
        assert decision_2.decision == OrchestratorDecision.STOP_SUCCESS
        print(f"[Orchestrator Decision - Iter 2] Decision: {decision_2.decision.value} -> {decision_2.reason}")

        # 2G. Evaluation Metrics: Ensure resolved findings do not penalize scores
        all_run_findings = db.query(Finding).filter(Finding.engineering_run_id == run_id).all()
        eval_stats = MetricCollector._aggregate_findings(all_run_findings)
        assert eval_stats["open_findings"] == 0
        assert eval_stats["resolved_findings"] == 1
        assert eval_stats["high_findings"] == 0
        print(f"[Evaluation Verification] Active High Findings Penalty: {eval_stats['high_findings']} (0 penalty for resolved finding)")

        # =========================================================================
        # SCENARIO 2: Unresolved Finding Remains OPEN (No Duplicates)
        # =========================================================================
        print("\n" + "="*80)
        print("SCENARIO 2: Unresolved Issue Persists (Iter 1: OPEN -> Iter 2: OPEN, No Duplicates)")
        print("="*80)

        run_unfixed = EngineeringRun(
            project_id=project.id,
            goal="Demonstrate persistent open finding across iterations",
            status="RUNNING",
        )
        db.add(run_unfixed)
        db.commit()
        db.refresh(run_unfixed)
        run_unfixed_id = run_unfixed.id
        print(f"[RUN 2] Created Engineering Run #{run_unfixed_id}")

        persisted_issue = {
            "type": "BREAKER",
            "severity": "HIGH",
            "category": "ERROR_HANDLING",
            "title": "Uncaught ValueError on duplicate task title",
            "description": "Duplicate task title causes uncaught ValueError instead of 409 Conflict.",
            "file_path": "app/services/task_service.py",
            "line_number": 75,
        }

        # Iteration 1: Issue detected
        exec_u1 = AgentExecution(
            engineering_run_id=run_unfixed_id,
            agent_type="BREAKER",
            agent_name="Breaker Agent",
            status="COMPLETED",
            iteration=1,
        )
        db.add(exec_u1)
        db.commit()

        FindingService.reconcile_findings(
            db=db,
            run_id=run_unfixed_id,
            agent_execution_id=exec_u1.id,
            agent_type=AgentType.BREAKER,
            iteration=1,
            reported_findings=[persisted_issue],
        )

        # Iteration 2: Builder did NOT fix -> Breaker detects the same issue again
        exec_u2 = AgentExecution(
            engineering_run_id=run_unfixed_id,
            agent_type="BREAKER",
            agent_name="Breaker Agent",
            status="COMPLETED",
            iteration=2,
        )
        db.add(exec_u2)
        db.commit()

        persisted_issue_iter2 = dict(persisted_issue)
        persisted_issue_iter2["line_number"] = 78  # slightly shifted

        FindingService.reconcile_findings(
            db=db,
            run_id=run_unfixed_id,
            agent_execution_id=exec_u2.id,
            agent_type=AgentType.BREAKER,
            iteration=2,
            reported_findings=[persisted_issue_iter2],
        )

        # Verify DB: Still only 1 record, remains OPEN!
        records_run2 = db.query(Finding).filter(Finding.engineering_run_id == run_unfixed_id).all()
        assert len(records_run2) == 1
        assert records_run2[0].status == "OPEN"
        assert records_run2[0].iteration == 1
        assert records_run2[0].resolved_iteration is None
        assert records_run2[0].line_number == 78
        print(f"[DB Verification - Unfixed Run] Finding #{records_run2[0].id}: status='{records_run2[0].status}', records_count={len(records_run2)} (NO duplicate created)")

        # Control Room snapshot verification for unfixed run
        cr_unfixed_snap = ControlRoomService.get_snapshot(run_unfixed_id, db)
        assert cr_unfixed_snap.findings_summary.total == 1
        assert cr_unfixed_snap.findings_summary.open == 1
        assert cr_unfixed_snap.findings_summary.resolved == 0
        print(f"[Control Room Verification - Unfixed Run] Open: {cr_unfixed_snap.findings_summary.open}, Resolved: {cr_unfixed_snap.findings_summary.resolved}")

        # Iteration 3: Max iterations reached with unresolved issue -> STOP_FAILURE
        decision_unfixed = OrchestratorPolicy.evaluate(
            iteration=3,
            max_iterations=3,
            builder_result=AgentResult(AgentType.BUILDER, "", AgentStatus.COMPLETED, "Tried to fix."),
            tester_result=AgentResult(AgentType.TESTER, "", AgentStatus.COMPLETED, "31 passed"),
            breaker_findings=[{"severity": "HIGH", "title": records_run2[0].title}],
            security_findings=[],
        )
        assert decision_unfixed.decision == OrchestratorDecision.STOP_FAILURE
        print(f"[Orchestrator Decision - Max Iterations Reached] Decision: {decision_unfixed.decision.value} -> {decision_unfixed.reason}")

        print("\n" + "="*80)
        print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
        print("="*80)

    finally:
        db.close()


if __name__ == "__main__":
    run_controlled_autonomous_demo()
