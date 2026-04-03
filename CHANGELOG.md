# Changelog

All notable changes to Tinkerloop should be recorded here.

## Unreleased

### Changed

- renamed the PyPI distribution to `tinkerloop-ai` and prepared Trusted Publishing for stable releases
- lowered the supported Python floor to `3.10` and expanded CI coverage to `3.10` through `3.12`
- added an explicit `confirm` command, confirmation artifact namespace, and actor-model docs for outer coding-model vs inner target-orchestrator workflows

## 0.1.2

### Changed

- hardened scenario execution failure handling so target failures and trace-capture failures are classified separately
- tightened scenario validation and removed duplicate CLI scenario execution paths
- expanded installed-wheel smoke coverage in CI and aligned docs with the current adapter and trust model contract
- refreshed the local pre-PR review skill and Copilot instructions to enforce findings-first review passes

## 0.1.1

### Changed

- refreshed the README opener to be more product-facing
