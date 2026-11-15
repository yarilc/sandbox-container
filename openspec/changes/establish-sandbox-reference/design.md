# Design

## Context

`sandbox-container` main (`9ff66c8`) has the same tree as `claude-container` main (`094ec39`), which is `sandbox-ref-18` plus its archive commit. Everything agent-specific currently reaches shared code through `agent/profile.json` and `agent/policies/default.json`. Shared modules load the profile when they are imported, from `ROOT/agent/profile.json`, where `ROOT` is the parent of the module's directory: `setup/common.py`, `network/session.py` and `network/qualify.py` all do this. Nine shared tests read the profile through `tests/sandbox_profile.py` and derive `HOST`, `NARROW_PROFILE` and `WIDE_PROFILE` from its `auth` methods.

Three assumptions in the shared code block a shell profile today:
- `validate()` requires 1–8 `auth` methods and a non-empty `approval_bypass_env`.
- `policy.load()` requires at least one policy profile.
- `setup/` assumes a provider default (`defaults()`), always asks the authentication and permission-bypass questions, and indexes `PROFILE.auth` for any mode other than offline.

The per-agent files are `claude-container.sh` (947 lines), `Containerfile`, `.containerignore`, `agent/`, and these tests: `test_wrapper.py` (83 tests), `test_runtime.py`, `test_network_runtime.py` with `network_tls_fixture.py`, `test_setup_runtime.py`, `test_image_pins.py`, `run-runtime.sh` and `image-smoke.sh`.

## Goals / Non-Goals

**Goals:**
- A working reference: setup, qualification, offline and unrestricted sessions, toolchains, Podman delegation and host CA trust all pass their runner modes with the shell profile.
- The shared code runs unchanged in all five agent wrappers once they adopt `sandbox-ref-19`, with wrapper-side adjustments only to tests and launchers.
- Shared tests produce the same result whatever profile the checkout has.

**Non-Goals:**
- A shared launcher core. That is phase 2; `sandbox-container.sh` is still a per-wrapper file derived from `claude-container.sh`.
- Adopting `sandbox-ref-19` in any agent wrapper, or removing reference-only files from `claude-container`.
- The golden layer of libraries and tools, and the test-bench role for the agent wrappers.
- Fixing the open review items (M1, M5, M6).

## Decisions

### 1. Reference profile values

| Field | Value |
| --- | --- |
| `name` / `wrapper` | `sandbox-container` / `sandbox-container.sh` |
| `display_name` | `Sandbox` |
| `env_prefix` / `label_namespace` | `SANDBOX_CONTAINER` / `io.sandbox-container` |
| `identifiers` | `["sandbox-container"]` |
| `images` | `localhost/sandbox-container`, `localhost/sandbox-container-egress`, `localhost/sandbox-container-guard-toolchain` |
| `install.state_name` | `sandbox-container-egress` |
| `native.home` / `command` | `/sandbox-home` / `bash` |
| `native.config_dir_env` / `config_home` | `SANDBOX_CONTAINER_CONFIG_DIR` / `.config/sandbox-container` |
| `native.shared_dirs` | `[".config/openspec"]` |
| `native.approval_bypass_env`, `protected_env` | absent |
| `auth` | `{}` |

The identifier is `sandbox-container` and not `sandbox`, because the shared files legitimately contain `sandbox-egress`, `SANDBOX_GUARD_*` and `SANDBOX_TEST_*`. A bare `sandbox` would make the identifier scan fail on every shared file.

`SANDBOX_CONTAINER_` lives inside the neutral `SANDBOX_` namespace that toolchains already cannot set. A new shared alignment test fails if any neutral harness or guard name (`SANDBOX_TEST_*`, `SANDBOX_GUARD_*`, `SANDBOX_RUNTIME_TESTS`, `SANDBOX_QUALIFICATION_*`, `SANDBOX_SETUP_*`, `SANDBOX_TOOLCHAIN_EXAMPLES`, `SANDBOX_IDLE_TESTS`) starts with `SANDBOX_CONTAINER_`. Alternative considered: `SANDBOX_SHELL_` with the wrapper still named `sandbox-container.sh`. Rejected, because the wrapper, project and variables would no longer share one name.

The configuration directory gives shared state a purpose: the image sets `HISTFILE` to `$SANDBOX_CONTAINER_CONFIG_DIR/bash_history`, so history persists in shared and isolated modes, just as Claude state does in the Claude wrapper.

### 2. Schema relaxations stay minimal and explicit

- `auth` accepts 0–8 methods.
- `approval_bypass_env` becomes optional. `Profile.approval_bypass_env` is `None` when it is absent, and every consumer skips it: setup environment, toolchain protected names, alignment variable lists, questionnaire.
- `policy.load()` accepts `profiles: {}` only when the rules passed by the profile have no methods. A profile with methods and an empty policy still fails.
- `session.py prepare/agent-args`, `qualify.py` and setup refuse `provider` for a profile without methods, with one shared message: `profile declares no authentication method`.

Alternative considered: a synthetic `test` method in the shipped shell profile, which the launcher hides. This was rejected during exploration (option A2), because the product would carry a fake provider and setup and qualification would have to ignore it.

### 3. Fixture profile through a fixture tree, never through a variable

`tests/fixtures/agent/profile.json` and `tests/fixtures/agent/policies/default.json` describe a neutral agent:
- name `fixture-agent`, prefix `FIXTURE_AGENT`;
- identifiers `["fixture-agent"]`;
- methods `narrow` (one host, `api.provider.test`) and `wide` (two hosts), with `login_args` on one method and `credential_env` on the other;
- `approval_bypass_env` `FIXTURE_AGENT_YOLO`;
- `protected_env` `["FIXTURE_AGENT_"]`.

A second fixture, `tests/fixtures/shell-agent/` (name `fixture-shell`, no methods, no bypass variable, empty policy profiles), covers the no-method branches of setup, session and qualification. Shared tests therefore never need the reference's own profile to test them.

`tests/sandbox_profile.py` builds, once per test process, a private fixture root under `SANDBOX_TEST_TMPDIR`. The root holds copies of `network/` and `setup/` plus the fixture `agent/`. It puts that root's `network/` and `setup/` first on `sys.path`, so modules that load their profile at import time naturally read the fixture: `ROOT` resolves to the fixture root. It exports `FIXTURE_ROOT` and the fixture-derived names (`PROFILE`, `HOST`, `NARROW_PROFILE`, `WIDE_PROFILE`, `env()`). It also exports `REAL_ROOT` and `REAL_PROFILE` for the checks that must see the checkout itself.

Alternative considered: an environment variable such as `SANDBOX_TEST_PROFILE` read by `agent_profile.load()`. Rejected, because protected production code would gain a profile-selection input. The fixture tree changes no production behavior.

Tests that launch the checkout's wrapper as a subprocess are the exception. Launchers are per-agent files with hard-coded variable names, so a fixture wrapper cannot exist until the phase-2 launcher core, and wrappers differ in mode admission (the reference defaults to offline, agent wrappers refuse a missing mode).
- The eight such tests in `test_setup` (setup entry, missing-mode dispatch, PTY questionnaire, budget plan, cancellation, managed help, rerun and saved-mode admission) move to a new per-agent file, `tests/test_setup_wrapper.py`, outside `SHARED_TESTS`. The reference adapts them to the offline default; each agent wrapper recreates its copy from its previous shared version when it adopts `sandbox-ref-19`.
- The `QualificationRuntime` gate tests in `test_qualification` stay shared and use `REAL_ROOT`, `REAL_PROFILE` and the real wrapper, because `--container-qualify` behaves the same in every wrapper.

The provider behavior these tests covered stays covered at module level with the fixture.

Test ownership after the split:
- **Fixture profile (module-level tests):** `test_network_policy`, `test_session`, `test_qualification`, `test_setup`, `test_toolchains`, `test_guard`, `test_network_feasibility`, `test_mux`, `test_tls_*`. Any test that spawns a shared module uses `FIXTURE_ROOT` paths.
- **Real profile:** `test_agent_profile`, which now validates the checkout's profile and policy, skips method checks when there are no methods, and validates the fixture profile itself. Also `test_alignment`, which runs the identifier scan with the real identifiers plus the fixture identifiers, and checks wrapper/image consistency against the real profile.
- `test_alignment`'s required wrapper variables drop the provider-only suffixes (`NETWORK_PROFILE`, `NETWORK_POLICY`, `NETWORK_RUNTIME_DIR`, `EGRESS_IMAGE`) and the approval variable when the real profile has no methods or no bypass variable.

The two fixture files are listed in `SHARED_TESTS`, so `propagate.py` copies them. The tool resolves shared directories only at the top level (`network/`, `setup/`), so explicit file entries need no change to the tool.

### 4. Shared setup without methods

`setup/common.py` and `setup/setup.py` branch only on `PROFILE.auth` being empty and on `PROFILE.approval_bypass_env` being `None`:
- network choices are `offline` and `unrestricted`, and `defaults()` proposes `offline`;
- no authentication question, residual notice or login step, and authentication status is `not applicable`;
- no permission-bypass question, and `yolo` is saved as `false`;
- `runtime_environment()` omits the bypass variable and the provider-only variables.

The preference schema does not change: `auth` stays `none` and `yolo` stays `false`, so existing agent installations are unaffected.

### 5. The shell launcher is derived from the Claude launcher

`sandbox-container.sh` starts as `claude-container.sh` with these changes:
- the profile names;
- `bash` as the command, with arguments forwarded to it and `--container-shell` accepted as a no-op;
- the YOLO branch, the Claude optional-traffic variables and `ANTHROPIC_API_KEY` forwarding removed;
- the provider branch replaced by a rejection;
- the missing-mode refusal replaced by the offline default plus the protected-installation check (decision 6).

The restricted session flow (`session.py prepare/start/agent-args/stop`), mounts, budgets, toolchains, CA, delegation and lifecycle code stay as they are. This keeps the phase-2 extraction a comparison of six launchers that share their ancestry.

Alternative considered: a minimal launcher written from scratch. Rejected, because it would drop hardening that phase 2 would then have to reconcile.

### 6. Offline default and setup guidance

When the effective mode is empty, the launcher sets it to `offline` and checks for the protected guard manifest in `network/bin` of its own installation before any engine query. If the manifest is missing, it prints a setup-required message naming `--container-setup` and the `SANDBOX_CONTAINER_NETWORK=unrestricted` alternative. Full trusted-path validation still happens later, in `session.py prepare`. The early check exists only to give the actionable message without an engine query.

### 7. Image

The `Containerfile` keeps the pinned base, the HTTPS apt block, the `build-ca` secret and the package list. It drops the Claude npm package and `CLAUDE_*`/`DISABLE_*` variables and keeps `@fission-ai/openspec@1.16.0`. It sets `HOME=/sandbox-home`, `SANDBOX_CONTAINER_CONFIG_DIR` and the `HISTFILE` default, creates `/sandbox-home` and `/workspace` in a layer, keeps copying `relay.py`/`mux.py` to `/opt/sandbox-egress` (the fixture-profile network runtime tests use them), and uses `ENTRYPOINT ["bash"]`. `test_image_pins.py` checks the OpenSpec pin and the base digest; the CLI/policy equality test is removed.

### 8. Reference runtime network tests drive the session helper

The reference wrapper cannot start provider sessions, so `test_network_runtime.py` keeps its controlled TLS, SNI, transport and CA coverage but drives `network/session.py` directly. It does so from a protected fixture installation (the fixture tree with a built guard) using the reference images by immutable ID. The fixture profile's image names are never built or pulled: runtime tests pass image IDs where the helper accepts them and tag the reference images temporarily under the fixture names otherwise, removing the tags afterwards.

### 9. Reference role

- `tools/propagate.py`: the docstring and messages name `sandbox-container`; `MANIFEST_HEAD` drops "Claude reference"; the tool logic is unchanged.
- `docs/propagation.md`: names five targets, Claude included.
- `docs/network-contract.md`: the parity table gets a `sandbox-container` row marked `Reference (sandbox-ref-19)`; the Claude row becomes a target row and keeps its last values (`Ported from sandbox-ref-18`) until Claude adopts `sandbox-ref-19`.
- The README, `AGENTS.md`, `docs/setup.md` and `network/README.md` are rewritten for the shell.
- `docs/validation.md` keeps its history and gains a `sandbox-ref-19` section.

## Risks / Trade-offs

- [The fixture tree diverges from what a wrapper installs] → It is copied from the same `network/` and `setup/` at test time. Only `agent/` differs, and `test_agent_profile` validates both profiles with the same loader.
- [Shared tests that resolve paths from `ROOT` silently keep reading the real profile] → `sandbox_profile.py` makes `ROOT` an alias of `FIXTURE_ROOT`, and a new alignment check fails if a shared test imports `agent_profile` from the checkout path.
- [Every wrapper's adoption of `sandbox-ref-19` gets larger: tests change ownership and the alignment variable list changes] → The tests are shared, so they arrive by propagation. The launchers need no change for the schema relaxations because agent profiles keep their methods and bypass variable.
- [The offline default makes a forgotten mode silently restrictive instead of refused] → That is the intended default for the reference. The Claude-style explicit-mode admission stays in the agent wrappers.
- [The reference can no longer prove end-to-end provider behavior through a real agent CLI] → The production guard, relay and proxy are still exercised through the session helper with the fixture profile. Authenticated checks remain operator-run in each agent wrapper.
- [The Claude-specific history in `docs/validation.md` and the archive can be read as reference evidence] → The new validation section states that earlier entries were recorded for the Claude wrapper.

## Migration Plan

1. Implement on a branch in `sandbox-container`.
2. Build the image with `SANDBOX_CONTAINER_NETWORK=unrestricted SANDBOX_CONTAINER_MAINTENANCE=1`, then run setup on this host.
3. Run every runner mode, since all shared areas change: unit discovery, `--setup`, `--setup-runtime`, `--qualification`, `--guard`, `--network`, `--network-policy`, `--wrapper` and the default runtime mode.
4. Record the results, merge, and create the annotated tag `sandbox-ref-19`. The operator pushes, then runs setup on the Rocky 9 and newer WSL hosts.
5. Archive with spec sync. Each agent wrapper then adopts `sandbox-ref-19` in its own change, Claude first, because its change also removes the reference-only files.

Rollback: `sandbox-ref-18` and every wrapper are untouched until their adoptions, so abandoning the branch restores the previous state.
