# Agent Work Loop

Evaluate five independent dimensions. Missing evidence remains unavailable and must not be scored as success.

| Dimension | Question | Typical evidence |
| --- | --- | --- |
| Task Understanding | Does the agent know the goal and definition of done? | AGENTS.md, specs, acceptance criteria |
| Controlled Execution | Is execution bounded and repeatable? | Skills, commands, sandbox and permission policy |
| Change Validation | Is there evidence the change works? | Tests, lint, builds, browser checks and diagnostics |
| Reliable Delivery | Do review and release gates still apply? | CI, approvals, recovery and release checks |
| Learning Capture | Does the next task benefit? | Reusable skills, run evidence and maintained guidance |

Scores describe observed evidence for this run. They do not claim historical improvement without comparable episodes.
