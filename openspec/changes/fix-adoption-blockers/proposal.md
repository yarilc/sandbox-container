# Proposal

## Why

Planning Claude's adoption of `sandbox-ref-19` found two defects that would affect every agent wrapper, so they are fixed here first under `sandbox-ref-20`, as the propagation procedure requires:

- The shared `tests/test_guard.py` (`guarded_multiplex`) reads the proxy image from the runtime harness with `environment[profile_env('EGRESS_IMAGE')]`. Since `sandbox-ref-19`, `profile_env` names the fixture variable (`FIXTURE_AGENT_EGRESS_IMAGE`), but each agent wrapper's `test_network_runtime.provider_fixture()` returns its own variable names. `--guard` would fail with `KeyError` in all five wrappers.
- Each wrapper's `tests/test_reference_copy.py` still names `claude-container` as its sibling reference checkout, in its docstring, in `SIBLING` and in a skip message. `tools/propagate.py` rewrites only the tag, commit and hashes, so after adoption the sibling check would look for the new tag in `claude-container`, not find it, and skip silently.

## What Changes

- `tests/test_guard.py` takes the proxy image from the harness environment without depending on the wrapper's variable names: it uses the single entry whose name ends in `_EGRESS_IMAGE`.
- `tools/propagate.py --apply` also makes the target manifest name the reference repository: the `SIBLING` checkout path, the docstring and the skip message name the directory of the checkout the tool runs from (`sandbox-container`). The dry run lists this as a manifest change.
- `tests/test_propagate.py` covers both rewrites; `docs/propagation.md` documents them.
- The change ends with the annotated tag `sandbox-ref-20`. Every wrapper, Claude first, then adopts `sandbox-ref-20` directly instead of `sandbox-ref-19`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reference-propagation`: an applied run also points the target manifest at the reference repository; shared tests that use a wrapper's runtime harness read no wrapper-specific variable names.

## Impact

- Shared file: `tests/test_guard.py` (new tag needed; wrappers adopt it with `tools/propagate.py`).
- Reference-only files: `tools/propagate.py`, `tests/test_propagate.py`, `docs/propagation.md`.
- No production code, image, profile or qualification identity changes, so installations need no new setup.
