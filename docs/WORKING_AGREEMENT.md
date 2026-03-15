# Working Agreement

This document defines how to use Tinkerloop day to day with the features that already exist.

It is a process agreement, not a product roadmap.
The goal is to make runs more comparable, failures easier to act on, and reruns more disciplined without adding new core behavior.

## Scope

This agreement applies when:
- authoring or editing scenarios
- adding or maintaining adapters
- using Tinkerloop to diagnose and improve a target app

This agreement does not change the project charter:
- deterministic checks stay first-line gates
- target-app logic stays behind adapters
- no automatic deploys
- no autonomous code changes without a human gate

## Default Loop

Use this sequence unless there is a specific reason not to.

1. Confirm target readiness first.
Run adapter preflight and resolve the inner runtime before trusting any scenario result.
If runtime selection is ambiguous, stop and choose explicitly instead of running with a guessed configuration.

2. Start with the smallest valid scope.
Prefer one tagged slice or one explicit scenario family before running a broad regression set.
Use `--tag` or `--scenario` for the first loop.

3. Review artifacts, not just terminal output.
Treat these as the primary evidence for a run:
- `latest.json`
- `latest-failures.json`
- `latest-diagnosis.json`

4. Patch one bounded cause at a time.
Do not mix unrelated fixes in the same iteration.
If multiple scenario families fail for different reasons, split them into separate loops.

5. Rerun the failing slice first.
After a change, rerun the smallest affected scope.
Then use `--failed-from` to validate the failed set from report artifacts.

6. End with a broader regression pass.
Once targeted failures clear, rerun the broader tagged slice or full scenario set before considering the loop complete.

## Run Discipline

- Keep the inner runtime explicit in notes and reports whenever it matters to the result.
- Do not compare runs taken against different runtime selections as if they were equivalent.
- Do not treat a passing targeted rerun as sufficient if the change can affect unrelated scenarios.
- When a preflight fails, fix readiness first instead of debugging scenario behavior.
- Prefer repeated small loops over a single large patch followed by a full rerun.

## Scenario Authoring Rules

- Every scenario should have a clear `scenario_id` and a concise description.
- Tag scenarios so feature slices can be rerun intentionally.
- Mark destructive scenarios explicitly and keep them opt-in.
- Prefer deterministic checks over vague output expectations.
- Use tool-trace checks when the tool path matters, not only assistant text checks.
- Keep each scenario focused on one behavior family when possible.

## Adapter Readiness Checklist

Before trusting a new or changed adapter, verify:
- `preflight()` blocks cleanly on auth, config, and runtime readiness issues
- runtime resolution reflects the target repo boundary instead of machine-wide guesses
- ambiguous runtime state produces a bounded candidate list with reasons
- trace capture works for the target app's real tool execution path
- `run_metadata()` is useful enough to explain what environment was exercised

If one of these is weak, fix the adapter contract first.
Do not paper over adapter uncertainty with looser scenario checks.

## Failure Triage Template

For each failing scenario family, capture:
- symptom: what failed in `latest-diagnosis.json`
- check failure: which deterministic check failed
- observed path: what tool calls or assistant behavior actually happened
- likely owner: target module, prompt, routing rule, or adapter boundary
- next rerun scope: exact `--scenario`, `--tag`, or `--failed-from` command to use after the next change

The point is to make each rerun intentional and auditable.

## Review Standard

A loop is only complete when:
- preflight is clean
- runtime selection is explicit or confidently resolved
- the targeted rerun passes
- the failed set passes when rerun from artifacts
- the broader regression scope appropriate to the change also passes

## Anti-Patterns

Avoid these:
- broad reruns before reproducing the failure on a narrow slice
- changing scenario expectations to hide adapter or product regressions
- comparing results across different runtime selections without calling that out
- relying on terminal logs when the JSON artifacts disagree
- bundling multiple unrelated fixes into one validation loop

## Minimum Commands

Narrow first:

```bash
tinkerloop \
  run \
  --adapter <adapter-factory> \
  --user-id <user-id> \
  --scenarios <scenario-dir> \
  --tag <tag>
```

Rerun the failed set from report artifacts:

```bash
tinkerloop \
  run \
  --adapter <adapter-factory> \
  --user-id <user-id> \
  --scenarios <scenario-dir> \
  --failed-from artifacts/reports
```

Use these as the standard validation spine unless the target app needs a more specific workflow.
