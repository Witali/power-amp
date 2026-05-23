# Project Instructions

- Keep project communication in Russian by default unless the user asks otherwise.
- After every fifth user prompt in this project session, check `git status --short`, create a concise progress commit when there are meaningful changes, and push the current branch after a successful commit.
- Prefer coherent commits with working generated outputs. If the user explicitly asks to save progress, a small WIP-style commit is acceptable.
- For ordinary non-destructive local commands inside this project, proceed without asking first. Still honor required sandbox or system approval prompts.
- Do not revert user changes unless the user explicitly asks for that.
- Automate repeated project actions in scripts instead of relying on chat context. Prefer `scripts/project_tasks.py` and the npm wrappers `npm run symbols`, `npm run check`, and `npm run build`.
- Prefer Python for project scripts by default; use Go for complex calculations, heavy image processing, or performance-sensitive tools.
- When adding or downloading local tools for project work, update `docs/downloaded_tools.md` with the tool name, version, source URL, local path, purpose, and Git policy.
- When a new software tool is needed on Windows, first look for a Microsoft Store package and offer that installation path before downloading portable archives or installers.
- Prefer installing newly downloaded local tools under `.tmp/tools/` or another project-local path covered by `.gitignore`; do not place tool payloads in tracked directories.
- Store downloaded `archive.radio.ru` page scans under `.tmp/archive_radio_ru/<year>/<month>/` and keep them there until the user explicitly asks to delete them.
- When the user sends a page layout mockup or screenshot with markup/corrections, regenerate the markup for that page with the current pipeline first, compare it with the reported issue, and only then decide whether the algorithm still needs improvement.
- Keep any image containing manual layout corrections until all related regression tests pass.
- When changing an algorithm in a script, update the matching description or pipeline documentation in the same turn, especially docs stored next to that script.
