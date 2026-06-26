---
description: Standard plan → implement → verify → walkthrough cycle for AquaSense
---
# devloop
## Before planning
Check constraints against .agents/rules/constitution.md. If anything in the request
conflicts with it, flag it before proceeding.
## Planning (required)
Produce a Task List and Implementation Plan as Artifacts. Include verification
steps (tests, security skill run, doc/ADR updates). Do not implement until I
click Proceed.
## Implementation
Smallest reasonable diff. If a change touches secrets, auth, or DB schema, run
the security-review skill before marking the task complete.
## Verification
Run tests if present. If you added/changed an architectural decision, write
an ADR. Update API docs/diagrams if endpoints or schema changed.
## Output
Produce a Walkthrough artifact with what changed and how to verify it.