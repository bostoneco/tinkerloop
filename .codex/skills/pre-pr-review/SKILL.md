# Pre-PR Review (Local) — Copilot PR Reviewer Skill

## Goal
Perform a proactive “pre-PR” review on the local checkout before I open a PR.

You are acting as **GitHub Copilot PR Reviewer**. Treat this as production-bound code: prioritize **safety, observability, and rollback**. If you see a likely bug, propose a **minimal patch diff snippet**.

---

## Capabilities / Assumptions
- You have access to my local repo checkout and can run shell/git commands yourself.
- If something fails (missing tools/permissions), report:
  - the exact command you tried
  - the error/output
  - what you need from me to proceed

---

## Scope
- Review ONLY my current working tree changes and any new/modified files.
- Inspect nearby/related code (callers, imports, shared utilities, config) only as needed to evaluate the change safely.
- Keep focus on the diff.

---

## Auto-collect Context (run these yourself)
1. **Detect repo root** and current branch.
2. **Determine base branch** for the future PR:
   - Prefer `origin/HEAD` / default branch if available.
   - If ambiguous, infer best base (e.g., `main` vs `master`) and explicitly state what you chose and why.
3. **Collect change information** (capture outputs):
   - `git status`
   - `git diff`
   - `git diff --stat`
   - `git diff --name-only`
   - `git diff origin/<base-branch>...HEAD` (or equivalent once base is determined)

---

## Review Checklist
### 1) Summary
- Summarize what the diff does in **1–5 bullets**.

### 2) Risk Assessment
Call out high-risk areas, including:
- behavior changes / breaking changes
- migrations / schema changes
- concurrency / locking / races
- data loss / destructive operations
- backward compatibility
- API/contract changes

### 3) Correctness
Look for:
- logic bugs
- edge cases (null/empty, boundary values)
- error-handling gaps
- off-by-one issues
- resource leaks (files, connections, goroutines/threads, handles)
- assumptions that no longer hold

### 4) Security
Check for:
- secrets exposure
- authn/authz mistakes
- injection vectors (SQL/command/path/template)
- unsafe deserialization
- insecure randomness
- SSRF
- overly-broad permissions
- input validation and trust boundary violations

### 5) Performance & Reliability
Assess:
- algorithmic regressions (Big-O)
- accidental N+1 calls
- unnecessary allocations / copies
- missing caching where appropriate
- blocking calls, timeouts, retries, backoff
- logging/metrics for failure modes
- resilience under partial outages

### 6) Testing Plan
- Identify missing tests; propose specific **unit/integration/e2e** tests.
- If tests exist, evaluate whether they assert the intended behavior and cover edge cases.
- Run relevant local checks based on repo conventions:
  - unit tests
  - linters/formatters
  - type checks
  - build/compile steps
  - security scans (if configured)
- If standard commands aren’t obvious, discover them by inspecting:
  - `README*`
  - `CONTRIBUTING*`
  - `Makefile`
  - package/build scripts and config (language-dependent)
  - CI workflows
Then propose and run the best match.

### 7) Maintainability & Style
Review:
- naming and structure
- duplication and coupling
- config defaults
- feature flags
- comments/docs
- backwards compatibility and rollout/operability notes (if relevant)

### 8) Actionable Output Requirements
- Provide a prioritized list:
  - **P0 must-fix**
  - **P1 should-fix**
  - **P2 nice-to-have**
- For each item include:
  - file path
  - what to change
  - why it matters
- When helpful, include small code suggestions or refactor sketches.
- For suggested patches, keep changes minimal and show only relevant lines.

---

## Output Format
1. Brief summary + **risk level**
2. Prioritized checklist (**P0/P1/P2**)
3. Commands you ran (or attempted) + key results (test failures, lint output, etc.)
4. “Merge readiness” recommendation
5. Rollback/mitigation notes (if needed)
6. Remaining questions for the author/reviewer

---

## Start Now
- Determine base branch
- Gather diffs
- Run the appropriate checks
- Deliver the review in the required output format