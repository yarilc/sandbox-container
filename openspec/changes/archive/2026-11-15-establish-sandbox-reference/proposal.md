# Proposal

## Why

`claude-container` has been both the Claude Code product and the reference for the shared sandbox components (`network/`, `setup/`, the shared tests and `tools/propagate.py`). Because the reference was only exercised with the Claude profile, several shared defects (the XDG, DBUS and identifier-comment fixes behind `sandbox-ref-15` to `sandbox-ref-17`) first surfaced in other wrappers. `sandbox-container` now holds the imported history up to `sandbox-ref-18` (merge `9ff66c8`). This change makes it an agent-neutral reference: an air-gapped Bash shell with every sandbox feature, from which the next tag, `sandbox-ref-19`, is propagated to all five agent wrappers, Claude included.

## What Changes

- **BREAKING** The wrapper becomes `sandbox-container.sh`, which opens an interactive Bash shell. All variables move from `CLAUDE_CONTAINER_*` to `SANDBOX_CONTAINER_*`; images, labels, the in-container home and the installation names follow the new profile. Claude Code, `CLAUDE_YOLO`, account login, API-key forwarding and Claude optional-traffic variables are removed.
- **BREAKING** Network modes: `offline` is the default when no mode is set; `unrestricted` stays available on explicit request; `provider` is rejected because the reference profile declares no authentication method. Host Podman delegation remains allowed only with `unrestricted`.
- Shared agent profile schema (`network/agent_profile.py`): `auth` accepts zero methods and `approval_bypass_env` becomes optional. A profile without methods cannot select provider mode, and its policy file declares no profiles.
- Shared setup (`setup/`): with no authentication method it offers only `offline` and `unrestricted`, defaults to `offline`, and skips the authentication, residual-exfiltration and login steps. Without an approval-bypass variable it skips the permission-bypass question.
- Shared tests: mechanics tests (policy, proxy, session, qualification, setup, toolchains, guard) run against a fixed, agent-neutral fixture profile with a synthetic `.test` provider. A small shared suite validates the real profile and policy of the checkout and skips provider checks when the profile has no methods. Alignment checks require only the variables the wrapper's profile can use.
- Runtime image: same pinned `node:22-bookworm-slim` base and HTTPS apt block as the agent wrappers, keeps the pinned OpenSpec CLI, installs no agent CLI, and uses `bash` as the entrypoint.
- Reference role: `tools/propagate.py`, `docs/propagation.md` and the `reference-propagation` capability name `sandbox-container` as the reference and Claude as one of five adopting wrappers. The five-wrapper parity table gains a reference row.
- Documentation (`README.md`, `AGENTS.md`, `docs/setup.md`, `docs/network-contract.md`, `network/README.md`) describes the shell. History (`docs/validation.md`, archived changes) is kept.
- The change ends with the annotated tag `sandbox-ref-19`. Its adoption by the five wrappers is a separate change in each of them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: Claude home, YOLO and approval wording become the neutral shell; no approval-bypass control exists.
- `container-launcher`: shell entrypoint, `SANDBOX_CONTAINER_*` names, `offline` default instead of missing-mode admission, `provider` rejected.
- `container-podman-access`: same opt-in policy under `SANDBOX_CONTAINER_PODMAN`, no YOLO combinations.
- `container-setup`: questionnaire and readiness for a profile without authentication methods or approval bypass; no login assistance or residual-exfiltration acknowledgement in the reference.
- `host-ca-trust`: neutral variable names and in-container bundle path.
- `network-egress`: provider mode exists only for profiles that declare authentication methods; Claude authentication profiles move out; the profile schema accepts zero methods and an optional approval-bypass variable.
- `persistent-state`: shared and isolated state for the shell home instead of `~/.claude`.
- `reference-propagation`: `sandbox-container` is the reference; the shared fixture profile and the real-profile suite are part of the shared test set.
- `runtime-image`: no agent CLI or CLI-policy version pin; OpenSpec stays pinned; `bash` entrypoint.
- `toolchain-library`: neutral variable and wrapper names.
- `workspace-mounts`: neutral variable and wrapper names.

## Impact

- Code: `sandbox-container.sh` (derived from `claude-container.sh`), `Containerfile`, `.containerignore`, `agent/profile.json`, `agent/policies/default.json`, `network/agent_profile.py`, `network/policy.py`, `setup/common.py`, `setup/setup.py`, `tools/propagate.py`.
- Tests: new `tests/fixtures/` profile tree, `tests/sandbox_profile.py`, every shared test that reads the profile, `test_agent_profile.py`, `test_alignment.py`, `test_propagate.py`; per-wrapper `test_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`, `test_setup_runtime.py`, `test_image_pins.py`, `run-runtime.sh` and `image-smoke.sh` rewritten for the shell.
- Shared files change, so every wrapper must adopt `sandbox-ref-19` with launcher and test adjustments. Claude's adoption also removes its reference-only files.
- Operators: the installation name changes, so setup must be run again; existing `claude-container` installations are unaffected until Claude adopts `sandbox-ref-19`. Nothing is distributed, so no compatibility aliases are provided.
