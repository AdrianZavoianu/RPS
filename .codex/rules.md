# Iterative Development Rules (FAST)

This repository is currently in **FAST** stage. Prioritize rapid iteration and clean structure.  
Validation, exhaustive error handling, logging/observability, automated testing, and full documentation are **deferred** unless essential for basic function.

---

# Purpose and Philosophy
Move quickly from idea to working feature while keeping code readable and easy to harden later. Preserve clarity, simple architecture, and consistent structure.

# Core Principles
- **Velocity first, clarity always.**
- Use modern, supported stacks and idioms.
- Keep separation of concerns and feature-based organization.
- Avoid premature optimization and abstraction.
- Prefer small, readable modules.

# Guardrails
- **Security is non‑negotiable:** no secrets in code/logs; avoid unsafe file ops.
- **Fail visibly:** raise obvious errors; no silent failures.
- **No destructive DB ops** and **no schema changes** without explicit approval.
- Dev-only data and fallbacks allowed, but must be marked.

# Implementation Conventions
- **Components:** small, single-purpose; containers fetch minimal data.
- **Styles:** semantic class first, Tailwind utilities next.
- **APIs:** inline/simple fetches acceptable; skip caching/pagination unless core.
- **Forms:** minimal validation; schemas optional.
- **Types:** keep consistent where practical; strict typing deferred.
- **Errors & loading:** basic placeholders acceptable.
- **Accessibility:** minimum viable usability.
- **Performance:** avoid obvious inefficiencies; skip micro-optimizations.
- **File layout:** organize by feature; colocate component + logic.
- **Testing:** manual is acceptable; note gaps for later.
- **Logging:** optional; temporary prints allowed and must be tagged.
- **Docs:** optional lightweight notes if helpful.

# Markers (must be used)
- `# TODO(PROD): ...` — required improvements for hardening.
- `# TEMP(FAST): ...` — temporary fast-mode shortcuts.
- `# DEBUG(FAST): ...` — temporary debug prints (delete later).

# Exit Criteria (to move to PROD)
1) TODOs are identified and actionable.  
2) Core workflows correct and modular.  
3) No known logical errors.  
4) Structure consistent and readable.  
5) End-to-end works with representative data.
