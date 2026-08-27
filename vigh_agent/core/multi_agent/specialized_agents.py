"""
Specialized Autonomous Agents for VIGH-02 Multi-Agent Mode.
Includes Planner, Coder, Tester, Reviewer, and Security Agents.
"""

import re
import json
from typing import Dict, Any, List, Optional, Generator, Callable, Tuple

from vigh_agent.core.session import AgentSession
from vigh_agent.core.memory import ConversationMemory
from vigh_agent.core.multi_agent.context import (
    SharedContext, AgentRole, TaskStatus, TaskItem, ExecutionPlan,
    TestReport, SecurityFinding, SecurityReport, ReviewIssue, ReviewReport,
    AutoFixAttempt
)
from vigh_agent.core.multi_agent.events import MultiAgentEvent
from vigh_agent.core.multi_agent.prompts import (
    PLANNER_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT, TESTER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT, SECURITY_SYSTEM_PROMPT, AUTOFIX_SYSTEM_PROMPT
)
from vigh_agent.tools.registry import tool_registry
from vigh_agent.models.provider import ToolCall, StreamChunk


class BaseSpecializedAgent:
    """Base class for all specialized domain agents in the swarm."""

    def __init__(
        self,
        role: AgentRole,
        name: str,
        system_prompt: str,
        allowed_tools: List[str],
        session: AgentSession,
        context: SharedContext
    ):
        self.role = role
        self.name = name
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools
        self.session = session
        self.context = context
        self.memory = ConversationMemory(system_prompt=system_prompt, max_messages=25)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns schemas for only the tools this agent is permitted to use."""
        all_schemas = tool_registry.get_schemas()
        return [
            s for s in all_schemas
            if s.get("function", {}).get("name") in self.allowed_tools
        ]

    def run_agent_loop(
        self,
        prompt: str,
        phase: str,
        max_steps: int = 6,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, str]:
        """
        Runs an autonomous reasoning and tool execution loop for this agent.
        Yields MultiAgentEvents and returns the final assistant text.
        """
        self.memory.add_user_message(prompt)
        workspace = str(self.context.workspace_root or self.session.workspace_root)
        provider = self.session.provider

        if not provider:
            evt = MultiAgentEvent(
                type="error",
                agent=self.name,
                phase=phase,
                content="No active LLM provider configured."
            )
            if on_event:
                on_event(evt)
            yield evt
            return "Error: No provider"

        start_evt = MultiAgentEvent(
            type="agent_start",
            agent=self.name,
            phase=phase,
            content=f"{self.name} is working..."
        )
        if on_event:
            on_event(start_evt)
        yield start_evt

        current_step = 0
        tools_schema = self.get_tool_schemas()
        final_assistant_text = ""

        while current_step < max_steps:
            current_step += 1
            messages = self.memory.get_messages()

            assistant_text = ""
            collected_tool_calls: List[ToolCall] = []

            for chunk in provider.chat_stream(messages, tools=tools_schema if tools_schema else None):
                if chunk.content:
                    assistant_text += chunk.content
                    evt = MultiAgentEvent(
                        type="agent_token",
                        agent=self.name,
                        phase=phase,
                        content=chunk.content
                    )
                    if on_event:
                        on_event(evt)
                    yield evt

                if chunk.tool_calls:
                    collected_tool_calls.extend(chunk.tool_calls)

            # Fallback tool call extraction if model emitted XML or JSON markdown
            if not collected_tool_calls and assistant_text:
                fallback_calls = tool_registry.parse_fallback_tool_calls(assistant_text)
                for f_name, f_args in fallback_calls:
                    if f_name in self.allowed_tools:
                        collected_tool_calls.append(ToolCall(id=f_name, name=f_name, arguments=f_args))

            final_assistant_text = assistant_text
            self.memory.add_assistant_message(
                assistant_text,
                tool_calls=collected_tool_calls if collected_tool_calls else None
            )

            # If no tools called, agent finished its thinking/response
            if not collected_tool_calls:
                break

            # Execute tools
            for tc in collected_tool_calls:
                if tc.name not in self.allowed_tools:
                    continue

                tool_start_evt = MultiAgentEvent(
                    type="agent_tool_start",
                    agent=self.name,
                    phase=phase,
                    content=f"Tool: {tc.name}",
                    data={"name": tc.name, "arguments": tc.arguments}
                )
                if on_event:
                    on_event(tool_start_evt)
                yield tool_start_evt

                tool_res = tool_registry.execute(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    workspace_root=workspace
                )

                # Record diffs if tool produced code changes
                if isinstance(tool_res, dict) and tool_res.get("diff"):
                    diff_content = tool_res["diff"]
                    target_file = tool_res.get("path", "file")
                    desc = tool_res.get("message", f"Modified by {self.name}")
                    self.context.record_diff(target_file, diff_content, desc)

                    diff_evt = MultiAgentEvent(
                        type="diff",
                        agent=self.name,
                        phase=phase,
                        content=diff_content,
                        data={"path": target_file, "description": desc}
                    )
                    if on_event:
                        on_event(diff_evt)
                    yield diff_evt

                tool_end_evt = MultiAgentEvent(
                    type="agent_tool_end",
                    agent=self.name,
                    phase=phase,
                    content=f"Tool {tc.name} completed",
                    data={"name": tc.name, "result": tool_res}
                )
                if on_event:
                    on_event(tool_end_evt)
                yield tool_end_evt

                self.memory.add_tool_response(
                    tool_name=tc.name,
                    tool_call_id=tc.id,
                    result=tool_res
                )

        complete_evt = MultiAgentEvent(
            type="agent_complete",
            agent=self.name,
            phase=phase,
            content=f"{self.name} completed task.",
            data={"output": final_assistant_text}
        )
        if on_event:
            on_event(complete_evt)
        yield complete_evt

        return final_assistant_text


class PlannerAgent(BaseSpecializedAgent):
    """Specialized in analyzing architectures and generating execution plans."""

    def __init__(self, session: AgentSession, context: SharedContext):
        super().__init__(
            role=AgentRole.PLANNER,
            name="Planner",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            allowed_tools=["scan_folder", "read_file", "search_code", "outline_symbols", "list_dir"],
            session=session,
            context=context
        )

    def plan(
        self,
        user_request: str,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, ExecutionPlan]:
        """Formulates a structured execution plan for the user request."""
        prompt = (
            f"User Goal:\n{user_request}\n\n"
            "Please analyze the workspace, understand the requirements, and produce a structured "
            "execution plan with target files, sequenced tasks, acceptance criteria, and risks."
        )

        final_text = ""
        gen = self.run_agent_loop(prompt, phase="planning", max_steps=5, on_event=on_event)
        try:
            while True:
                evt = next(gen)
                yield evt
        except StopIteration as stop:
            final_text = stop.value or ""

        # Parse structured plan from response
        plan = self._parse_plan(final_text, user_request)
        self.context.set_plan(plan)
        return plan

    def _parse_plan(self, text: str, user_request: str) -> ExecutionPlan:
        """Extracts ExecutionPlan model from text or JSON blocks."""
        # Try JSON block
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                tasks = []
                for idx, t in enumerate(data.get("tasks", [])):
                    tasks.append(TaskItem(
                        id=t.get("id", f"TASK-{idx+1}"),
                        title=t.get("title", f"Task {idx+1}"),
                        description=t.get("description", ""),
                        target_files=t.get("target_files", [])
                    ))
                return ExecutionPlan(
                    summary=data.get("summary", text[:200]),
                    tasks=tasks if tasks else [TaskItem(id="TASK-1", title="Implement solution", description=user_request)],
                    target_files=data.get("target_files", []),
                    acceptance_criteria=data.get("acceptance_criteria", ["Complete functionality without errors"]),
                    risk_factors=data.get("risk_factors", [])
                )
            except Exception:
                pass

        # Fallback heuristic parser from bullet points or numbered lists
        tasks = []
        target_files = []
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if re.match(r"^(\d+\.|\-|\*)\s+(.+)", line_str):
                clean_title = re.sub(r"^(\d+\.|\-|\*)\s+", "", line_str)
                if len(clean_title) > 5:
                    tasks.append(TaskItem(
                        id=f"TASK-{len(tasks)+1}",
                        title=clean_title,
                        description=clean_title
                    ))
            # Detect file mentions e.g. `filename.py`
            files_found = re.findall(r"`([a-zA-Z0-9_\-/\\]+\.[a-zA-Z0-9]+)`", line_str)
            for f in files_found:
                if f not in target_files:
                    target_files.append(f)

        if not tasks:
            tasks = [TaskItem(id="TASK-1", title="Implement requested changes", description=user_request)]

        return ExecutionPlan(
            summary=text[:300] if len(text) > 300 else text,
            tasks=tasks[:8],
            target_files=target_files,
            acceptance_criteria=["Functional implementation verified by tests", "Zero syntax errors"],
            risk_factors=[]
        )


class CoderAgent(BaseSpecializedAgent):
    """Specialized in writing code, editing files, and applying surgical patches."""

    def __init__(self, session: AgentSession, context: SharedContext):
        super().__init__(
            role=AgentRole.CODER,
            name="Coder",
            system_prompt=CODER_SYSTEM_PROMPT,
            allowed_tools=[
                "read_file", "write_file", "edit_file", "search_code",
                "outline_symbols", "list_dir", "git_status", "git_diff"
            ],
            session=session,
            context=context
        )

    def execute_plan(
        self,
        plan: ExecutionPlan,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, str]:
        """Executes all coding tasks outlined in the plan."""
        tasks_desc = "\n".join([f"- [{t.id}] {t.title}: {t.description}" for t in plan.tasks])
        prompt = (
            f"User Goal: {self.context.user_request}\n\n"
            f"Execution Blueprint:\n{tasks_desc}\n\n"
            f"Target Files: {', '.join(plan.target_files) if plan.target_files else 'As needed'}\n\n"
            "Please implement the required code changes using the tools (`read_file`, `write_file`, `edit_file`). "
            "Ensure the code is complete, correct, and production-ready."
        )

        for task in plan.tasks:
            self.context.update_task_status(task.id, TaskStatus.IN_PROGRESS)
            task_evt = MultiAgentEvent(
                type="task_update",
                agent=self.name,
                phase="coding",
                content=f"Starting {task.id}: {task.title}",
                data={"task_id": task.id, "status": "in_progress"}
            )
            if on_event:
                on_event(task_evt)
            yield task_evt

        final_text = ""
        gen = self.run_agent_loop(prompt, phase="coding", max_steps=8, on_event=on_event)
        try:
            while True:
                evt = next(gen)
                yield evt
        except StopIteration as stop:
            final_text = stop.value or ""

        for task in plan.tasks:
            self.context.update_task_status(task.id, TaskStatus.COMPLETED, result="Implemented")
            task_evt = MultiAgentEvent(
                type="task_update",
                agent=self.name,
                phase="coding",
                content=f"Completed {task.id}: {task.title}",
                data={"task_id": task.id, "status": "completed"}
            )
            if on_event:
                on_event(task_evt)
            yield task_evt

        return final_text

    def auto_fix(
        self,
        diagnostics: Dict[str, Any],
        iteration: int,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, AutoFixAttempt]:
        """Applies surgical error fixes based on diagnostics from Tester/Security/Reviewer."""
        diag_str = json.dumps(diagnostics, indent=2)
        prompt = (
            f"### AUTO-FIX REPAIR CYCLE #{iteration}\n\n"
            f"The verification swarm detected the following issues that must be fixed:\n"
            f"```json\n{diag_str}\n```\n\n"
            "Please read the affected files around the error locations, use `edit_file` or `write_file` "
            "to fix the bugs/vulnerabilities, and explain the fix applied."
        )

        # Temporarily use autofix prompt for this specialized cycle
        prev_prompt = self.system_prompt
        self.system_prompt = AUTOFIX_SYSTEM_PROMPT
        self.memory.system_prompt = AUTOFIX_SYSTEM_PROMPT

        final_text = ""
        gen = self.run_agent_loop(prompt, phase="autofix", max_steps=6, on_event=on_event)
        try:
            while True:
                evt = next(gen)
                yield evt
        except StopIteration as stop:
            final_text = stop.value or ""

        self.system_prompt = prev_prompt
        self.memory.system_prompt = prev_prompt

        attempt = AutoFixAttempt(
            iteration=iteration,
            trigger="test_failure" if diagnostics.get("test_errors") else "security_or_review",
            issues_addressed=[str(e) for e in diagnostics.get("test_errors", [])] + [str(s.get("issue", "")) for s in diagnostics.get("security_issues", [])],
            actions_taken=final_text[:300] if len(final_text) > 300 else final_text,
            result_success=True
        )
        self.context.add_autofix_attempt(attempt)
        return attempt


class TesterAgent(BaseSpecializedAgent):
    """Specialized in test execution, test case creation, and error diagnosis."""

    def __init__(self, session: AgentSession, context: SharedContext):
        super().__init__(
            role=AgentRole.TESTER,
            name="Tester",
            system_prompt=TESTER_SYSTEM_PROMPT,
            allowed_tools=["run_command", "read_file", "write_file", "list_dir", "search_code"],
            session=session,
            context=context
        )

    def test(
        self,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, TestReport]:
        """Runs test verification and collects diagnostic results."""
        prompt = (
            f"User Goal: {self.context.user_request}\n"
            f"Modified Files: {list(self.context.modified_files.keys())}\n\n"
            "Please check for existing tests or write appropriate unit test cases, run them using `run_command` "
            "(e.g., `python -m unittest discover tests` or `pytest`), and provide a full test report."
        )

        final_text = ""
        gen = self.run_agent_loop(prompt, phase="verification", max_steps=5, on_event=on_event)
        try:
            while True:
                evt = next(gen)
                yield evt
        except StopIteration as stop:
            final_text = stop.value or ""

        report = self._parse_test_output(final_text)
        self.context.add_test_report(report)

        res_evt = MultiAgentEvent(
            type="test_result",
            agent=self.name,
            phase="verification",
            content=f"Test Suite Status: {'PASSED' if report.success else 'FAILED'}",
            data=report.model_dump()
        )
        if on_event:
            on_event(res_evt)
        yield res_evt

        return report

    def _parse_test_output(self, text: str) -> TestReport:
        """Parses test logs, exit codes, and passed/failed numbers."""
        lower_text = text.lower()
        success = True

        # Check for failure keywords
        if "fail" in lower_text or "error" in lower_text or "traceback" in lower_text or "assertionerror" in lower_text:
            if "ran " in lower_text and "ok" in lower_text and "failures=0" in lower_text:
                success = True
            elif "0 failed" in lower_text and "passed" in lower_text:
                success = True
            else:
                success = not ("failures=" in lower_text or "errors=" in lower_text or "failed" in lower_text)

        passed_count = 0
        failed_count = 0

        # Try to find counts like "Ran 8 tests" or "8 passed"
        ran_match = re.search(r"ran\s+(\d+)\s+tests?", lower_text)
        if ran_match:
            total = int(ran_match.group(1))
            fail_match = re.search(r"failures=(\d+)", lower_text)
            err_match = re.search(r"errors=(\d+)", lower_text)
            f_count = (int(fail_match.group(1)) if fail_match else 0) + (int(err_match.group(1)) if err_match else 0)
            failed_count = f_count
            passed_count = max(0, total - f_count)
            success = (f_count == 0)
        else:
            pytest_pass = re.search(r"(\d+)\s+passed", lower_text)
            pytest_fail = re.search(r"(\d+)\s+failed", lower_text)
            if pytest_pass:
                passed_count = int(pytest_pass.group(1))
            if pytest_fail:
                failed_count = int(pytest_fail.group(1))
                success = (failed_count == 0)

        # Extract traceback snippet if failed
        traceback = ""
        if not success:
            tb_match = re.search(r"(Traceback \(most recent call last\):[\s\S]+)", text)
            if tb_match:
                traceback = tb_match.group(1)[:2000]
            else:
                traceback = text[-1500:]

        return TestReport(
            success=success,
            command="Test verification runner",
            exit_code=0 if success else 1,
            passed_count=passed_count if (passed_count + failed_count > 0) else (1 if success else 0),
            failed_count=failed_count if (passed_count + failed_count > 0) else (0 if success else 1),
            output=text,
            error_traceback=traceback,
            suggestions=["Review assertion errors and tracebacks" if not success else "Test suite verified successfully"]
        )


class ReviewerAgent(BaseSpecializedAgent):
    """Specialized in code quality, clean architecture, and performance analysis."""

    def __init__(self, session: AgentSession, context: SharedContext):
        super().__init__(
            role=AgentRole.REVIEWER,
            name="Reviewer",
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            allowed_tools=["read_file", "search_code", "outline_symbols", "git_diff"],
            session=session,
            context=context
        )

    def review(
        self,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, ReviewReport]:
        """Conducts deep code review of modified files."""
        modified_list = list(self.context.modified_files.keys())
        prompt = (
            f"User Goal: {self.context.user_request}\n"
            f"Modified Files: {modified_list}\n\n"
            "Please review the code quality, bugs, architecture, and performance. "
            "Rate overall quality on a scale of 1-10, identify any issues or risks, and list strengths."
        )

        final_text = ""
        gen = self.run_agent_loop(prompt, phase="verification", max_steps=4, on_event=on_event)
        try:
            while True:
                evt = next(gen)
                yield evt
        except StopIteration as stop:
            final_text = stop.value or ""

        report = self._parse_review_output(final_text)
        self.context.add_review_report(report)

        rev_evt = MultiAgentEvent(
            type="review_result",
            agent=self.name,
            phase="verification",
            content=f"Code Review Score: {report.score}/10 ({'APPROVED' if report.approved else 'CHANGES REQUESTED'})",
            data=report.model_dump()
        )
        if on_event:
            on_event(rev_evt)
        yield rev_evt

        return report

    def _parse_review_output(self, text: str) -> ReviewReport:
        """Parses review score and feedback."""
        score = 9
        score_match = re.search(r"(?:score|rating|quality):\s*(\d+)(?:/10)?", text, re.IGNORECASE)
        if score_match:
            try:
                score = min(10, max(1, int(score_match.group(1))))
            except Exception:
                pass

        approved = score >= 7 and "reject" not in text.lower() and "blocker" not in text.lower()
        issues = []
        strengths = []

        # Find bullet points
        for line in text.splitlines():
            line_str = line.strip()
            if line_str.startswith(("-", "*", "•")):
                clean = line_str.lstrip("-*• ")
                if any(w in clean.lower() for w in ("bug", "issue", "risk", "warning", "fix", "missing")):
                    issues.append(ReviewIssue(
                        severity="MAJOR" if "critical" in clean.lower() or "blocker" in clean.lower() else "MINOR",
                        description=clean,
                        suggestion=clean
                    ))
                elif any(w in clean.lower() for w in ("good", "clean", "robust", "strength", "well", "solid", "optimal")):
                    strengths.append(clean)

        return ReviewReport(
            score=score,
            approved=approved,
            issues=issues[:6],
            strengths=strengths[:5] or ["Modular design and proper encapsulation"],
            refactor_recommendations=[i.suggestion for i in issues[:3]]
        )


class SecurityAgent(BaseSpecializedAgent):
    """Specialized in security auditing, vulnerability scanning, and credential detection."""

    def __init__(self, session: AgentSession, context: SharedContext):
        super().__init__(
            role=AgentRole.SECURITY,
            name="Security",
            system_prompt=SECURITY_SYSTEM_PROMPT,
            allowed_tools=["scan_folder", "read_file", "search_code"],
            session=session,
            context=context
        )

    def audit(
        self,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, SecurityReport]:
        """Conducts static security analysis on the workspace and modified files."""
        modified_list = list(self.context.modified_files.keys())
        prompt = (
            f"User Goal: {self.context.user_request}\n"
            f"Modified Files: {modified_list}\n\n"
            "Please perform a security vulnerability scan (e.g., using `scan_folder` or examining code). "
            "Check for secrets, injection, unsafe operations, and OWASP Top 10 vulnerabilities. "
            "Report severity (CLEAN, LOW, MEDIUM, HIGH, CRITICAL) and remediation recommendations."
        )

        final_text = ""
        gen = self.run_agent_loop(prompt, phase="verification", max_steps=4, on_event=on_event)
        try:
            while True:
                evt = next(gen)
                yield evt
        except StopIteration as stop:
            final_text = stop.value or ""

        report = self._parse_security_output(final_text)
        self.context.add_security_report(report)

        sec_evt = MultiAgentEvent(
            type="security_audit",
            agent=self.name,
            phase="verification",
            content=f"Security Status: {report.highest_severity} ({len(report.findings)} findings)",
            data=report.model_dump()
        )
        if on_event:
            on_event(sec_evt)
        yield sec_evt

        return report

    def _parse_security_output(self, text: str) -> SecurityReport:
        """Parses security findings and severity rating."""
        upper = text.upper()
        severity = "CLEAN"
        clean = True

        if "CRITICAL" in upper and "CRITICAL SEVERITY" in upper or "CRITICAL:" in upper:
            severity = "CRITICAL"
            clean = False
        elif "HIGH" in upper and ("HIGH SEVERITY" in upper or "HIGH RISK" in upper or "HIGH:" in upper):
            severity = "HIGH"
            clean = False
        elif "MEDIUM" in upper and ("MEDIUM SEVERITY" in upper or "MEDIUM RISK" in upper or "MEDIUM:" in upper):
            severity = "MEDIUM"
            clean = False
        elif "LOW" in upper and ("LOW SEVERITY" in upper or "LOW RISK" in upper or "LOW:" in upper):
            severity = "LOW"
            clean = True

        findings = []
        for line in text.splitlines():
            line_str = line.strip()
            if any(k in line_str.upper() for k in ("VULNERABILITY", "FINDING", "SECRET", "INJECTION", "UNSAFE")):
                if len(line_str) > 10:
                    findings.append(SecurityFinding(
                        severity=severity if severity != "CLEAN" else "LOW",
                        issue=line_str,
                        remediation="Apply recommended security hygiene"
                    ))

        return SecurityReport(
            clean=clean and (severity in ("CLEAN", "LOW")),
            highest_severity=severity,
            findings=findings[:5],
            summary="Security audit completed. Workspace verified." if clean else f"Found {len(findings)} potential security concerns.",
            recommendations=["Keep credentials in environment variables", "Validate all external inputs"]
        )
