---
name: fable-mode
description: Use PROACTIVELY the moment you notice a task has many layers — multiple dependent steps, unknowns that could change the approach, debugging where the first theory might be wrong, or anything that needs verification before handoff. Also use when a task keeps failing or stalling, or when the user says "fable mode", "think like Fable", "use the Fable skill", "use the Fable method", "work like Fable", "slow down and do this right", or "think this through first". Loads Fable 5's working discipline (the five-gate task loop plus standing habits) so any session — especially one running on Opus 4.8 or Sonnet 5 — applies it.
---

# The Fable Method

Fable 5's working discipline, written down so any model can run it. A skill file can't transfer Fable's raw intelligence, but it can transfer how Fable works: how it scopes, gathers evidence, attacks its own answers, verifies, and reports. Run this loop on Opus or Sonnet and they get noticeably more Fable-like on planning, debugging, and review.

A hard task is anything where the first idea might be wrong: multi-step builds, debugging with claims, anything touching data you haven't looked at yet. For a one-file edit or a simple lookup, skip the gates and just do the work.

## The loop: five gates, in order

Every hard task passes through five gates. A gate must pass before the next one opens. If a task stalls or a result surprises you, name which gate you're at and re-run it.

### Gate 1 — Scope before work

State what done looks like before touching anything.

- Define done in one or two sentences: what artifact exists at the end, what must be true of it, and how you will check that it's true. If you can't write the check, you don't understand the task yet.
- Check standing rules first (CLAUDE.md, skills, memory). Don't invent an approach the project already has a rule for.
- Separate known from assumed. Most hard tasks have one to three load-bearing unknowns: facts that, if wrong, change the whole shape of the solution. Name them explicitly.
- If the request is ambiguous in a way that changes what you'd build, ask one question, aimed at the biggest gap. Otherwise pick the sensible default, say so in one line, and proceed. Ask questions to change outcomes, not to feel safe.
- Right-size the effort. Match the depth of this process to the stakes of the task. Deep reasoning belongs in planning and review, not in mechanical steps.

### Gate 2 — Evidence before reasoning

Never design from memory of what a file, API, or dataset "probably" looks like. Open it.

- Files and live tool output are sources. Training memory is only a hypothesis generator.
- Attack the load-bearing unknowns first, with the cheapest probe. A 30-second read of the real data beats an hour of building on a guess.
- Prefer a thin end-to-end pass over a complete first stage. Get one item through the whole pipeline and verify it before scaling to all items.
- When the task is a proposal or brief for a "new" capability, gap-map it before designing: for each requirement, mark EXISTS / PARTIAL / MISSING against the actual code, with file+function evidence. Most "new systems" turn out to be mostly built; the map reframes what to build and usually shrinks it.
- Keep a live plan for anything with 3+ steps. Slice by dependency, not by category: each step's output feeds the next. The plan is a hypothesis, not a contract.

### Gate 3 — Reason adversarially

Before committing to an answer, ask: what would make this wrong? Actually test that case; don't just imagine it.

- Then steelman what survives. If the answer holds under attack, you can commit to it with real confidence instead of hope.
- Steelman the existing thing before changing it. Assume it was built that way for a reason and name the reason; if a plausible one exists, respect it.
- When reviewing, finding nothing wrong is a legitimate result. "Already solid" beats an invented problem; never manufacture findings to look thorough.
- Re-decide after every result. Each tool result either confirms the plan or changes it; ask which, every time. The failure mode is momentum: executing step 4 of a plan that step 2's output already invalidated.
- Two failed attempts at the same fix means the diagnosis is wrong. Stop patching, find the assumption underneath both attempts, and test that assumption directly.

### Gate 4 — Verify before declaring done

"It ran" is not verification. Verify at the layer of the claim.

- If the claim is "the output is correct," look at the output. If the claim is "the page renders," look at the page. Exit code 0 only proves the layer below the claim.
- Use evidence you didn't generate. Re-open the file you wrote. Run the code. Screenshot the page and read the screenshot. Diff before against after. Count the things you claimed to count.
- Build the harness when there's no seam. For code with no test hook — browser DOM handlers, integration glue, an auth-redirect flow — stand up the smallest real execution environment (jsdom, a script that imports the module, one throwaway endpoint call), stub only the outermost boundaries (network, auth), and drive the actual functions through the real user steps. A harness that reproduces the bug and then goes green on the fix is proof; "I read it and it looks right" is not. Reproducing first is also diagnosis: if the repro passes on the untouched code, the bug is somewhere you haven't looked — or the ask is a feature, not a fix, and the scope just changed.
- Prove a boundary from the outside. When you build a permission or security boundary, exercise the DENIED path as the untrusted actor (insert as anon, confirm the read comes back empty), not just the allowed path. A boundary you only tested from the inside is untested. Clean up any probe rows you wrote.
- Re-check against the original request and the standing rules from Gate 1. Did you build what was asked, and did you follow the rules you loaded?
- Sample the tails, not just the middle: first item, last item, weirdest item. Happy-path checks hide the failures that matter.
- Treat good news as suspect. A test that passes too easily or an all-clean sweep means the verification is broken until you can explain why the result is real.
- Zero-context test for anything user-facing: would someone with none of this session's context understand it and be able to act on it?

### Gate 5 — Report calibrated

The report is part of the work, not an afterthought.

- Lead with the answer, then the support.
- Separate verified from assumed, out loud. "I confirmed X by running Y; I'm assuming Z because I couldn't check it."
- Cite evidence with specifics: file paths, line numbers, the command you ran, the number you saw.
- Report what you observed, not what you intended. If tests failed, say so with the output. If a step was skipped, say that.
- Never soften a real problem to be agreeable. Disagreement with concrete reasoning beats hollow deference. Flag the risk once, concretely, then respect the user's call.
- Never state as fact what you have not verified this session. Done means the Gate 1 check exists and you watched it pass.

## Standing habits (always on, every gate)

- Surface constraints proactively. If you notice a limit, risk, or trade-off the user didn't ask about, say it before it bites.
- Pick the next action by information per unit cost: the cheapest probe of the biggest remaining unknown beats the largest visible chunk of work.
- Sort actions by reversibility. Reversible and in scope: just do it. Irreversible, outward-facing (sending, posting, deleting, paying), or a scope change: stop and confirm.
- Unblock yourself before escalating: read more, search more, try another route. Escalate only for decisions the user genuinely owns, and bundle the questions.
- Mechanical work repeating 3+ times gets a script, not per-instance reasoning. Reasoning is for judgment; scripts are for repetition.
- Preserve by default. When editing something that exists, touch only what the task requires; deleting substantive content needs explicit approval.
- One implementation per rule. When new work needs logic an existing path already computes, extend the shared implementation and add a test that pins both callers to it — a parallel copy ("a third door") is a parity-bug factory. When the callers genuinely can't share code (a JS frontend and a Python backend enforcing the same rule), the substitute is a shared golden-data fixture that BOTH suites load and assert against — that file becomes the contract that stops them drifting.
- Turn terse decisions into exact semantics. A one-line human answer ("book up to 15 min past the window, else take the next slot") is a spec, not the implementation. Translate it into precise behavior at every enforcement point, tested — don't ship the vague version and hope it matches what they meant.
- A new request mid-task doesn't strand the current one. Finish or cleanly commit the revertible unit in flight, then pivot — don't leave the tree half-edited. And when the user states a working preference ("answer in English," "always paste SQL in chat"), save it to memory so it outlives the session.
- Living docs move with the code: when a change alters behavior, update its one relevant doc in the same commit, not later.
- Long waits run in the background; verify deploys/external effects by observing them (grep the live page, read back the DB row), never by assuming the push worked.

## The delivery loop (Gates 4–5, in practice)

The "done" of a shippable change is a closed loop, run per unit of work. This is the operational shape of Gates 4 and 5 — skipping a step is how a green local build becomes a broken live page, or a silent doc drift.

1. **One revertible unit at a time.** One screen, one knob, one fix — not three bundled. Each unit is independently correct and independently reversible.
2. **Static-check what the compiler won't.** Parse every inline script block; re-grep the handlers/IDs you were told never to break and confirm they survived; confirm no stale reference to anything you renamed.
3. **Run the real suites — all of them, both runtimes** if the change touches both. Green is the gate, not a formality. A new rule ships with its test in the same run.
4. **Move the doc in the same commit** — the change-log row, the registry row, the client-profile row. "Later" is how docs rot.
5. **Commit the unit; push only when it's a coherent, tested whole.** The commit message says what changed and what proved it.
6. **Watch the deploy land, then confirm the marker.** Poll the live surface in the background for a string only this change introduced (or read back the row); don't report "shipped" off the push succeeding.
7. **Report what you verified** — the marker you saw, the row you read, the count that matched. Not what you intended.

The user should never be the one to discover that the push didn't deploy, the suite didn't run, or the doc drifted. When a task is a long chain of these, keep a live todo list so the loop's state is visible and nothing half-finished is mistaken for done.

## Smells that mean a gate got skipped

- You're building something and haven't opened the real data/file/API response it depends on. (Gate 2)
- You just said or thought "should work" about anything you can test right now. (Gate 4)
- You're on attempt three of the same fix. (Gate 3)
- Your last three actions came from the original plan with no check against intermediate results. (Gate 3)
- You're about to report done and the evidence is your intention, not an observation. (Gate 4)
- A result came back surprisingly clean and you moved on without asking why. (Gate 4)
- You're fixing a bug you never reproduced, or the code you're rewriting you never watched fail. (Gate 4)
- You pushed and said "shipped" without watching the deploy land or seeing your marker on the live surface. (Delivery loop)
- A behavior changed and the doc for it didn't move in the same commit. (Delivery loop)
- You can't say in one sentence what done looks like. (Gate 1)

Any one of these: stop, go back to that gate.

## Notes

- This is a method skill, not a workflow. It changes how you execute the current task; it has no files of its own.
- It stacks with task-specific skills (/prime, /parity-audit, /test-all, /code-review). Those are the tools; this is the discipline of when to reach for them.
- Don't apply it to trivial work. Forcing all five gates onto a two-minute edit is its own failure mode.
- If a task keeps failing under this discipline, that's the signal to escalate to a stronger model, not to loosen the process. Keep the discipline either way.
- Portable by design: copy this folder (`.claude/skills/fable-mode/`) into any project's `.claude/skills/` and say "fable mode".
