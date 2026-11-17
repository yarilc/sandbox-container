# Proposal

## Why

The Claude adoption of `sandbox-ref-22` found Claude identifiers in the shared `tests/test_launcher.py`: `CLAUDE_YOLO` four times, `ANTHROPIC_BASE_URL` twice and an alias named `claude`. They came from the reference's old `tests/test_wrapper.py`, which was not shared. Every wrapper whose profile declares `claude` or `anthropic` fails `tests/test_alignment.py` after adopting the tag. The reference cannot see the defect, because its alignment test checks only the reference's own identifier.

## What Changes

- Replace the seven lines with neutral names: `OTHER_AGENT_YOLO`, `OTHER_AGENT_BASE_URL` and the alias `agent-alias`. Each test keeps its meaning: another agent's variable is ignored or reaches the shell, and the alias resolves to the wrapper.
- `tests/test_alignment.py` also scans the shared files for the identifiers of every sibling wrapper. It finds the siblings next to the checkout as the directories with an `agent/profile.json`. With no sibling checkout, the extra check is skipped and its skip reason says so.
- Tag the result `sandbox-ref-23`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: "Agent-neutral shared sandbox components" also rejects the identifiers of sibling wrapper profiles.

## Impact

- Shared test files only (`tests/test_launcher.py`, `tests/test_alignment.py`). The launcher, setup and network code do not change, and neither does the qualification identity.
- Claude's adoption change moves from `sandbox-ref-22` to `sandbox-ref-23`.
