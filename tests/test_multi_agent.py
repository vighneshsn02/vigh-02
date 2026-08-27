"""
Comprehensive Unit & Integration Tests for VIGH-02 Multi-Agent Mode.
Tests SharedContext, Specialized Agents, Parallel Verification, Auto-Fix Loop,
Orchestrator Synthesis, and REST API Endpoints.
"""

import tempfile
import unittest
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional
from unittest.mock import MagicMock, patch

from vigh_agent.core.session import AgentSession
from vigh_agent.core.multi_agent.context import (
    SharedContext, AgentRole, TaskStatus, TaskItem, ExecutionPlan,
    TestReport, SecurityFinding, SecurityReport, ReviewIssue, ReviewReport,
    AutoFixAttempt, AgentMessage
)
from vigh_agent.core.multi_agent.events import MultiAgentEvent
from vigh_agent.core.multi_agent.specialized_agents import (
    PlannerAgent, CoderAgent, TesterAgent, ReviewerAgent, SecurityAgent
)
from vigh_agent.core.multi_agent.orchestrator import MultiAgentOrchestrator
from vigh_agent.core.agent import VighAgent
from vigh_agent.models.provider import BaseProvider, StreamChunk, ToolCall


class MockLLMProvider(BaseProvider):
    """Deterministic Mock LLM Provider for unit testing."""

    def __init__(self, responses: Optional[List[str]] = None):
        super().__init__(name="mock", base_url="http://mock", model="mock-coder")
        self.responses = responses or ["Mocked assistant response"]
        self.call_count = 0
        self.recorded_messages: List[List[Dict[str, Any]]] = []

    def health_check(self) -> bool:
        return True

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": "mock-coder", "name": "Mock Coder", "provider": "mock"}]

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Generator[StreamChunk, None, None]:
        self.recorded_messages.append(messages)
        idx = min(self.call_count, len(self.responses) - 1)
        resp = self.responses[idx]
        self.call_count += 1

        # Yield response in chunks
        words = resp.split(" ")
        for i, word in enumerate(words):
            yield StreamChunk(content=word + (" " if i < len(words) - 1 else ""))


class TestMultiAgentContext(unittest.TestCase):
    """Tests for SharedContext and blackboard memory."""

    def setUp(self):
        self.context = SharedContext(user_request="Build REST API", workspace_root=".")

    def test_plan_and_tasks_lifecycle(self):
        plan = ExecutionPlan(
            summary="API Architecture Plan",
            tasks=[
                TaskItem(id="T1", title="Create models", target_files=["models.py"]),
                TaskItem(id="T2", title="Create endpoints", target_files=["api.py"])
            ],
            target_files=["models.py", "api.py"]
        )
        self.context.set_plan(plan)

        self.assertIsNotNone(self.context.plan)
        self.assertEqual(len(self.context.plan.tasks), 2)
        self.assertEqual(self.context.plan.tasks[0].status, TaskStatus.PENDING)

        # Update task status
        self.context.update_task_status("T1", TaskStatus.IN_PROGRESS)
        self.assertEqual(self.context.plan.tasks[0].status, TaskStatus.IN_PROGRESS)

        self.context.update_task_status("T1", TaskStatus.COMPLETED, result="Created User model")
        self.assertEqual(self.context.plan.tasks[0].status, TaskStatus.COMPLETED)
        self.assertEqual(self.context.plan.tasks[0].result, "Created User model")

    def test_diff_and_modified_files_tracking(self):
        self.context.record_diff("main.py", "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n+print('hello')", "Added hello")
        self.assertIn("main.py", self.context.modified_files)
        self.assertEqual(len(self.context.diffs), 1)
        self.assertEqual(self.context.diffs[0]["path"], "main.py")

    def test_test_report_and_failure_detection(self):
        passed_report = TestReport(success=True, command="pytest", passed_count=5, failed_count=0)
        self.context.add_test_report(passed_report)
        self.assertFalse(self.context.has_critical_issues_or_test_failures())

        failed_report = TestReport(success=False, command="pytest", passed_count=3, failed_count=2, error_traceback="AssertionError: 2 != 3")
        self.context.add_test_report(failed_report)
        self.assertTrue(self.context.has_critical_issues_or_test_failures())

        diagnostics = self.context.get_auto_fix_diagnostics()
        self.assertEqual(len(diagnostics["test_errors"]), 1)
        self.assertIn("AssertionError", diagnostics["test_errors"][0]["traceback"])

    def test_security_report_and_critical_detection(self):
        clean_sec = SecurityReport(clean=True, highest_severity="CLEAN", findings=[])
        self.context.add_security_report(clean_sec)
        self.assertFalse(self.context.has_critical_issues_or_test_failures())

        vuln_sec = SecurityReport(
            clean=False,
            highest_severity="CRITICAL",
            findings=[SecurityFinding(severity="CRITICAL", file="auth.py", line=10, issue="Hardcoded secret key", remediation="Use env var")]
        )
        self.context.add_security_report(vuln_sec)
        self.assertTrue(self.context.has_critical_issues_or_test_failures())

        diagnostics = self.context.get_auto_fix_diagnostics()
        self.assertEqual(len(diagnostics["security_issues"]), 1)
        self.assertEqual(diagnostics["security_issues"][0]["severity"], "CRITICAL")

    def test_review_report_and_score(self):
        review = ReviewReport(score=9, approved=True, strengths=["Modular architecture", "Clean typing"])
        self.context.add_review_report(review)
        self.assertEqual(len(self.context.review_reports), 1)
        self.assertEqual(self.context.review_reports[0].score, 9)

    def test_autofix_history(self):
        attempt = AutoFixAttempt(iteration=1, trigger="test_failure", issues_addressed=["AssertionError"], actions_taken="Fixed math function", result_success=True)
        self.context.add_autofix_attempt(attempt)
        self.assertEqual(len(self.context.autofix_history), 1)

    def test_summary_snapshot(self):
        snap = self.context.get_summary_snapshot()
        self.assertEqual(snap["user_request"], "Build REST API")
        self.assertIn("modified_files", snap)


class TestSpecializedAgents(unittest.TestCase):
    """Tests for specialized agent reasoning and parsing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.session = AgentSession(workspace_path=str(self.workspace))
        self.context = SharedContext(user_request="Build calculator", workspace_root=str(self.workspace))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_planner_agent(self):
        mock_plan_json = """
```json
{
  "summary": "Implement Calculator Module",
  "target_files": ["calc.py"],
  "tasks": [
    {"id": "TASK-1", "title": "Create addition", "target_files": ["calc.py"]},
    {"id": "TASK-2", "title": "Create multiplication", "target_files": ["calc.py"]}
  ],
  "acceptance_criteria": ["All arithmetic operations work accurately"],
  "risk_factors": ["Division by zero"]
}
```
"""
        self.session.provider = MockLLMProvider(responses=[mock_plan_json])
        planner = PlannerAgent(session=self.session, context=self.context)

        events = list(planner.plan("Build calculator"))
        self.assertTrue(any(e.type == "agent_start" for e in events))
        self.assertIsNotNone(self.context.plan)
        self.assertEqual(len(self.context.plan.tasks), 2)
        self.assertEqual(self.context.plan.tasks[0].id, "TASK-1")

    def test_coder_agent(self):
        mock_coder_response = "I have written the calculator in calc.py."
        self.session.provider = MockLLMProvider(responses=[mock_coder_response])
        coder = CoderAgent(session=self.session, context=self.context)

        plan = ExecutionPlan(
            summary="Test plan",
            tasks=[TaskItem(id="T1", title="Write calc.py", target_files=["calc.py"])]
        )
        events = list(coder.execute_plan(plan))
        self.assertTrue(any(e.type == "task_update" for e in events))
        self.assertTrue(any(e.type == "agent_complete" for e in events))

    def test_tester_agent(self):
        mock_tester_response = """
Ran 8 tests in 0.05s
OK (passed=8, failures=0)
All unit tests passed with 100% verification.
"""
        self.session.provider = MockLLMProvider(responses=[mock_tester_response])
        tester = TesterAgent(session=self.session, context=self.context)

        events = list(tester.test())
        self.assertTrue(any(e.type == "test_result" for e in events))
        self.assertEqual(len(self.context.test_reports), 1)
        self.assertTrue(self.context.test_reports[0].success)
        self.assertEqual(self.context.test_reports[0].passed_count, 8)

    def test_reviewer_agent(self):
        mock_review_response = """
Code Review Quality Score: 9/10
Status: APPROVED
Strengths:
- Clean modular structure
- Excellent exception handling
- Proper type annotations
"""
        self.session.provider = MockLLMProvider(responses=[mock_review_response])
        reviewer = ReviewerAgent(session=self.session, context=self.context)

        events = list(reviewer.review())
        self.assertTrue(any(e.type == "review_result" for e in events))
        self.assertEqual(len(self.context.review_reports), 1)
        self.assertEqual(self.context.review_reports[0].score, 9)
        self.assertTrue(self.context.review_reports[0].approved)

    def test_security_agent(self):
        mock_sec_response = """
Security Audit Status: CLEAN
No vulnerabilities, hardcoded credentials, or SQL injection vectors detected.
"""
        self.session.provider = MockLLMProvider(responses=[mock_sec_response])
        security = SecurityAgent(session=self.session, context=self.context)

        events = list(security.audit())
        self.assertTrue(any(e.type == "security_audit" for e in events))
        self.assertEqual(len(self.context.security_reports), 1)
        self.assertTrue(self.context.security_reports[0].clean)


class TestMultiAgentOrchestrator(unittest.TestCase):
    """Tests full MultiAgentOrchestrator workflow, parallelization, and auto-fix."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.session = AgentSession(workspace_path=str(self.workspace))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_orchestrator_pipeline(self):
        mock_responses = [
            # 1. Planner
            """
```json
{
  "summary": "Create Greeter Module",
  "target_files": ["greeter.py"],
  "tasks": [{"id": "TASK-1", "title": "Implement greet function", "target_files": ["greeter.py"]}],
  "acceptance_criteria": ["Returns greeting"],
  "risk_factors": []
}
```
""",
            # 2. Coder
            "Implemented greeter.py successfully.",
            # 3. Tester
            "Ran 3 tests: OK (passed=3, failures=0)",
            # 4. Security
            "Security Status: CLEAN. Zero vulnerabilities.",
            # 5. Reviewer
            "Quality Score: 10/10. Approved.",
            # 6. Synthesis
            "# Greeter Execution Complete\nAll tests passed and security verified."
        ]

        self.session.provider = MockLLMProvider(responses=mock_responses)
        orchestrator = MultiAgentOrchestrator(session=self.session, parallel_verification=False)

        events = list(orchestrator.run_stream("Create greeter module"))
        event_types = [e.type for e in events]

        self.assertIn("phase_start", event_types)
        self.assertIn("agent_start", event_types)
        self.assertIn("test_result", event_types)
        self.assertIn("security_audit", event_types)
        self.assertIn("review_result", event_types)
        self.assertIn("final_response", event_types)
        self.assertIn("done", event_types)

    def test_auto_fix_loop_on_failure(self):
        mock_responses = [
            # 1. Planner
            """
```json
{
  "summary": "Create Math Module",
  "target_files": ["math_mod.py"],
  "tasks": [{"id": "TASK-1", "title": "Implement divide", "target_files": ["math_mod.py"]}],
  "acceptance_criteria": ["Handles division"],
  "risk_factors": []
}
```
""",
            # 2. Coder initial
            "Implemented division.",
            # 3. Tester initial (FAILS!)
            "FAILURES: 1 failed, 0 passed. Traceback: ZeroDivisionError in math_mod.py:5",
            # 4. Security initial
            "Security Status: CLEAN",
            # 5. Reviewer initial
            "Quality Score: 6/10. Needs fix for ZeroDivisionError.",
            # 6. Coder Auto-Fix
            "Fixed ZeroDivisionError by adding check.",
            # 7. Tester Re-Test (PASSES!)
            "Ran 2 tests: OK (passed=2, failures=0)",
            # 8. Security Re-Audit
            "Security Status: CLEAN",
            # 9. Master Synthesis
            "# Execution and Auto-Fix Complete\nFixed ZeroDivisionError and verified."
        ]

        self.session.provider = MockLLMProvider(responses=mock_responses)
        orchestrator = MultiAgentOrchestrator(session=self.session, max_autofix_iterations=1, parallel_verification=False)

        events = list(orchestrator.run_stream("Create math module with division"))
        event_types = [e.type for e in events]

        self.assertIn("autofix_start", event_types)
        self.assertIn("autofix_complete", event_types)
        self.assertEqual(len(orchestrator.context.autofix_history), 1)

    def test_vigh_agent_mode_switch(self):
        mock_responses = [
            """
```json
{"summary": "Test Swarm", "tasks": [{"id": "T1", "title": "Run test"}]}
```
""",
            "Code written",
            "Ran 1 test: OK",
            "Security: CLEAN",
            "Review: 9/10",
            "Final synthesis"
        ]
        self.session.provider = MockLLMProvider(responses=mock_responses)
        agent = VighAgent(session=self.session)

        # Single agent mode
        agent.session.set_mode("single")
        self.assertEqual(agent.session.mode, "single")

        # Multi agent mode
        agent.session.set_mode("multi")
        self.assertEqual(agent.session.mode, "multi")

        events = list(agent.chat_stream("Build small tool", mode="multi"))
        self.assertTrue(len(events) > 0)
        self.assertTrue(any(e.type == "phase_start" for e in events))


if __name__ == "__main__":
    unittest.main()
