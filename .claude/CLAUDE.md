# 🧩 Iterative Development Mode (Rapid Prototyping)

This document defines the operating principles for **fast, iterative application development**.
The goal is to move from concept to functional prototype as quickly as possible while maintaining a clean, logically structured foundation that can later evolve into production-grade code.

## 📚 Project Documentation

Before starting work, familiarize yourself with the project documentation:

- **[ARCHITECTURE.md](../ARCHITECTURE.md)**: Complete technical architecture, database schema, design patterns, and component structure. **Read this for understanding the system design.**
- **[CLAUDE.md](../CLAUDE.md)**: Quick development guide with common tasks and utility references
- **[PRD.md](../PRD.md)**: Product requirements, features, and roadmap

---

# Purpose and Philosophy

Speed and iteration are paramount.  
Focus on producing functional, logically correct, and modular code without the overhead of validation, logging, testing, or exhaustive documentation.  
The structure should remain clean and scalable so that later refactoring into production form (Mode 2) is straightforward.

This mode is for **exploration and evolution**, not stability or auditability.  
You are allowed to skip safeguards that slow iteration, but you must **preserve clarity, architecture, and consistency**.

---

# Core Principles

**1. Professional mindset with flexibility:**  
Act as a full-stack developer using modern, scalable stacks (Django, React, Rust, etc.). Use current best practices but relax rigor for speed.

**2. Architecture and structure:**  
Maintain separation of concerns and consistent folder layout. Favor clear module boundaries that can be hardened later.

**3. Minimal communication noise:**  
Remain silent unless the code is incomplete, an ambiguity prevents execution, or a critical issue emerges.

**4. Code clarity and modularity:**  
Write clear, maintainable code that can be expanded. Skip production polish but keep naming, structure, and logic easy to follow.

**5. Avoid technical debt traps:**  
You may leave temporary solutions, but every simplification must be clearly marked with `# TODO` or `# TEMP`. Never hide complexity behind unclear shortcuts.

**6. Iteration velocity:**  
Optimize for feedback cycles — implement, test manually, iterate. Do not aim for full coverage or perfection.

**7. Performance awareness:**  
Avoid intentional inefficiencies, but don’t prematurely optimize. The focus is correct logical flow.

**8. Feature work:**  
Understand dependencies before changing code. Maintain backward consistency across the prototype to avoid rewriting core logic later.

---

# Guardrails

**1. Security always enforced:**  
Never expose secrets, tokens, or unsafe file operations. Validate at least high-risk inputs (auth, DB writes).

**2. Fail visibly, not silently:**  
If logic is unclear or inputs invalid, raise errors immediately instead of logging or hiding failures.

**3. No schema mutations without consent:**  
Do not alter databases, indexes, or models beyond what’s necessary for iteration unless approved.

**4. No production dependencies:**  
Avoid complex observability, feature flags, or analytics libraries at this stage.

**5. Data safety:**  
Do not perform destructive or irreversible database operations. Work in isolated dev environments.

**6. Fallback values:**  
Dont use fallback values or mock data for prototyping, use the real data if possible.

**7. Rapid dependency adoption:**  
You may add libraries that significantly speed iteration as long as they are well-maintained and compatible with the tech stack.

**8. Documentation optional:**  
Write comments only for unclear logic or to mark areas requiring later improvement.

---

# Implementation Conventions

**Tailwind and JSX/TSX:**  
Semantic class first, utilities next. Keep purpose clear (`<div className="card p-4 bg-neutral-900" />`).
Declare semantic selectors centrally in `structure.css`.

**Component boundaries:**  
Keep components small and single-purpose. Pure components handle UI; containers handle minimal data fetching.

**Data and API usage:**  
Simplify calls; no caching layers or pagination unless core to feature. Inline fetches allowed for simplicity.

**Forms and validation:**  
Basic form validation is optional. Keep forms functional and clean, schema validation can be added later.

**Types and contracts:**  
Keep types consistent where practical but tolerate flexibility during iteration. Strong typing enforced in Mode 2.

**Error and loading states:**  
Basic placeholders are enough. No need for standardized boundaries yet.

**Accessibility:**  
Ensure minimum viable usability, but detailed WCAG adherence can wait.

**Performance:**  
Avoid obvious inefficiencies but skip premature micro-optimizations.

**File layout:**  
Organize by feature. Keep simple co-location (component + logic). Avoid overengineering structure.

**Testing:**  
Manual validation is acceptable. Automated tests will be added in Mode 2.

**Logging and monitoring:**  
Optional or omitted. Use console-level or temporary prints if necessary, always tagged `# DEBUG`.

**Documentation:**  
Optional lightweight notes at the module level if useful for handoff.

---


