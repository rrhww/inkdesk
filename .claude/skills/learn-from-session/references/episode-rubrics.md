# Episode Selection Rubrics

Use this reference after reconstructing the session evidence. Score each candidate from 0 to 3 on transfer value, causal depth, decision quality, learner gap, and evidence strength. Select the highest total; break ties by evidence strength.

## Debugging

Capture the symptom, candidate hypotheses, ordering rationale, discriminating checks, observations, belief updates, root cause, fix, and verification. Reward checks whose possible outcomes would separate multiple hypotheses. Penalize repeated commands and unexplained guesswork.

## Requirement Analysis

Capture the user outcome, ambiguous terms, hidden constraints, non-goals, edge cases, and acceptance evidence. Prefer moments where clarification changed the implementation boundary.

## Design

Capture constraints, viable alternatives, decision criteria, validation work, trade-offs, and the chosen option. Do not present the selected option as inevitable.

## Feature Implementation

Capture decomposition, dependency order, risk-first work, interfaces, failure handling, and acceptance verification. Prefer decisions that generalize beyond the repository.

## Refactoring

Capture the smell, behavioral boundary, safety net, transformation steps, and regression evidence. Distinguish structural improvement from unrelated cleanup.

## Review

Capture the risk model, affected behavior, severity and confidence, evidence, remedy, and missing tests. Prefer findings that teach how to detect the class of problem.

## Low-Value Filter

Reject episodes dominated by renaming, formatting, dependency installation, repeated file reads, boilerplate generation, or project-specific trivia unless one reveals a reusable engineering principle.
