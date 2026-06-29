# How to Build a Great Agent (for any topic)

> A reusable, topic-agnostic playbook. It distills the methodology proven on the Dona project
> (3 customer-facing agents for an Israeli real-estate company) into steps any future session can
> follow to build a strong agent - including one for Maslul itself. Worked examples live in
> [`examples/dona/`](examples/dona/). To apply this specifically to Maslul, read
> [`building-for-maslul.md`](building-for-maslul.md). To start a new agent, copy
> [`agent-prompt-template.md`](agent-prompt-template.md).

> **Status: living document.** Update it as we learn; it is a foundation, not gospel.
>
> **Before building any real agent (do this first):** invoke the **brainstorming skill** to fit the agent to
> its purpose and to these principles, and **research the best methodology, connections, and integrations**
> for that specific purpose. The Dona examples are **one illustration** (a very specific home-inspection
> agent with its own warm-service tone) - take the **structure and principles**, not the specifics. A
> different purpose needs its own tone, its own knowledge, and its own integrations.

---

## 0. What a "great agent" actually is

An agent is **not** a chatbot and **not** a prompt. It is a system that **decides and acts**, bounded by
clear rules. The whole playbook rests on a few invariants:

- **Two responsibilities only:** every agent (1) **decides** (by calling tools) and (2) **communicates**.
  It does not "run business logic" in its head. This keeps it predictable and testable.
- **Grounded, never inventive:** facts come from an approved knowledge source with a citation. No source -
  it says "I don't have verified information" and escalates. The anti-hallucination discipline is the
  product, not a nice-to-have.
- **Bounded:** explicit limits per domain (what it may/may not do), enforced by guardrails and permissions.
- **Has memory:** it remembers the user/context across turns and sessions, so it never re-asks.
- **Knows when to step back:** money, legal, and safety decisions go to a human (human-in-the-loop).
- **Configured per client, not hardcoded:** the domain logic lives in config/knowledge, so a new client
  is an onboarding exercise, not a rewrite.

If you keep these six in mind, every other choice follows.

---

## 1. The architecture (5 layers)

Think of any agent system as five layers. A single-agent system collapses some of them, but the mental
model is the same.

| Layer | What it does | Key artifacts |
|---|---|---|
| **1. Orchestration** | Detects language + intent, routes to the right agent, manages handoffs and shared services | router/intent, orchestrator |
| **2. Specialized Agents** | The experts. Each has a focused System Prompt and a small toolset | the 8-part prompts |
| **3. Memory & Data** | Persistent state outside the model: company facts, per-user facts, conversation, open issues | memory model, namespaces |
| **4. Integration / Tools** | How the agent acts on the world: knowledge search, CRM/DB writes, messaging, booking | tool definitions |
| **5. Governance & Observability** | Guardrails, permissions (RBAC), escalation/supervisor, logging, evals | guardrails, supervisor, evals |

**Single agent vs multi-agent:** use multiple agents when the domains have **different rules or different
risk** (e.g. a legal agent that must say "info only" vs a field agent that can act). Use one agent when the
scope is narrow. Multi-agent buys you focus, per-domain guardrails, and easy maintenance; the cost is an
orchestration layer.

---

## 2. The build process, step by step

This is the order to actually build in. Steps 1-2 are research; 3-11 are construction; 12-13 are hardening.

| # | Step | What you produce | Why it matters |
|---|---|---|---|
| 1 | **Understand the business** | Who the users are, the customer journey, the brand voice, the real touchpoints | A tailored solution, not a generic one. See `examples/dona/step1-context-gathering-example.md` |
| 2 | **Research the domain** | A facts file with sources + verification flags for anything uncertain | The grounding source of truth. See `step2-research-example.md` |
| 3 | **Choose the architecture** | Single vs multi-agent; the layer map | Right structure for the risk profile |
| 4 | **Define each agent** | A System Prompt per agent using the 8-part structure (section 3) | Predictable, reproducible behavior |
| 5 | **Build the knowledge base (RAG)** | Approved documents, chunked, with source + version | Anti-hallucination (section 5) |
| 6 | **Design memory** | What is remembered, at what scope, in what namespace (section 6) | Continuity; never re-ask |
| 7 | **Set permissions (RBAC)** | Who sees what, who may do what, where human approval is required | Data isolation + safety |
| 8 | **Define tools** | A small, well-described toolset; read vs write; confirm-before-write (section 7) | The agent can act, safely |
| 9 | **Add guardrails** | Input/output filters, disclaimers, fail-safe behavior (section 8) | Safety and policy |
| 10 | **Wire orchestration** | Language detect, intent routing, handoff payloads | The user gets one seamless conversation |
| 11 | **Add a supervisor / escalation** | Triggers and routes for money/legal/safety/edge cases | Human-in-the-loop |
| 12 | **Write evals** | Normal + **adversarial** test conversations (section 9) | Prove it holds under pressure |
| 13 | **Observability + iterate** | Logging, KPIs, then tune on real data (section 10) | Improve from reality, not guesses |

> Reusable checklist version of this is at the bottom of the file.

---

## 3. The agent prompt: 8-part structured prompting

Write each agent's System Prompt as a **structured spec**, not a conversational paragraph. A structured
prompt reduces variance, is testable and reproducible, and "gets it right the first time" without a human
correcting every step. The eight parts, in fixed order:

1. **Role / Persona** - who the agent is, the brand voice, and the "two responsibilities only" framing.
2. **Objective** - the single outcome it drives toward.
3. **Context** - why the task matters (reputation, risk of error). This adds reliability.
4. **SOP** - a numbered work process, including clarifying questions and a safety check.
5. **Instructions / Rules** - tone, answer format, allowed vs forbidden (limits), missing-info handling,
   guardrails, memory rules.
6. **Tools & Subagents** - each tool: when to call, input, output, and handoff targets.
7. **Examples** - input -> behavior pairs that demonstrate the SOP.
8. **Notes** - "important" reminders and escalation triggers.

Three prompt layers to keep distinct: **System** (the stable spec above), **Input** (the user turn), and
**Action** (the tool call the model emits). See `examples/dona/methodology.md` for the full treatment.

---

## 4. Core principles (the "laws")

These are the non-negotiables. Quote them when justifying a design choice.

- **Grounding / anti-hallucination:** answer only from approved sources with source + version; no source ->
  "no verified information" + escalate. Apply the same honesty to your own work: present only what you built.
- **Relevant-only:** pull just the knowledge/memory the turn needs. Don't inflate the context window.
- **Decide vs execute:** the agent emits a structured request; your code executes it. Never let the model
  "pretend" to have done something.
- **Complete-before-write:** before a write action (open ticket, draft, booking), gather **all** required
  fields and ask for any missing ones in **one batched message**, so the action is complete on first try.
  This shortens SLA and kills back-and-forth.
- **Fail-safe:** when unsure, stop and escalate, never guess.
- **Per-client config, not hardcoded:** business logic belongs in tenant config/knowledge. (This is already
  Maslul's rule: scheduling logic is tenant config, never a default.)
- **Data isolation:** every memory/data read is filtered by user; no leakage between users/tenants.
- **Human for money/legal/safety:** these are never decided by the agent.

---

## 5. Anti-hallucination via RAG (the most important mechanism)

The agent does not answer from the model's parametric memory; it **retrieves** approved text and answers
from it, with a citation.

How RAG works:
1. Documents are split into **chunks**.
2. Each chunk becomes an **embedding** (a numeric vector capturing meaning), stored in a **vector DB**.
3. At query time, the question is embedded too; a **similarity search** finds the closest chunks.
4. Those chunks are injected into the prompt as context; the model answers **from the supplied text** and
   can cite the source + version.
5. No relevant chunk -> "no verified information" + escalate.

Why this and not fine-tuning: RAG keeps facts current and auditable (update a document, not the model) and
lets you show the source. Use fine-tuning for **style/format**, never as your fact store.

---

## 6. Memory (state lives outside the model)

The model is **stateless** between calls and its **context window** is finite. So persist state in a
database and re-inject only what's relevant per turn.

- **Short-term:** the current conversation history.
- **Long-term:** durable facts about the user (their project, their entities, open issues), often as summaries.
- **Namespaces:** each agent has its own memory space so domain A's data doesn't leak into agent B.
- **Six useful scopes** (from the Dona model): Company, Project, User-Session, Approved-Doc,
  Unresolved-Issue, Escalation. See `examples/dona/memory-model-6-layers.md`.

Memory is also a **trigger source**: "this user contacted us 3 times about the same thing" -> escalate.

---

## 7. Tool calling (how the agent acts)

Tools are how the agent affects the world. Design rules:

- **Small, well-described set.** A tool's description matters as much as the prompt: when to call, the input,
  the output.
- **Read vs write.** Read tools (lookup/search) are free. **Write tools** (open/schedule/draft) require
  **explicit user confirmation** (confirm-before-write), and sometimes human approval.
- **Mechanics:** the model returns a structured request (JSON) naming a function + arguments; your code runs
  it (CRM/DB/messaging API) and returns the result; the model continues from the result.
- **Grounded returns + fail-safe:** knowledge tools return content with source + version; a tool failure
  becomes "no verified information" + escalate, never a fabrication.

See `examples/dona/tool-calling-logic.md`.

---

## 8. Guardrails (the control layer)

A layer wrapping the agent on both sides:

- **Input:** detect prompt-injection/jailbreak, block requests for others' PII, detect out-of-scope.
- **Output:** enforce disclaimers, block unsafe answers or over-promising, verify claims are grounded.
- **Implementation:** rules + pattern checks + sometimes an "LLM-as-judge" reviewing the draft before send.
- **Principle:** fail-safe.

See `examples/dona/guardrails-*.md` and `guardrails-no-hallucination.md`.

---

## 9. Evals (prove it holds)

Test the agent like a system, not by vibes.

- **Normal evals:** does it follow the SOP for the common cases?
- **Adversarial evals:** try to break it - demand binding advice it shouldn't give, ask it to invent a fact,
  prompt-inject it, request another user's PII, push an out-of-scope task, impersonate an authority,
  downplay a safety issue. Each must produce the safe behavior (disclaimer/refuse/escalate/ground).

See `examples/dona/evals-adversarial.md` and `evals-test-conversations.md`.

---

## 10. Observability + KPIs

You can't improve what you don't measure.

- **Log** every turn: who, route taken, tools called, latency, cost, whether escalated.
- **KPIs** (especially for customer-facing/onboarding agents): self-service resolution (deflection/
  containment), first-response time + SLA, escalation rate **and accuracy**, CSAT/NPS, time-to-value.
- Then **iterate** on real data: tune routing, memory, and prompts from what actually happens.

---

## Reusable checklist (copy this when starting a new agent)

```
[ ] 1. Business understood: users, journey, voice, touchpoints
[ ] 2. Domain researched: facts file with sources + verification flags
[ ] 3. Architecture chosen: single vs multi-agent + layer map
[ ] 4. Each agent has an 8-part System Prompt
[ ] 5. Knowledge base built (RAG), every entry has source + version
[ ] 6. Memory designed: scopes, namespaces, short/long-term
[ ] 7. RBAC set: who sees/does what; human-approval gates
[ ] 8. Tools defined: small set, read vs write, confirm-before-write
[ ] 9. Guardrails: input + output, disclaimers, fail-safe
[ ] 10. Orchestration: language detect, intent routing, handoff payloads
[ ] 11. Supervisor/escalation: money/legal/safety/edge triggers + routes
[ ] 12. Evals: normal + adversarial, all pass
[ ] 13. Observability + KPIs in place; iterate on real data
```
