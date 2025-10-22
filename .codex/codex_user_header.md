MODE: FAST
REPO: <name>
SERVICE: <name_or_path>
SCOPE: <short_task_name>
BRANCH: feature/<branch>

GOAL
- <one sentence objective>

CONSTRAINTS
- Follow FAST rules in .codex/rules.md and Codex System Rules (FAST).
- No schema changes unless explicitly stated.
- No secrets or PII in code/logs.
- Output only requested files/diffs.

DELIVERABLES
- Minimal working code with clean structure.
- Mark TODO(PROD), TEMP(FAST), DEBUG(FAST).
- Short handoff notes for hardening.

NOTES
- List assumptions explicitly.
