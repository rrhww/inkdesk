# Vendored Harness Sources

Production does not fetch these sources from GitHub. This directory contains an
audited, reduced snapshot for the `harness-audit-v1` workflow.

## Better Harness

- Repository: `QoderAI/better-harness`
- Commit: `40011c1e98374c4b24b2d8fde43d9e39611f1df6`
- Source: `models/agent-work-loop.md`
- Local file: `better-harness-agent-work-loop.md`
- Modification: reduced to the stable five dimensions, evidence boundary, and
  finding retention gates; upstream score ranges are mapped to Inkdesk's 0-4
  reader scale.

## Agency Agents

- Repository: `msitarzewski/agency-agents`
- Commit: `8ef49232e02431f7ca4792b487e5a85a7939ff3a`
- Sources:
  - `engineering/engineering-codebase-onboarding-engineer.md`
  - `testing/testing-test-automation-engineer.md`
  - `security/security-ai-generated-code-auditor.md`
  - `engineering/engineering-software-architect.md`
- Local files: `profiles/*.md`
- Modification: removed personality, memory, implementation, and write-oriented
  instructions. Retained the evidence discipline and role boundary needed for
  read-only analysis of a pre-collected Evidence Bundle.
