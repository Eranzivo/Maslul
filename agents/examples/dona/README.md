# Dona - Worked Examples

> The actual agent artifacts from the Dona project (three customer-facing agents for an Israeli real-estate
> company), copied here as **reference examples**. The website, PDF, and build tooling were intentionally
> left out - only the agent-building substance is here.
>
> Use these for **structure and principles, not for copying.** Dona's agents are very specific - e.g. the
> "בדק בית" (home-inspection) agent has its own warm service tone and its own domain. A different agent
> needs its own tone, knowledge, and integrations. (Most files are in Hebrew, as the original was.)

## What's here
- `methodology.md` - 8-part structured prompting + the 3 prompt layers.
- `step1-context-gathering-example.md` - how the client's business and customer journey were mapped.
- `step2-research-example.md` - domain research with sources + verification flags.
- `agent-1-bedek-bayit.system-prompt.md` / `agent-2-legal-contracts...` / `agent-3-contractor-field...` -
  the three full 8-part System Prompts.
- `knowledge-*.md` - the RAG knowledge bases (each entry with source + version).
- `guardrails-permissions-rbac.md`, `guardrails-escalation-policy.md`, `guardrails-no-hallucination.md`.
- `tool-calling-logic.md` - tool definitions, read vs write, confirm-before-write.
- `memory-model-6-layers.md`, `memory-session-policy.md`, `memory-company-profile-example.md`.
- `orchestration-*.md` - orchestrator, intent routing, language, compliance, supervisor, observability.
- `evals-adversarial.md`, `evals-test-conversations.md`.
