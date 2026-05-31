# Security Policy

We take the security and integrity of the Results Processing System (RPS) seriously. As an open-source, local-first engineering application, protecting user data and verifying code execution security is paramount.

This document describes how to report security vulnerabilities and outlines our security commitment.

---

## 1. Supported Versions

We actively maintain and provide security patches for the following versions:

| Version | Supported | Notes |
| :--- | :--- | :--- |
| **v2.22.x** |  Active / Supported | Main active branch for NGI Zero development. |
| **v2.21.x** |  Security-only patches | Supported until next major release. |
| **< v2.20** |  Unsupported | We recommend upgrading to v2.22+ immediately. |

---

## 2. Reporting a Vulnerability

If you discover a security vulnerability (such as a remote code execution bug, local file path traversal, or database manipulation flaw), **please do not open a public issue.** Instead, follow our private disclosure channel:

1. **Send a secure email** to our security team at `security@rps.local` (or [insert maintainer email, e.g., adrian.zavoianu@gmail.com]).
2. **Include in your email:**
   * A detailed description of the vulnerability.
   * A proof of concept (PoC) or step-by-step reproduction instructions.
   * Any potential impact or scope of the vulnerability.

We will acknowledge receipt of your report within **48 hours** and provide a triaged evaluation with a proposed remediation timeline. We ask that you give us at least **90 days** to patch and release a fix before public disclosure.

---

## 3. Our Secure Coding Framework in RPS

Because RPS is a local-first application processing structural engineering Excel sheets, we implement several defensive design rules to safeguard the host system. If you are developing features or writing patches, you must adhere to these policies:

### SQL Injection Prevention
RPS uses **SQLAlchemy ORM** to manage the local project SQLite databases.
* **Do not use raw SQL string interpolation** (e.g., `f"SELECT * FROM ... WHERE name = '{user_input}'"`).
* Always rely on SQLAlchemy's query constructor, column objects, and parameterized queries which sanitize inputs by default.
* If a raw query is absolutely necessary (e.g. for specialized performance migrations), use parameterized SQL parameters (`text("SELECT ... WHERE name = :name")`).

### Path Traversal Protection
During batch folder imports, RPS scans Excel files located in a specified directory.
* When resolving filenames or building paths, ensure directories do not resolve outside the intended workspace using standard path sanitization:
  ```python
  from pathlib import Path
  
  # Ensure the target file path remains strictly under the project directory
  base_dir = Path(project_root).resolve()
  target_file = Path(import_file).resolve()
  if not target_file.is_relative_to(base_dir):
      raise PermissionError("Access denied: File resolves outside project bounds.")
  ```

### Dependency Hygiene
* Keep libraries in `Pipfile` updated.
* Regularly execute security checks in your dev environment:
  ```bash
  # Check for known vulnerabilities in third-party packages
  pipenv run safety check
  
  # Run static security linter on source code
  pipenv run bandit -r src/
  ```

---

*Thank you for helping us keep RPS secure, trustable, and robust for the engineering community!*
