---
name: learn-from-session
description: Turn a completed coding or product-work session into an interactive, offline HTML learning workbook that teaches transferable debugging, requirement analysis, design, implementation, refactoring, review, and verification skills. Use after a bug is fixed, a feature or refactor is completed, a technical approach is chosen, a review reaches conclusions, or when the user asks to review, learn from, or understand the process behind the current session. Do not use for routine edits with no meaningful learning value or while the task is still actively unresolved.
---

# Learn From Session

Convert the visible evidence from the current session into an active-learning workbook. Teach how the work moved from uncertainty to evidence and decisions, not only the final answer.

## Workflow

1. Confirm that the session contains a completed or reviewable milestone. If it does not, explain why a workbook would be premature and stop.
2. Reconstruct learning episodes only from visible conversation, diffs, commands, logs, tests, and decisions. Never request or reveal hidden chain-of-thought.
3. Read [references/episode-rubrics.md](references/episode-rubrics.md). Score the episodes and select the highest-transfer-value episode; list other meaningful episodes in the event map.
4. Read [references/teaching-method.md](references/teaching-method.md). Create a rewind question that hides the eventual answer and asks the learner to choose a next action, expected observation, and interpretation.
5. Label every decision-trace item as `evidence`, `reconstruction`, or `recommendation`. Do not turn hindsight into claimed session evidence.
6. Read [references/workbook-schema.md](references/workbook-schema.md). Create valid workbook JSON. For an initial workbook, set `stage` and mastery status to `workbook` and `exposed`.
7. Run `python scripts/render_workbook.py <input.json> --output <path>` from this Skill directory. Default to `learning-reviews/<date>-<topic>.html` under the active workspace unless the user specifies another path.
8. Return the HTML path and invite the learner to answer before expanding the reference path. The workbook must remain useful without returning to chat.
9. When the learner returns answers, give targeted feedback, add evidence of understanding, set `stage` to `final`, update mastery only as allowed by the evidence, and overwrite the same HTML file.

## Content Rules

- Prefer causal mechanisms, discriminating checks, requirement boundaries, trade-off criteria, implementation ordering, and verification strategy.
- Include failed attempts only when they changed the hypothesis space or reveal an inefficient pattern worth correcting.
- State when the Agent's exploration was repetitive, weakly motivated, or lucky. Offer a better expert path as `recommendation`.
- Teach one core capability at a time. Keep the initial activity near three minutes and offer other episodes afterward.
- Change surface details in the transfer challenge while preserving the underlying mechanism.
- Treat reading and answer disclosure as `exposed`, not proof of mastery.

## Mastery Rules

- `exposed`: the concept appeared; no learner evidence exists.
- `explained`: the learner accurately explained the mechanism or trade-off.
- `transferred`: the learner solved a changed but structurally similar case.
- `independent`: a later real task shows unprompted application.

Never infer mastery from Agent-authored code, report completion, or the learner opening the HTML.

## Failure And Privacy Rules

- If context is incomplete, say which evidence is unavailable and avoid confident reconstruction.
- If no high-value episode exists, do not generate filler; give a concise explanation.
- Do not persist full transcripts, source code, secrets, logs, or customer data in a learner profile.
- Escape all session-controlled text before inserting it into HTML.
- If Python or file writing is unavailable, use `assets/learning-workbook-template.html` as a guide and produce the same structure directly. If no file can be written, provide a compact chat fallback and disclose the limitation.

## Evaluation

For development, regression testing, or self-review, read [references/evaluation-cases.md](references/evaluation-cases.md) and check fidelity, active recall, transfer quality, mastery evidence, privacy, offline behavior, and accessibility.
