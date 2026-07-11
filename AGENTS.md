# AGENTS.md

## Engineering Rules

- Read the minimal local context required for the task.
- Keep changes scoped and avoid unrelated refactors.
- For bug fixes, write the failing test first, confirm it fails for the expected reason, then fix the bug.
- For user-visible changes in `web/**`, review the affected flow in a real browser before signoff.
- For documentation screenshots in Markdown, avoid fixed `height` attributes on `<img>` tags; prefer Markdown images or width-only HTML so previews preserve aspect ratio.
- Never commit secrets or credentials.
- Keep `.env*.example` files synchronized with required environment variables.
