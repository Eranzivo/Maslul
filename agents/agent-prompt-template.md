# Agent System Prompt - Structural Template

> **Status: living document.** This is a STRUCTURE, not a finished prompt. Every `[...]` is a decision to
> make for the specific agent's purpose. **Do not copy tone or specifics from the Dona examples** - they are
> one illustration (a very specific "בדק בית" home-inspection agent with its own warm-service tone). A
> different purpose needs its own tone, knowledge, and integrations.
>
> **Do this before filling the template in:**
> 1. **Brainstorm** (use the brainstorming skill): purpose, users, success criteria, single vs multi-agent.
> 2. **Research** the best methodology for this *kind* of agent, the domain facts (with sources), and the
>    required **connections/integrations** (which CRM/DB/messaging/APIs, auth, data sensitivity).
> 3. Read [`how-to-build-an-agent.md`](how-to-build-an-agent.md) and apply the 6 invariants + the "laws".
> 4. Keep this filled copy updated as the agent evolves (it is a living doc too).

---

## Quick spec (fill this before writing the prompt)

| Field | Decision |
|---|---|
| Agent name / purpose | [...] |
| Primary users | [...] |
| Channel(s) (WhatsApp / web chat / internal / ...) | [...] |
| Single agent, or part of a multi-agent system? | [...] |
| Tone / register (research-appropriate, NOT assumed) | [...] |
| Knowledge sources for RAG (with owners) | [...] |
| Integrations / connections needed | [CRM? DB? messaging? booking? an internal API? auth?] |
| Write actions (need confirm / human approval) | [...] |
| Escalation targets (money / legal / safety / edge) | [...] |
| Success metrics (KPIs) | [...] |
| Data sensitivity / what must NOT leave the system | [...] |

---

## The 8-part System Prompt (fill each part)

```text
# 1. Role / Persona
[Who the agent is and its expertise. The voice/tone appropriate to THIS purpose - research it, do not assume.
State the invariant: "two responsibilities only - decide via tools, and communicate".]

# 2. Objective
[The single outcome the agent drives toward.]

# 3. Context
[Why it matters here: the reputation / risk / cost of an error in this domain. This adds reliability.]

# 4. SOP (numbered work process)
1. [Understand the request; identify who is asking (for permission scoping).]
2. [Ask for any missing required fields - all of them, in ONE batched message.]
3. [Safety / validity check for this domain.]
4. [Retrieve relevant knowledge (RAG) - always with source + version.]
5. [Answer / act, OR escalate if unsure or out of bounds.]
6. [Before any write action: ensure ALL fields are complete (complete-before-write).]
7. [Summarize what was done + next step; persist the relevant facts to memory.]

# 5. Instructions / Rules
- Tone & answer format: [research-appropriate to purpose]
- Allowed: [...]
- Forbidden / hard limits: [...]
- Missing info: ask for everything missing in one batched message (no drip-feeding).
- Grounding: answer only from approved sources with source + version; no source -> "no verified
  information" + escalate. Never quote facts from memory.
- Memory: [what to remember for continuity; what NOT to store; data isolation per user/tenant].
- Guardrails: [domain-specific input/output rules; fail-safe = stop + escalate when unsure].

# 6. Tools & Subagents
[For each tool: when to call, input, output. Mark READ (free) vs WRITE (confirm-before-write).
List the integrations/connections this agent uses (CRM/DB/messaging/API). Define handoff targets.]

# 7. Examples (input -> behavior)
[2-4 representative cases, including: a normal case, a missing-info case, and an escalation case.]

# 8. Notes
[Important reminders + escalation triggers (money / legal / safety / repeat-contact). What is NEVER decided
by the agent.]
```

---

## Living-doc changelog
- [YYYY-MM-DD] Created from template for `[agent name]`.
