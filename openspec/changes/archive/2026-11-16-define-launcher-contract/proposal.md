# Proposal

## Why

The six launchers (`sandbox-container.sh` and the five agent wrappers) expose the same interface, but their code has drifted into two lifecycle families. Measured against the reference after normalizing prefixes, Claude shares 81% of its code lines, and Codex, Antigravity, OpenCode and Pi share 26–40%. Every launcher defect is therefore ported by hand up to six times; the lifetime-notice fix was the latest example. The tests drifted the same way: each `tests/test_wrapper.py` has 1,500–1,900 lines. Before writing a shared launcher core, the target behavior must be fixed in one place. Otherwise the core inherits one family's gaps, and the adoptions find them late, as `sandbox-ref-19`, `-20` and `-21` did.

## What Changes

- Inventory every difference between the six launchers and their wrapper tests, phase by phase (arguments and help, modes and budgets, workspace and state checks, engine checks, mounts and image, creation and start, signals, shutdown and recovery). Record each difference in `docs/launcher-contract.md` with the decision taken for the shared core: adopt one family's behavior, take the union, or keep it agent-specific behind a hook.
- Define the contract of the shared launcher in the same document:
  - one shared Bash core, copied byte for byte like the other shared files;
  - a thin per-wrapper entry script;
  - a per-agent Bash file that carries the profile data the core needs and the agent hooks, kept consistent with `agent/profile.json`;
  - a shared launcher test suite on a shared fake engine.
- List every observable behavior the reconciliation changes, and the spec deltas the implementation change must write for them.
- Resolve the findings of an independent review of the document, including the installation and qualification lists the core files must join.
- No launcher code, test code, shared file or spec changes in this change; no new tag. The core, the shared tests, the spec deltas and the tag follow in the next change, so the specs change only when the behavior does.

## Capabilities

### New Capabilities

None in this change. The implementation change introduces `shared-launcher`
from the contract recorded here.

### Modified Capabilities

None in this change (`skip_specs: true`). The implementation change modifies
`container-launcher`, `container-isolation` and `persistent-state` as listed
in the document's "Spec deltas for the implementation change".

## Impact

- Reference only: `docs/launcher-contract.md` and `docs/launcher-test-map.md` (new), a `docs/validation.md` entry. No change to `network/`, `setup/`, the shared tests, any launcher or any wrapper repository.
- Read-only analysis of the five agent wrappers' launchers and `tests/test_wrapper.py`.
- Following changes: shared core and tests in `sandbox-container` under a new tag, then one adoption change per wrapper (Claude, then Codex, Antigravity and Pi, then OpenCode).
