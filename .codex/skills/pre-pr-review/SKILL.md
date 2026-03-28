# Pre-PR Review (Local)

## Goal
Perform a proactive review of the current local checkout before opening a PR.

Treat this as production-bound code. Prioritize:

- correctness
- regression risk
- observability and diagnostics
- rollback safety
- doc/code/test alignment

This is a review workflow, not an editing workflow.
Do not change code unless the user explicitly asks for fixes.

## Scope

- Review only the current working tree changes and newly added files.
- Inspect nearby callers, shared utilities, config, docs, and tests only as needed to evaluate the diff safely.
- Keep the focus on bugs, risky assumptions, duplicated logic, stale tests, abandoned code paths, and release-surface drift.

## Repo-Specific Expectations

For this repo, always check:

- docs match current code and CLI behavior
- unit tests are still current and not asserting obsolete behavior
- release/build flows still work when packaging or CLI/docs change
- no emoji, AI giveaway phrasing, or sloppy compatibility leftovers appear in code/comments/loggers/docs

## Auto-Collect Context

Run these yourself:

1. Detect repo root and current branch.
2. Determine the likely base branch.
   - Prefer `origin/HEAD`.
   - If ambiguous, infer the best base and state the choice.
3. Collect diff context.
   - `git status --short`
   - `git diff --stat`
   - `git diff --name-only`
   - `git diff`
   - `git diff origin/<base-branch>...HEAD`
4. If `HEAD` already matches the base branch and the review is only about uncommitted working-tree changes, say that explicitly.

## Review Checklist

### 1) Correctness

Look for:

- logic bugs
- broken or misleading error handling
- wrong failure classification
- empty/null/boundary cases
- broken cleanup/finalization paths
- assumptions that the diff invalidates

### 2) Risk

Call out:

- behavior or contract changes
- API or CLI changes
- packaging/release changes
- destructive or data-loss risk
- rollout or rollback concerns

### 3) Testing And Verification

- Identify missing tests and stale tests.
- Check whether current tests actually cover the risky edge cases in the diff.
- Run the best local checks for the repo. Prefer:
  - `pytest -q`
  - `ruff check .`
  - `python -m build --wheel --sdist --no-isolation`
- If packaging, install, or CLI behavior changed, run an installed-wheel smoke test when practical.
- If a reproduced edge case is not covered by tests, call that out explicitly even if the suite passes.

### 4) Docs And Operability

Check:

- README and docs against actual behavior
- troubleshooting guidance against actual failure modes
- release checklist vs CI/workflow enforcement
- whether the diff makes diagnosis easier or harder for operators

### 5) Maintainability And Style

Review:

- duplication
- dead or abandoned code
- unnecessary compatibility layers
- naming and structure
- comments and user-facing wording

## Output Requirements

Reviews must be findings-first.
Prioritize bugs, regressions, misleading semantics, and missing tests before summaries.

For each finding include:

- priority: `P0`, `P1`, or `P2`
- file path
- what is wrong
- why it matters

When helpful, include a minimal patch sketch, but do not dump large rewrites.

If you find no issues, say that explicitly and still mention residual risks or coverage gaps.

## Output Format

1. Findings (`P0` / `P1` / `P2`) ordered by severity
2. Open questions or assumptions
3. Brief summary + risk level
4. Commands run + key results
5. Merge readiness recommendation
6. Rollback or mitigation notes

## Start

- Determine the base branch
- Gather the working-tree diff
- Run the repo-appropriate checks
- Deliver a findings-first review
