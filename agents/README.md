# agents/ - Agent-building foundation (internal)

> Internal foundation for building AI agents in this workspace, captured from the methodology proven on the
> Dona/Elysian assignment. **These are living documents** - update them as we learn. This folder is a
> starting point, not a finished product.

## Read in this order
1. [`how-to-build-an-agent.md`](how-to-build-an-agent.md) - the topic-agnostic playbook. **Start here.**
2. [`agent-prompt-template.md`](agent-prompt-template.md) - structural 8-part template to copy for a new agent.
3. [`building-for-maslul.md`](building-for-maslul.md) - applying the playbook to a Maslul agent.
4. [`examples/dona/`](examples/dona/) - worked examples (3 agents + knowledge, memory, guardrails, tools,
   orchestration, evals). Reference for **structure and principles**, not for copying tone/specifics.

## Golden rules (short version)
- Two responsibilities only: **decide** (via tools) + **communicate**.
- **Grounded, never inventive** (RAG + cite source; no source -> escalate).
- **Bounded** (limits + guardrails + RBAC); **has memory**; **human** for money/legal/safety.
- **Per-client config, not hardcoded.**

## Before building any real agent (rule: every agent, no exceptions)
**Brainstorm first** (use the brainstorming skill) + **research** the best methodology, connections, and
integrations for that specific purpose. We do this for **every** agent we build - properly, not by
copy-paste. The Dona example is one illustration - take structure, not specifics. A different purpose needs
its own tone, knowledge, and integrations.
