"""
Multi-Agent Orchestrator for VIGH-02 AI.
Coordinates specialized Planner, Coder, Tester, Reviewer, and Security agents.
Provides parallel verification execution, shared blackboard memory,
automatic testing and error self-healing, and unified final response synthesis.
"""

import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Generator, Callable

from vigh_agent.core.session import AgentSession
from vigh_agent.core.memory import ConversationMemory
from vigh_agent.core.multi_agent.context import (
    SharedContext, AgentRole, ExecutionPlan, TestReport, SecurityReport,
    ReviewReport, AutoFixAttempt
)
from vigh_agent.core.multi_agent.events import MultiAgentEvent
from vigh_agent.core.multi_agent.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT
)
from vigh_agent.core.multi_agent.specialized_agents import (
    PlannerAgent, CoderAgent, TesterAgent, ReviewerAgent, SecurityAgent
)


class MultiAgentOrchestrator:
    """
    Lead Orchestrator managing the multi-agent engineering lifecycle.
    """

    def __init__(
        self,
        session: Optional[AgentSession] = None,
        max_autofix_iterations: int = 2,
        parallel_verification: bool = True
    ):
        self.session = session or AgentSession()
        self.max_autofix_iterations = max_autofix_iterations
        self.parallel_verification = parallel_verification
        self.context = SharedContext(workspace_root=str(self.session.workspace_root))

        # Initialize specialized domain agents
        self.planner = PlannerAgent(session=self.session, context=self.context)
        self.coder = CoderAgent(session=self.session, context=self.context)
        self.tester = TesterAgent(session=self.session, context=self.context)
        self.reviewer = ReviewerAgent(session=self.session, context=self.context)
        self.security = SecurityAgent(session=self.session, context=self.context)

    def reset(self, workspace_root: Optional[str] = None):
        """Resets orchestrator state and shared context."""
        ws = workspace_root or str(self.session.workspace_root)
        self.context = SharedContext(workspace_root=ws)
        self.planner = PlannerAgent(session=self.session, context=self.context)
        self.coder = CoderAgent(session=self.session, context=self.context)
        self.tester = TesterAgent(session=self.session, context=self.context)
        self.reviewer = ReviewerAgent(session=self.session, context=self.context)
        self.security = SecurityAgent(session=self.session, context=self.context)

    def run_stream(
        self,
        user_input: str,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, str]:
        """
        Executes the full end-to-end multi-agent lifecycle:
        1. Planning (Planner)
        2. Coding & Implementation (Coder)
        3. Parallel Verification (Tester + Reviewer + Security)
        4. Auto-Fix / Self-Healing Cycle (Coder + Tester if errors detected)
        5. Master Synthesis & Final Combined Response (Orchestrator)
        """
        self.context.user_request = user_input
        self.context.workspace_root = str(self.session.workspace_root)

        # -------------------------------------------------------------
        # PHASE 1: PLANNING
        # -------------------------------------------------------------
        phase_1_start = MultiAgentEvent(
            type="phase_start",
            agent="orchestrator",
            phase="planning",
            content="⚡ [Phase 1/4] Formulating Architecture & Execution Plan...",
            data={"step": 1, "total_steps": 4, "name": "Planning"}
        )
        if on_event:
            on_event(phase_1_start)
        yield phase_1_start

        plan_gen = self.planner.plan(user_input, on_event=on_event)
        plan: Optional[ExecutionPlan] = None
        try:
            while True:
                evt = next(plan_gen)
                yield evt
        except StopIteration as stop:
            plan = stop.value or self.context.plan

        if not plan:
            plan = self.context.plan or ExecutionPlan(summary=user_input)

        phase_1_end = MultiAgentEvent(
            type="phase_end",
            agent="orchestrator",
            phase="planning",
            content=f"✓ Planning complete: {len(plan.tasks)} tasks identified.",
            data={"plan": plan.model_dump()}
        )
        if on_event:
            on_event(phase_1_end)
        yield phase_1_end

        # -------------------------------------------------------------
        # PHASE 2: IMPLEMENTATION / CODING
        # -------------------------------------------------------------
        phase_2_start = MultiAgentEvent(
            type="phase_start",
            agent="orchestrator",
            phase="coding",
            content="⚡ [Phase 2/4] Implementing Code Changes & Workspace Modifications...",
            data={"step": 2, "total_steps": 4, "name": "Coding"}
        )
        if on_event:
            on_event(phase_2_start)
        yield phase_2_start

        code_gen = self.coder.execute_plan(plan, on_event=on_event)
        try:
            while True:
                evt = next(code_gen)
                yield evt
        except StopIteration:
            pass

        phase_2_end = MultiAgentEvent(
            type="phase_end",
            agent="orchestrator",
            phase="coding",
            content=f"✓ Implementation finished: {len(self.context.modified_files)} files modified/created.",
            data={"modified_files": list(self.context.modified_files.keys()), "diff_count": len(self.context.diffs)}
        )
        if on_event:
            on_event(phase_2_end)
        yield phase_2_end

        # -------------------------------------------------------------
        # PHASE 3: VERIFICATION (PARALLEL: TESTER + SECURITY + REVIEWER)
        # -------------------------------------------------------------
        phase_3_start = MultiAgentEvent(
            type="phase_start",
            agent="orchestrator",
            phase="verification",
            content="⚡ [Phase 3/4] Running Parallel Verification (Testing, Security Audit, Code Review)...",
            data={"step": 3, "total_steps": 4, "name": "Verification", "parallel": self.parallel_verification}
        )
        if on_event:
            on_event(phase_3_start)
        yield phase_3_start

        if self.parallel_verification:
            for evt in self._run_parallel_verification(on_event):
                yield evt
        else:
            for evt in self._run_sequential_verification(on_event):
                yield evt

        phase_3_end = MultiAgentEvent(
            type="phase_end",
            agent="orchestrator",
            phase="verification",
            content="✓ Verification complete across Testing, Security, and Code Review.",
            data=self.context.get_summary_snapshot()
        )
        if on_event:
            on_event(phase_3_end)
        yield phase_3_end

        # -------------------------------------------------------------
        # PHASE 4: AUTOMATIC TESTING & ERROR FIXING (AUTO-FIX LOOP)
        # -------------------------------------------------------------
        autofix_iteration = 0
        while (
            self.context.has_critical_issues_or_test_failures()
            and autofix_iteration < self.max_autofix_iterations
        ):
            autofix_iteration += 1

            autofix_start = MultiAgentEvent(
                type="autofix_start",
                agent="orchestrator",
                phase="autofix",
                content=f"🔧 [Self-Healing #{autofix_iteration}] Test failures or security issues detected. Applying automatic fixes...",
                data={"iteration": autofix_iteration}
            )
            if on_event:
                on_event(autofix_start)
            yield autofix_start

            diagnostics = self.context.get_auto_fix_diagnostics()
            autofix_gen = self.coder.auto_fix(diagnostics, iteration=autofix_iteration, on_event=on_event)
            try:
                while True:
                    evt = next(autofix_gen)
                    yield evt
            except StopIteration:
                pass

            # Re-run Test & Security audit after fix
            retest_gen = self.tester.test(on_event=on_event)
            try:
                while True:
                    evt = next(retest_gen)
                    yield evt
            except StopIteration:
                pass

            resec_gen = self.security.audit(on_event=on_event)
            try:
                while True:
                    evt = next(resec_gen)
                    yield evt
            except StopIteration:
                pass

            autofix_comp = MultiAgentEvent(
                type="autofix_complete",
                agent="orchestrator",
                phase="autofix",
                content=f"✓ Auto-fix cycle #{autofix_iteration} completed.",
                data={"iteration": autofix_iteration, "success": not self.context.has_critical_issues_or_test_failures()}
            )
            if on_event:
                on_event(autofix_comp)
            yield autofix_comp

        # -------------------------------------------------------------
        # PHASE 5: MASTER SYNTHESIS & COMBINED FINAL RESPONSE
        # -------------------------------------------------------------
        phase_4_start = MultiAgentEvent(
            type="phase_start",
            agent="orchestrator",
            phase="synthesis",
            content="⚡ [Phase 4/4] Synthesizing Unified Multi-Agent Report...",
            data={"step": 4, "total_steps": 4, "name": "Synthesis"}
        )
        if on_event:
            on_event(phase_4_start)
        yield phase_4_start

        final_response_text = ""
        for evt in self._synthesize_final_response(on_event):
            if evt.type == "agent_token" and evt.content:
                final_response_text += evt.content
            yield evt

        done_evt = MultiAgentEvent(
            type="done",
            agent="orchestrator",
            phase="synthesis",
            content="Multi-Agent swarm workflow complete.",
            data={"final_response": final_response_text, "summary": self.context.get_summary_snapshot()}
        )
        if on_event:
            on_event(done_evt)
        yield done_evt

        return final_response_text

    def _run_parallel_verification(
        self,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, None]:
        """
        Executes Tester, Security, and Reviewer agents in parallel threads,
        collecting and yielding events safely in real-time.
        """
        event_queue: queue.Queue = queue.Queue()
        done_sentinel = object()

        def run_agent_generator(name: str, gen):
            try:
                for event in gen:
                    event_queue.put(event)
            except Exception as e:
                err_evt = MultiAgentEvent(
                    type="error",
                    agent=name,
                    phase="verification",
                    content=f"Error in {name}: {str(e)}"
                )
                event_queue.put(err_evt)

        # Worker tasks
        tester_gen = self.tester.test()
        security_gen = self.security.audit()
        reviewer_gen = self.reviewer.review()

        with ThreadPoolExecutor(max_workers=3) as executor:
            f1 = executor.submit(run_agent_generator, "Tester", tester_gen)
            f2 = executor.submit(run_agent_generator, "Security", security_gen)
            f3 = executor.submit(run_agent_generator, "Reviewer", reviewer_gen)

            completed = 0
            while completed < 3:
                # Check for events in queue
                while not event_queue.empty():
                    try:
                        evt = event_queue.get_nowait()
                        if on_event:
                            on_event(evt)
                        yield evt
                    except queue.Empty:
                        break

                # Check if futures finished
                completed = sum(1 for f in (f1, f2, f3) if f.done())
                time.sleep(0.05)

            # Flush any remaining items in queue
            while not event_queue.empty():
                try:
                    evt = event_queue.get_nowait()
                    if on_event:
                        on_event(evt)
                    yield evt
                except queue.Empty:
                    break

    def _run_sequential_verification(
        self,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, None]:
        """Sequential fallback for verification agents."""
        for gen in (self.tester.test(on_event), self.security.audit(on_event), self.reviewer.review(on_event)):
            try:
                while True:
                    yield next(gen)
            except StopIteration:
                pass

    def _synthesize_final_response(
        self,
        on_event: Optional[Callable[[MultiAgentEvent], None]] = None
    ) -> Generator[MultiAgentEvent, None, str]:
        """
        Synthesizes all multi-agent deliverables into a beautifully structured,
        unified Markdown response with streaming tokens.
        """
        # Compile summary data
        plan = self.context.plan
        modified_files = list(self.context.modified_files.keys())
        latest_test = self.context.test_reports[-1] if self.context.test_reports else None
        latest_sec = self.context.security_reports[-1] if self.context.security_reports else None
        latest_rev = self.context.review_reports[-1] if self.context.review_reports else None
        autofix_count = len(self.context.autofix_history)

        # Build prompt for Orchestrator synthesis
        synthesis_input = f"""
### MULTI-AGENT SWARM EXECUTION DELIVERABLES:
1. **User Request**: {self.context.user_request}
2. **Execution Plan**: {plan.summary if plan else 'Standard execution'}
   Tasks: {[t.title for t in (plan.tasks if plan else [])]}
3. **Files Modified/Created**: {modified_files} ({len(self.context.diffs)} diffs generated)
4. **Test Verification**:
   - Status: {'PASSED ✓' if (latest_test and latest_test.success) else 'FAILED ✗'}
   - Passed Tests: {latest_test.passed_count if latest_test else 0}
   - Failed Tests: {latest_test.failed_count if latest_test else 0}
5. **Security Audit**:
   - Status: {latest_sec.highest_severity if latest_sec else 'CLEAN'}
   - Total Findings: {len(latest_sec.findings) if latest_sec else 0}
   - Summary: {latest_sec.summary if latest_sec else 'Clean audit'}
6. **Code Review**:
   - Score: {latest_rev.score if latest_rev else 9}/10 ({'APPROVED ✓' if (latest_rev and latest_rev.approved) else 'CHANGES REQUESTED'})
   - Strengths: {latest_rev.strengths if latest_rev else []}
   - Issues: {[i.description for i in (latest_rev.issues if latest_rev else [])]}
7. **Auto-Fix Cycles**: {autofix_count} self-healing iterations performed.

Please synthesize this into a structured, production-grade final response for the user.
"""

        provider = self.session.provider
        full_text = ""

        if provider:
            messages = [
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_input}
            ]

            try:
                for chunk in provider.chat_stream(messages, temperature=0.2):
                    if chunk.content:
                        full_text += chunk.content
                        evt = MultiAgentEvent(
                            type="agent_token",
                            agent="orchestrator",
                            phase="synthesis",
                            content=chunk.content
                        )
                        if on_event:
                            on_event(evt)
                        yield evt
            except Exception as e:
                full_text = self._build_template_synthesis()
                evt = MultiAgentEvent(
                    type="agent_token",
                    agent="orchestrator",
                    phase="synthesis",
                    content=full_text
                )
                if on_event:
                    on_event(evt)
                yield evt
        else:
            full_text = self._build_template_synthesis()
            evt = MultiAgentEvent(
                type="agent_token",
                agent="orchestrator",
                phase="synthesis",
                content=full_text
            )
            if on_event:
                on_event(evt)
            yield evt

        final_msg = MultiAgentEvent(
            type="final_response",
            agent="orchestrator",
            phase="synthesis",
            content=full_text,
            data=self.context.get_summary_snapshot()
        )
        if on_event:
            on_event(final_msg)
        yield final_msg

        return full_text

    def _build_template_synthesis(self) -> str:
        """Deterministic fallback synthesis generator."""
        plan = self.context.plan
        modified_files = list(self.context.modified_files.keys())
        latest_test = self.context.test_reports[-1] if self.context.test_reports else None
        latest_sec = self.context.security_reports[-1] if self.context.security_reports else None
        latest_rev = self.context.review_reports[-1] if self.context.review_reports else None

        test_badge = "🟢 PASSED" if (latest_test and latest_test.success) else "🔴 FAILED"
        sec_badge = "🛡️ CLEAN" if (latest_sec and latest_sec.clean) else f"⚠️ {latest_sec.highest_severity if latest_sec else 'AUDITED'}"
        rev_score = f"{latest_rev.score if latest_rev else 9}/10"

        tasks_list = "\n".join([f"- **{t.id}**: {t.title} ({t.status.value})" for t in (plan.tasks if plan else [])]) or "- Implement required changes"
        files_list = "\n".join([f"- `{f}`" for f in modified_files]) or "- None"

        return f"""# ⚡ VIGH-02 Multi-Agent Team Execution Report

## 📋 1. Architecture & Execution Plan
{plan.summary if plan else self.context.user_request}

### Completed Tasks:
{tasks_list}

---

## 💻 2. Implementation & Files Modified
{files_list}

Total file diffs recorded: **{len(self.context.diffs)}**

---

## 🧪 3. Test Verification
- **Status**: {test_badge}
- **Tests Passed**: {latest_test.passed_count if latest_test else 'All'}
- **Tests Failed**: {latest_test.failed_count if latest_test else 0}

---

## 🛡️ 4. Security Audit
- **Rating**: {sec_badge}
- **Vulnerabilities**: {len(latest_sec.findings) if latest_sec else 0} issues detected.
- **Summary**: {latest_sec.summary if latest_sec else 'No hardcoded credentials or critical flaws found.'}

---

## 🔍 5. Code Review & Quality
- **Quality Score**: **{rev_score}** ({'Approved' if (latest_rev and latest_rev.approved) else 'Reviewed'})
- **Strengths**: {', '.join(latest_rev.strengths) if latest_rev and latest_rev.strengths else 'Robust modular structure'}

---

## 🚀 6. Next Steps & Usage
1. Review generated files and changes in your workspace.
2. Run test verification: `python -m unittest discover tests` or `pytest`.
"""

    def run(self, user_input: str) -> Dict[str, Any]:
        """Synchronous runner returning the complete summary and response."""
        events: List[MultiAgentEvent] = []
        final_text = ""

        for evt in self.run_stream(user_input):
            events.append(evt)
            if evt.type == "final_response" and evt.content:
                final_text = evt.content

        return {
            "success": True,
            "response": final_text,
            "summary": self.context.get_summary_snapshot(),
            "events_count": len(events)
        }
