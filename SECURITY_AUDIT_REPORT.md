# DocsMind v1.0 RC2 — Security Audit Report

This report documents the security posture improvements made during the DocsMind v1.0 RC2 hardening phase.

## Remediation Details

### 1. Credentials Isolation
- **SMTP & OAuth Scrubbing**: Hardcoded secrets in `backend/.env` have been completely removed.
- **Gitignore Auditing**: Excluded all `.env` variants (e.g. `**/.env`, `*.env.local`) to ensure credentials cannot be accidentally pushed to codebases.
- **Safe Environment Baseline**: Provided `.env.example` to define necessary deployment variables (e.g., SMTP details, client IDs) without embedding secrets.

### 2. Password Reset Hardening
- **Token Security**: Tokens are generated using `secrets.token_urlsafe(48)` to ensure cryptographic randomness.
- **Expiry Constraints**: Reset tokens expire exactly after 1 hour, reducing window of compromise.
- **Verification Isolation**: Verification endpoints check token validity without consuming them, separating authorization validation from execution.
- **Silent Validation Failures**: Request reset endpoints return standard responses regardless of email existence to prevent user enumeration attacks.

### 3. Account Safety Check
- **Soft Deletion Confirmation**: Delete account button prompts typed verification checks (`delete my account`) before triggering logout.
