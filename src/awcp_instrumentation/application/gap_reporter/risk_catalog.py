"""
Default governance risk catalog.

Each ``HookCategory`` maps to a ``(GovernanceRisk, GovernanceRecommendation)``
pair that reflects standard AWCP governance policy.

This catalog is intentionally decoupled from the reporter implementation so
that organisations can provide their own severity calibrations by injecting a
custom ``RiskCatalog`` into ``GovernanceGapReporter``.

Nothing in this module generates code.  ``instrumentation_hint`` values are
natural-language descriptions that the LLM Patch Generator will interpret.
"""
from __future__ import annotations

from typing import Dict, Tuple

from awcp_instrumentation.application.gap_reporter.models import (
    GovernanceRecommendation,
    GovernanceRisk,
    RiskSeverity,
)
from awcp_instrumentation.domain.enums.hook_category import HookCategory


# Type alias: maps each category to (risk, recommendation).
RiskCatalog = Dict[HookCategory, Tuple[GovernanceRisk, GovernanceRecommendation]]


DEFAULT_RISK_CATALOG: RiskCatalog = {
    HookCategory.TASK_STARTED: (
        GovernanceRisk(
            severity=RiskSeverity.HIGH,
            description="No hook fires when a task begins; task lifecycle is invisible to governance.",
            impact=(
                "Operators cannot track when tasks start, which agents are active, or "
                "whether tasks are being dispatched correctly. Debugging task attribution "
                "requires log archaeology rather than structured event data."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP task_started hook at the entry point of every task handler.",
            rationale=(
                "Task lifecycle observability is a baseline AWCP governance requirement. "
                "Without a task_started event the audit trail is incomplete and incident "
                "timelines cannot be reconstructed."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.task_started(task_id, agent_name, **context) at the "
                "very beginning of each task handler, before any business logic runs. "
                "Include task_id and agent_name in every call."
            ),
            priority=2,
        ),
    ),

    HookCategory.TASK_COMPLETED: (
        GovernanceRisk(
            severity=RiskSeverity.HIGH,
            description="No hook fires when a task completes; successful outcomes are not recorded.",
            impact=(
                "Governance dashboards cannot report task throughput or success rates. "
                "Compliance auditors cannot confirm that tasks finished cleanly. "
                "Task duration cannot be computed without paired start/complete events."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP task_completed hook at every successful task exit point.",
            rationale=(
                "Paired task_started / task_completed events are required for lifecycle "
                "tracking, SLA monitoring, and audit completeness."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.task_completed(task_id, result_summary, **context) at "
                "each successful return point in the task handler. Pass the same task_id "
                "used in the corresponding task_started call."
            ),
            priority=2,
        ),
    ),

    HookCategory.TASK_FAILED: (
        GovernanceRisk(
            severity=RiskSeverity.CRITICAL,
            description="No hook fires when a task fails; failures are silent to the governance layer.",
            impact=(
                "Failed tasks go unrecorded until a human notices missing output. "
                "Root-cause analysis must rely on raw exception traces rather than "
                "structured failure events. Repeated failures cannot trigger automated alerts."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP task_failed hook in every exception handler and early-exit path.",
            rationale=(
                "Task failure events are critical governance signals. They drive alerting, "
                "retry policies, and incident response. Without them, failures are invisible "
                "to the platform."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.task_failed(task_id, error_type, error_message, **context) "
                "inside every except block and at each non-success return path. Include the "
                "exception type name and a short description."
            ),
            priority=1,
        ),
    ),

    HookCategory.LLM_CALL: (
        GovernanceRisk(
            severity=RiskSeverity.CRITICAL,
            description="LLM calls are not instrumented; prompt content and model responses are unaudited.",
            impact=(
                "Sensitive prompts or model outputs may leave the system without being "
                "recorded. Policy violations inside prompts cannot be detected. "
                "Cost attribution by LLM call is impossible without per-call events."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP llm_call hook before every LLM invocation.",
            rationale=(
                "LLM call hooks are the primary mechanism for prompt auditing, cost tracking, "
                "and PII detection. They are mandatory in regulated environments."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.llm_call(model, prompt_preview, **context) immediately "
                "before every call to an LLM client. Do not include the full prompt in the "
                "hook payload if it may contain PII; use a redacted summary instead."
            ),
            priority=1,
        ),
    ),

    HookCategory.SYNTHESIZE: (
        GovernanceRisk(
            severity=RiskSeverity.HIGH,
            description="Synthesis steps are not instrumented; final-answer construction is untracked.",
            impact=(
                "The governance layer cannot observe how the agent assembles its final "
                "answer from retrieved evidence. Hallucination risks at synthesis time "
                "cannot be monitored or mitigated by downstream hooks."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP synthesize hook at the start of each answer-synthesis step.",
            rationale=(
                "Synthesis is the highest-risk step in RAG and agentic workflows. "
                "Instrumenting it enables hallucination monitoring, citation checking, "
                "and quality gate enforcement."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.synthesize(input_count, output_length, **context) at the "
                "beginning of the synthesis function, after retrieving supporting evidence "
                "but before generating the final response."
            ),
            priority=2,
        ),
    ),

    HookCategory.TOOL_CALL: (
        GovernanceRisk(
            severity=RiskSeverity.CRITICAL,
            description="Tool invocations are not instrumented; external side-effects are unrecorded.",
            impact=(
                "The agent can call external tools (APIs, databases, file systems) without "
                "any governance record. Unauthorised or erroneous tool calls cannot be "
                "detected, blocked, or audited after the fact."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP tool_call hook before every external tool invocation.",
            rationale=(
                "Tool calls represent the agent's interface with the outside world. "
                "They must be instrumented for policy enforcement, rate limiting, and "
                "audit completeness. This is a hard AWCP governance requirement."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.tool_call(tool_name, tool_input_summary, **context) "
                "immediately before invoking any external tool. The hook must fire before "
                "the tool executes so that a policy check can block the call if needed."
            ),
            priority=1,
        ),
    ),

    HookCategory.WEB_SEARCH: (
        GovernanceRisk(
            severity=RiskSeverity.HIGH,
            description="Web search calls are not instrumented; retrieval queries are unaudited.",
            impact=(
                "Search queries may leak sensitive context to external search providers "
                "without any governance record. The content retrieved cannot be inspected "
                "for relevance or safety before being fed into the LLM."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP web_search hook before every retrieval or web search call.",
            rationale=(
                "Web search instrumentation enables query auditing, result filtering, and "
                "data-provenance tracking. It is required when agents perform retrieval "
                "over external or user-controlled content."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.web_search(query, results_count, **context) immediately "
                "before the search client is invoked. Pass the raw query so that policy "
                "hooks can inspect or redact it."
            ),
            priority=2,
        ),
    ),

    HookCategory.TOKEN_USAGE: (
        GovernanceRisk(
            severity=RiskSeverity.MEDIUM,
            description="Token consumption is not tracked; cost and quota management is blind.",
            impact=(
                "The platform cannot enforce per-agent or per-task token budgets. "
                "Runaway agents may exhaust shared quota without warning. "
                "Cost attribution across teams or tenants is impossible."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP token_usage hook after each LLM response to record token counts.",
            rationale=(
                "Token usage events are the foundation of cost governance. Without them "
                "budgets cannot be enforced, anomalies cannot be detected, and chargeback "
                "reports cannot be generated."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.token_usage(prompt_tokens, completion_tokens, total_tokens, "
                "**context) immediately after receiving each LLM response. Read the token "
                "counts from the response object's usage field."
            ),
            priority=3,
        ),
    ),

    HookCategory.BUDGET_WARN: (
        GovernanceRisk(
            severity=RiskSeverity.HIGH,
            description="No early warning fires when token usage approaches the budget threshold.",
            impact=(
                "Agents consume budget silently until it is exhausted. There is no "
                "opportunity to reduce scope, switch to a cheaper model, or notify "
                "operators before the hard budget limit is hit."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP budget_warn hook when cumulative token usage exceeds the warning threshold.",
            rationale=(
                "Budget warnings give operators and the agent itself an opportunity to "
                "adapt before a hard budget stop. They are a required escalation step "
                "between normal operation and budget exhaustion."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.budget_warn(used_ratio, limit, agent_name, **context) "
                "when cumulative token or cost usage crosses the warning threshold "
                "(typically 80 % of the configured budget). Include used_ratio as a "
                "float between 0 and 1."
            ),
            priority=2,
        ),
    ),

    HookCategory.BUDGET_EXHAUSTED: (
        GovernanceRisk(
            severity=RiskSeverity.CRITICAL,
            description="No hook fires when the agent exhausts its budget; hard stops are unrecorded.",
            impact=(
                "Budget exhaustion events are not captured in the audit trail. "
                "Downstream systems receive no structured signal that the agent stopped "
                "due to budget constraints rather than an error. Quota violations cannot "
                "be tracked or reported to cost-governance stakeholders."
            ),
        ),
        GovernanceRecommendation(
            action="Emit an AWCP budget_exhausted hook immediately when the agent hits its budget limit.",
            rationale=(
                "Budget exhaustion is a governance-critical event. It must be recorded "
                "so that platform operators can enforce quotas, trigger alerts, and "
                "attribute costs to the correct team or task."
            ),
            instrumentation_hint=(
                "Call awcp_hooks.budget_exhausted(used_ratio, agent_name, **context) as "
                "the first action inside the budget-exhaustion handler. Set used_ratio to "
                "1.0 (or the actual overage ratio) and include the agent name and task id."
            ),
            priority=1,
        ),
    ),
}
