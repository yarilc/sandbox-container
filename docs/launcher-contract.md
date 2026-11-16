# Launcher contract

This document is the inventory behind the shared launcher (capability
`shared-launcher`, change `define-launcher-contract`). It lists every
difference between the six launchers and the behavior chosen for the shared
core. A difference kept for one agent names the hook that carries it.

Launchers read: `sandbox-container.sh` and the five agent wrappers'
`<wrapper>-container.sh`, all on `sandbox-ref-21` (2026-11-16). Column
abbreviations: **S** sandbox, **C** Claude, **X** Codex, **A** Antigravity,
**O** OpenCode, **P** Pi. `<P>` stands for each wrapper's variable prefix
(`SANDBOX_CONTAINER`, `CLAUDE_CONTAINER`, ...).

Decision types (design decision 2):

- **same** - same behavior, different code; the core takes the implementation
  named in the cell.
- **union** - a behavior present in some launchers only; the core takes it
  for all.
- **hook** - needed by one agent only; it moves behind the named hook.
- **user** - a conflicting or visible choice, decided by the user; the answer
  is recorded.

## Interface baseline

Source: each launcher's `--container-help`, run with an empty `HOME` and no
engine call, checked against the launcher source.

### Options

| Option | S | C | X | A | O | P | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `--container-setup` | yes | yes | yes | yes | yes | yes | |
| `--container-qualify` | yes | yes | yes | yes | yes | yes | |
| `--container-build` | yes | yes | yes | yes | yes | yes | |
| `--container-shell` | no-op | yes | yes | yes | yes | yes | Bash is the session in S |
| `--container-git-worktree` | yes | yes | yes | yes | yes | yes | |
| `--container-toolchain` | yes | yes | yes | yes | yes | yes | must be first |
| `--container-help` | yes | yes | yes | yes | yes | yes | |
| `--container-qualify-probe` | yes | yes | yes | yes | yes | yes | internal, not in help |

### Common variables

All six launchers accept these `<P>_*` variables with the same values and
defaults. Only the wording differs ("shell", "agent" or "session").

| Variable | Default | Meaning |
| --- | --- | --- |
| `MEMORY_LIMIT` | `4g` | memory budget |
| `CPU_LIMIT` | `2` | CPU budget, up to 3 decimals |
| `PIDS_LIMIT` | `512` | process budget |
| `RUN_TIMEOUT` | `0` (disabled) | container lifetime in whole seconds |
| `ALLOW_UNSAFE_WORKSPACE` | disabled | exact `1` permits a refused sensitive workspace with a warning |
| `TRUST_HOST_CA` | disabled | `1`, `true` or `yes` trusts a host CA bundle |
| `CA_BUNDLE` | first of the two system bundle paths | bundle to trust |
| `TOOLCHAINS` | mounted | `0`, `false` or `no` omits `/toolchains` |
| `TOOLCHAINS_DIR` | `${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains` | shared toolchain library |
| `IMAGE` | profile image | image name |
| `MAINTENANCE` | unset | exact `1` authorizes image preparation |
| `PODMAN` | disabled | exact `1` enables host Podman access |
| `PODMAN_SOCKET` | unset | absolute delegation socket override |
| `QUALIFICATION_INPUT` | unset | internal: qualification probe input |

### Variables with differing meaning or presence

| Variable | S | C | X | A | O | P |
| --- | --- | --- | --- | --- | --- | --- |
| `NETWORK` | offline (default) or unrestricted; provider unavailable | offline, provider or unrestricted; required or supplied by the managed launcher | same as C, "required for every launch" | as X | as X | as X |
| `NETWORK_PROFILE`, `NETWORK_POLICY`, `NETWORK_RUNTIME_DIR`, `EGRESS_IMAGE` | absent (no provider mode) | yes | yes | yes | yes | yes |
| `MAINTENANCE` scope | image preparation | image preparation | image builds and proxy pulls, including a missing image | as X | as X | as X |
| `PODMAN` | requires explicit unrestricted | rejected in offline (wording) | rejected in offline and provider | as X | as X | as X |
| `IMAGE` default tag | `:latest` | `:latest` | `:latest` | `:latest` | `:latest` | no tag (`localhost/pi-container`) |
| `STATE_DIR` | optional isolated home; unset keeps shared configuration | as S | isolated home at `/codex-home`; conflicts with a nonempty `CODEX_HOME` | unset: dedicated home under `~/.local/share/antigravity-container/home`; path: isolated home; empty: shared | persistent isolated home; unset or empty: shared OpenCode directories below an ephemeral home | holds `.pi` and `.agents` instead of `~/.pi` and `~/.agents` |
| `CONFIG_DIR` | shell configuration directory with Bash history (default `~/.config/sandbox-container`) | absent | absent | private directory replacing `~/.gemini` | private directory replacing the shared configuration directory | private directory replacing `~/.pi` |

### Agent-specific variables

| Variable | Wrapper | Meaning |
| --- | --- | --- |
| `YOLO` | O, P | permission bypass (O: auto-approve every request; P: `0/1/true/false/yes/no`, Pi has no approval layer) |
| `PROVIDER` | O | forward one provider's variables by name |
| `ENV_VARS` | O | extra variable names to forward |
| `AGENTS_DIR` | O | exact `1` mounts `~/.agents` read-only |
| `SYSTEM_CONFIG` | O | exact `1` mounts `/etc/opencode` read-only |
| `VERSION` | O | ignored with a notice (`OPENCODE_CONTAINER_VERSION`, `OPENCODE_VERSION`); the version is pinned in `Containerfile` |
| `GITCONFIG` | P | exact `1` mounts `~/.gitconfig` read-only |
| `PI_ENV_VARS` | P | extra variable names to forward (no prefix; same role as O's `ENV_VARS`) |
| `PI_READONLY_CONFIG` | P | nonempty mounts existing `.pi` and `.agents` read-only |
| `PI_NPM_CACHE_SIZE` | P | size of the `~/.npm` tmpfs (default `256M`) |
| `PI_DEBUG` | P | debug output without secret values |
| `EDITOR`, `VISUAL` | P | defaults `nano` inside the session |

The help texts also name native agent variables that the launchers read:
`CLAUDE_CONFIG_DIR`, `CODEX_HOME` (the profiles' `config_dir_env`), the
approval bypass variables, and fixed session settings such as
`AGY_CLI_DISABLE_AUTO_UPDATE`, `OPENCODE_DISABLE_AUTOUPDATE`, `PI_OFFLINE`,
`PI_SKIP_VERSION_CHECK` and `PI_TELEMETRY`.

## Phase 1-2: arguments, help, modes, budgets, lifetime

Profile data already describes several agent differences: `native.approval_bypass_env`
(`CLAUDE_YOLO`, `CODEX_YOLO`, `ANTIGRAVITY_YOLO`, `OPENCODE_CONTAINER_YOLO`,
`PI_CONTAINER_YOLO`; absent in S), `native.config_dir_env` (`SANDBOX_CONTAINER_CONFIG_DIR`,
`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `<P>_CONFIG_DIR` in A, O, P) and the
authentication methods (none in S). The core reads these values through
`agent/launcher.sh` instead of hooks.

| Behavior | S | C | X | A | O | P | Core decision | Hook |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `--container-help` anywhere wins, no engine call | yes | yes | yes | yes | yes | yes, also `--wrapper-help` | same; `--wrapper-help` removed (U2) | - |
| `--container-toolchain` first, execs `setup/toolchains.py` | yes | yes | yes | yes | yes | yes | same | - |
| `--container-qualify` alone, execs `network/qualify.py` | yes | yes | yes | sets the dedicated `STATE_DIR` first | yes | yes | same; A's dedicated home follows the `STATE_DIR` decision of phase 3 | - |
| `--container-setup` alone, interactive, execs `setup/setup.py` | yes | yes | yes | yes | yes | yes | same | - |
| `--container-qualify-probe` alone | yes | yes | yes | yes | yes | yes | same | - |
| `--container-shell` | no-op (session is Bash) | shell mode | shell mode | shell mode | shell mode | shell mode | same; a profile whose command is the shell treats it as a no-op | - |
| `--container-build` alone | builds, then starts | builds, then starts | builds, then starts | builds, then starts | builds, then starts | builds and exits (`build_only`, used by setup) | user (U3): builds and exits for every wrapper | - |
| Remaining arguments | to Bash | to the agent | to the agent | to the agent | to the agent | to the agent | same | `agent_command_args` |
| Missing `<P>_NETWORK` | offline | setup guidance, stop | as C | as C | as C | as C | user (U1): the profile's default mode; `provider` for every agent profile, `offline` for a profile without authentication methods; a default provider launch without its provider settings stops with setup guidance | - |
| Offline without protected installation | setup guidance before engine | (mode required) | (mode required) | (mode required) | (mode required) | (mode required) | union: S's check for every wrapper | - |
| `<P>_NETWORK=provider` | refused: no authentication method | accepted | accepted | accepted | accepted | accepted | same; refused when the profile has no method | - |
| Provider mode requires `NETWORK_PROFILE`, `NETWORK_POLICY`, `NETWORK_RUNTIME_DIR`, `EGRESS_IMAGE` | n/a | yes | yes | yes | yes | yes | same | - |
| `<P>_PODMAN=1` outside unrestricted | refused | refused | refused | refused | refused | refused | same | - |
| Boolean parsing (`1/true/yes`, `''/0/false/no`) | `boolean()` | `boolean()` | `boolean()` | `boolean()` | `case` | `case` | same: `boolean()` | - |
| Empty `<P>_TOOLCHAINS` | mounted | mounted | mounted | **not mounted** (`${...-1}`) | mounted | mounted | same: empty means default (mounted); visible change for A | - |
| Approval bypass variable | n/a | `CLAUDE_YOLO` | `CODEX_YOLO` adds `--yolo` | `ANTIGRAVITY_YOLO` | `OPENCODE_CONTAINER_YOLO`, refused with `OPENCODE_PERMISSION` | `PI_CONTAINER_YOLO`, notice only | union: the core validates the profile's `approval_bypass_env` and never applies it in shell mode | `agent_approval_bypass` |
| `STATE_DIR` with the native config variable | conflict with `CONFIG_DIR` | conflict with `CLAUDE_CONFIG_DIR` | conflict with `CODEX_HOME` | checked later | conflict | conflict | same: conflict with the profile's `config_dir_env` | - |
| `CONFIG_DIR` absolute, no colon, CR or LF | later | n/a | n/a | later | here | here | union, checked here | - |
| `<P>_IMAGE` without whitespace or control characters | no | no | no | no | yes | no | union | - |
| Provider credential follows the network profile | n/a | phase 5 | phase 5 | `GEMINI_API_KEY` for `gemini-api` | per profile | per profile | union from profile data; see phase 5 | - |
| Provider variable forwarding (`PROVIDER`, `ENV_VARS`, reserved names, notices) | no | no | no | no | yes | no | hook | `agent_environment` |
| Opt-in read-only integrations (`AGENTS_DIR`, `SYSTEM_CONFIG`; `GITCONFIG`) | no | no | no | no | yes | yes (phase 5) | hook, see phase 5 | `agent_mounts` |
| Legacy names: `PI_*` aliases (`select_setting`), `PI_NETWORK`, `PI_PULL_ALWAYS`; O deprecated shim and `VERSION` notices | no | no | no | no | yes | yes | user (U2): removed, no compatibility hook | - |
| Budgets and lifetime parsing and messages | identical | identical | identical | identical | identical | identical (via aliases) | same | - |

Covering tests: `test_help_*`, `test_missing_mode_*`, `test_mode_*_rejections_precede_engine`,
`test_boolean_forms_and_invalid_values`, `test_budget_*`, `test_lifetime*`,
`test_shell_does_not_receive_yolo_or_cli_arguments` (C, A), `test_yolo_*` (X, O, P),
`test_provider_*` and `test_deprecated_shim` (O), `test_common_names_and_deprecated_aliases`
and `test_gitconfig_deprecated_alias` (P).

### Decisions (user, 2026-11-16)

- **U1.** The default network mode is profile data. A wrapper with an agent
  (authentication methods in its profile) defaults to `provider`: an agent
  wrapper exists to use its provider's API. The reference shell, with no
  method, defaults to `offline`. Without the provider settings, a default
  launch stops with setup guidance before any engine or state operation.
- **U2.** Legacy names are removed without compatibility hooks: the project
  has no release yet, so backward compatibility is not a goal.
- **U3.** `--container-build` alone builds the image and exits in every
  wrapper; setup relies on it.

## Phase 3-4: workspace, isolated state, engine and cgroup checks

Claude matches the reference line for line here, apart from profile data
(home, `config_home`, shared directories). The table names C only where it
differs.

| Behavior | S | C | X | A | O | P | Core decision | Hook |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sensitive workspace list, home and `/mnt/<letter>` refused, exact `1` override | yes | yes | yes | yes | yes | yes | same | - |
| Host tool checks | podman, GNU timeout, GNU readlink | as S | podman; timeout checked later, no GNU check | podman, timeout without GNU check | podman (exit 127), GNU timeout | podman, timeout, stat, readlink, sha256sum in one loop | union: one early check of every host tool the core uses (podman, GNU timeout, GNU readlink, stat, sha256sum when building) | - |
| `CONTAINER_CONNECTION` refused; `CONTAINER_HOST` only absolute `unix://` beyond `/` | yes | yes | yes | yes | yes | yes | same | - |
| Engine response capture | `capture_response`: keeps final LF, one record | as S | `capture_engine_info`: one LF stripped, CR refused | as X, also refuses several records | `capture_response` plus CR and record checks | as X, every query bounded by `timeout 10s` | union: one capture function that strips one final LF, refuses CR and extra records, and bounds every query with a timeout (P) | - |
| Launch engine check (rootless, Linux, `ServiceIsRemote` true or false, remote only with explicit `unix://`) | whole-string compare | as S | field parse, extra field refused | regex | regex | field parse | same: field parse with extra fields refused (X, P) | - |
| Cgroup controllers, budget flags, notices for unenforced budgets | yes | yes | yes | yes | yes | yes | same | - |
| Restricted modes: host Python, same-host service, backend, version, platform queries; probe needs restricted | yes | yes | yes | yes | yes | yes | same | - |
| Podman delegation socket: override, `unix://` `CONTAINER_HOST`, XDG default; resolved; rootless and host path from the service | yes | yes | yes, clearer messages | yes, regex | yes | yes | same: resolve before the access check (X, O, P) | - |
| `STATE_DIR` lexical check (absolute, no colon, CR or LF) before the engine | no | no | no | yes | yes | yes | union | - |
| `STATE_DIR` must not overlap the workspace (physical paths) | `readlink -m` | as S | as S | parent-aware resolution | as A | as A | same: parent-aware resolution (A, O, P) | - |
| Private directory rule (owner, `077` clear, created with `umask 077`, never repaired) | `private_directory` | as S | `private_state` with per-variable hints | `validate_private` | `check_private_dir` | `validate_state` | same: one function, X's messages | - |
| Default state when `STATE_DIR` is unset | shared native directories | shared | shared (`CODEX_HOME` or `~/.codex`) | **dedicated isolated home** `~/.local/share/antigravity-container/home` | shared (four OpenCode directories) | shared (`~/.pi`, `~/.agents`) | user (U4): shared native directories from the profile for every wrapper; `STATE_DIR` selects an isolated home | - |
| Empty `STATE_DIR` | same as unset | same | same | shared state | same as unset | same as unset | same as unset (U4) | - |
| Shared state sources | profile `config_home` and `shared_dirs` | as S | as S | `.gemini` | as S, `private_shared_dirs` | as S, `private_shared_dirs` | same: from profile data | - |
| `CONFIG_DIR` override of the configuration directory | `SANDBOX_CONTAINER_CONFIG_DIR` | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` | `<P>_CONFIG_DIR`, shared state only | `<P>_CONFIG_DIR` | `<P>_CONFIG_DIR` (`.pi` only) | same: the profile's `config_dir_env` | - |
| Isolated home children and CA mount parent resolved before creation | yes | yes | yes | yes | yes | yes | same | - |
| Read-only state (`PI_READONLY_CONFIG`) | no | no | no | no | no | yes | user (U6): `<P>_READONLY_STATE` in the core for every wrapper | - |
| `ENV_VARS` extra variables by name (`<P>_ENV_VARS`, `PI_ENV_VARS`) | no | no | no | no | yes | yes | user (U5): `<P>_ENV_VARS` in the core for every wrapper; reserved names are core and profile data | - |
| Workspace-derived container name prefix | phase 6 | phase 6 | sanitized basename here | phase 6 | `sanitize_name` here | phase 6 | see phase 6 | - |
| Pi build-only exit before the cgroup checks | n/a | n/a | n/a | n/a | n/a | yes | follows U3: the build-only path needs only the engine check | - |

Covering tests: `test_sensitive_workspaces_refused_before_engine`, `test_state_*`,
`test_*isolated*`, `test_timeout_prerequisite_*`, `test_response_validation*`,
`test_*socket*`, `test_*delegation*`, `test_default_state_and_help_with_invalid_state` (X),
`test_common_names_and_deprecated_aliases` (P).

### Decisions (user, 2026-11-16)

- **U4.** Every wrapper shares the host's native agent directories by default,
  as declared by its profile; `STATE_DIR` selects an isolated home, and an
  empty value means unset. Antigravity loses its dedicated default home.
- **U5.** `<P>_ENV_VARS` forwards listed variable names (never values) in
  every wrapper. Names the core or the agent part sets itself are reserved and
  skipped with a notice.
- **U6.** `<P>_READONLY_STATE` mounts the existing shared or isolated state
  read-only in every wrapper; the state must already exist.

## Phase 5: mounts, toolchains, CA, image

| Behavior | S | C | X | A | O | P | Core decision | Hook |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Toolchain library via `setup/toolchains.py launch-env`, avoiding writable mounts; PATH after the image PATH | yes | yes | yes | yes | yes | yes | same | - |
| Restricted inputs to `network/session.py prepare` (installation, writable paths, mount targets, probe) | yes | yes | yes | yes | yes | yes | same; writable paths come from the core's own mount list | - |
| Hardening flags (`--rm --interactive --read-only`, keep-id user, `--cap-drop=all`, no-new-privileges, budgets) | yes | yes | yes | yes | yes | yes (`ALL`) | same | - |
| `/run/secrets` and `/dev/shm` empty read-only tmpfs | yes | yes | yes | yes | yes | yes | same | - |
| `/tmp` tmpfs | noexec 256m | as S | **exec** 512m | **exec** 512m | **exec** 512m | noexec 256M | user (U7): 512m, `noexec` unless the profile declares executable temporary storage | - |
| `/var/tmp` tmpfs | noexec 256m | as S | **exec** 512m | noexec 512m | noexec 512m | noexec 256M | user (U7): 512m, always `noexec` | - |
| `/run` tmpfs | 16m | 16m | 32m | 32m | 32m | 32M | same: 32m, `noexec` | - |
| Home in shared-state mode | image home (read-only root) | as S | tmpfs, exec, no size | tmpfs, exec, 64m | tmpfs, exec, 512m | tmpfs, **noexec**, 64M, plus `~/.npm` tmpfs (`PI_NPM_CACHE_SIZE`) | union and U7: always a 512m tmpfs home, `noexec` unless the profile declares executable temporary storage; extra agent tmpfs through a hook | `agent_mounts` |
| Native configuration variable inside the session | `SANDBOX_CONTAINER_CONFIG_DIR`, `HISTFILE` | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` | `<P>_CONFIG_DIR` | XDG variables and `<P>_CONFIG_DIR` | none | same: the profile's `config_dir_env` points at `<home>/<config_home>`; other fixed variables through data | `agent_environment` |
| `TERM` forwarded with a terminal | yes | yes | no | yes | no | yes | union | - |
| `EDITOR`, `VISUAL` | `nano` | `nano` | unset | `nano` | unset | host value or `nano` | union: host value or `nano` (P) | - |
| `USER` | unset | unset | unset | unset | host user name | unset | union | - |
| CA bundle at `<home>/ca/bundle.pem` with the four CA variables | yes | yes | yes | yes | yes | yes | same | - |
| Fixed agent settings (telemetry, update, traffic switches) | none | provider mode (6 variables) | none | always (`AGY_CLI_DISABLE_AUTO_UPDATE`, `--unsetenv DBUS_SESSION_BUS_ADDRESS`) | restricted modes (`OPENCODE_DISABLE_*`) | restricted modes (`PI_OFFLINE`, `PI_SKIP_VERSION_CHECK`, `PI_TELEMETRY`) | same: data in `agent/launcher.sh` per scope (always or restricted), applied after every forwarded variable so they win | - |
| Podman delegation mount at `/run/podman/podman.sock`, `CONTAINER_HOST` set; otherwise unset | yes | yes | yes | yes | yes | yes, also unsets `CONTAINER_CONNECTION` | union: unset both | - |
| Provider credential forwarding | n/a | through `session.py` | through `session.py` | profile credential, `GEMINI_API_KEY` in unrestricted | profile credential, `PROVIDER`, `ENV_VARS` | profile credential, `PI_ENV_VARS` | same: the profile credential of the selected method; `ENV_VARS` by U5 | `agent_environment` |
| Opt-in read-only host files (O `AGENTS_DIR`, `SYSTEM_CONFIG`; P `GITCONFIG`) | no | no | no | no | yes | yes | hook | `agent_mounts` |
| Bind validation (absolute, no colon, CR, LF; no shadowing of temporary mounts; destination conflicts) | partial | partial | partial | partial | `add_bind` | partial | union: every bind through one validated builder (O) | - |
| OpenCode labels `io.opencode-container.*` (managed, workspace, workspace name) | no | no | no | no | yes | no | see phase 6 (ownership labels) | - |
| Image build trigger | `--container-build` or missing image | as S | as S | as S, explicit build uses `--no-cache` | as S | as S, plus a stale image is refused (`build-inputs-hash` label) | user (U8): `--container-build` or missing image builds; a stale `build-inputs-hash` is refused with rebuild guidance; no `--no-cache` | - |
| Build arguments | none | none | none | none | none | `PI_VERSION` from `.version`, 300 s timeout | hook | `agent_build_args` |
| Who builds during setup | setup (`recipe`) | setup | setup | setup | setup | wrapper (`runtime_build: wrapper`) | U3 and U8: setup always runs the wrapper's `--container-build`; `runtime_build` leaves the profile | - |
| Build failure reporting | `set -e` | as S | as S | message with status | as S | `die` with timeout hint | same: message with status (A) | - |
| Proxy image present, or pulled by digest only under maintenance | n/a | yes | yes | yes | yes | yes | same | - |
| Restricted runtime image resolved to its ID | yes | yes | yes | yes | yes | yes | same | - |
| Approval bypass effect | n/a | `--dangerously-skip-permissions` | `--yolo` | `--dangerously-skip-permissions` | `OPENCODE_PERMISSION={"*":"allow"}` | notice only | hook (phase 1-2) | `agent_approval_bypass` |
| Shell mode entrypoint | always Bash | `/bin/bash` | `/bin/bash` | `/bin/bash` only unrestricted | `/bin/bash` only unrestricted | see phase 6 | see phase 6 | - |

### Decisions (user, 2026-11-16)

- **U7.** One temporary-storage layout for every wrapper: `/tmp` and
  `/var/tmp` 512m, `/run` 32m, ephemeral home 512m. All are `noexec` by
  default. A profile may declare executable temporary storage, which makes
  `/tmp` and the ephemeral home executable; `/var/tmp` and `/run` stay
  `noexec`. Antigravity and OpenCode declare it (native runtime components,
  OpenTUI shared libraries); Codex declares it only if its adoption shows a
  need.
- **U8.** The core labels every image with `build-inputs-hash` over its build
  inputs and refuses a stale image with rebuild guidance. `--container-build`
  never adds `--no-cache`. Agent build arguments come from `agent_build_args`.
  Setup always builds through the wrapper, so the profile's `runtime_build`
  field is removed.

## Phase 6: creation, budget verification, start

Lifecycle families: **A** = S, C, O (`shutdown`, `control`, immediate
shutdown from the signal trap); **B** = X, A, P (`cleanup`, `record_signal`,
deferred exit at checkpoints).

| Behavior | S | C | X | A | O | P | Core decision | Hook |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Name prefix: sanitized workspace basename with a numeric suffix | fallback wrapper name | as S | as S, computed in phase 3 | as S | `sanitize_name`, fallback `workspace` | as S | same: S, fallback wrapper name | - |
| Ownership label `io.<wrapper>.session=<token>` on create | yes | yes | yes | yes | yes, plus `io.opencode-container.*` labels | yes | same; O's extra labels dropped (unused by any check) | - |
| Private session directory (provider mode: inside `NETWORK_RUNTIME_DIR`) | `mktemp -d` | as X | yes | yes | yes | yes | same | - |
| Network mode notice on stderr | yes | yes | yes | yes | yes | yes | same | - |
| Restricted launch requires a current qualification (`qualify.py check`) | yes | yes | yes | yes | yes | yes | same | - |
| Provider proxy started by `session.py start` in its own process group | n/a | yes | yes | yes | yes | yes | same | - |
| Restricted application command | `/bin/bash` + args | shell: `/bin/bash` without args; agent: `/usr/local/bin/claude` + args | shell as C; agent: `codex --no-daemon -c sandbox_mode=...` plus provider-only `-c` overrides | as C | as C | as C | same: shell mode runs the profile shell with the arguments (S); the agent command comes from the profile | `agent_command_args` (mode-specific protected arguments, X) |
| Provider credential variable | n/a | `ANTHROPIC_API_KEY` | `OPENAI_API_KEY` for the API profiles | profile credential | profile credential | profile credential | same: the `credential_env` of the selected authentication method | - |
| Name reservation by `create`, up to 20 attempts; another session's name advances the index | yes | yes | yes | yes | yes | yes | same | - |
| Create interruptible (background client, `wait`) | yes | yes | `wait_for_create` | yes | yes | `wait_for_create` | same | - |
| Own container behind a failed create (name owned by this session) | reported, recovered by label at shutdown | as S | `owned_collision`, reported as unresolved if not recovered | as X | tested (`test_owned_name_is_not_a_collision`) | as X | union: never treated as a collision; removed, or reported as unresolved | - |
| CID record validation (64 hex, single record, no NUL) | regex on the file | as S | `recover_container_id` (NUL and LF aware) | as X | `read_cid` | as X | same: X | - |
| Budget verification of the created configuration before start | yes | yes | yes | yes | yes | yes | same | - |
| Start: `podman start --attach --interactive --sig-proxy=false`, stdin kept, optional diagnostics filter | yes | yes | yes | yes | yes | yes | same | - |
| Lifetime notice (monotonic clock from before create) | yes | yes | yes | yes | yes | yes | same | - |

## Phase 7: signals, shutdown, recovery

| Behavior | S | C | X | A | O | P | Core decision | Hook |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Signal model | trap runs `shutdown` at once | as S | first signal recorded; exit when a client or helper is waited on, otherwise at the next checkpoint | as X | as S | as X | user (U9): family A, immediate shutdown from the trap | - |
| Shutdown budget | 20 s shared deadline; each engine call gets the remaining time (`control`) | as S | 20 s for the proxy stop; each engine call a fixed 5 s timeout | as X | as S | as X | user (U9): one 20 s deadline shared by every shutdown engine call | - |
| Signal forwarded to an attached session, then forced removal | `podman kill`, 5 s grace | as S | as S | as S | as S | as S | same | - |
| Owned container removed (`rm --force --time 0 --ignore`), failures reported without changing the status | yes | yes | yes | yes | yes | yes | same | - |
| Recovery of an interrupted creation: CID record, create output, then ownership label lookup confirmed by inspect | yes | yes | CID record, then label lookup | as X | as S | as X | same: S's order, X's record validation | - |
| Restricted helpers (qualification check, proxy start) stopped with TERM, grace, KILL | yes | yes, process group | yes, process group | yes | yes | yes | same: process group for the proxy helper | - |
| Diagnostics filter drained before it is reaped | yes | yes | yes | yes | yes | yes | same | - |
| Provider proxy stopped by `session.py stop` within the remaining budget | n/a | yes | yes | yes | yes | yes | same | - |
| Exit status: the application's, or the first signal's | yes | yes | yes | yes | yes | yes | same | - |

Covering tests (both families): `test_exit_status_and_owned_cleanup`,
`test_*collision*`, `test_owned_name_is_not_a_collision` (X, A, O, P),
`test_interrupted_creation_*`, `test_*signal*`, `test_stalled_creation_*`,
`test_stubborn_application_and_stalled_cleanup_are_bounded` (X, P),
`test_cleanup_failure_or_stall_preserves_application_status` (S, C),
`test_interrupted_restricted_helpers_*` (X, O).

### Decisions (user, 2026-11-16)

- **U9.** The core uses family A's lifecycle: the signal trap starts shutdown
  at once, and every shutdown engine call takes the time left in one 20 s
  deadline. It adds family B's CID record validation and its explicit handling
  of this session's own container behind a failed create. The signal, stall
  and collision tests of both families become shared core tests.

## Wrapper tests

Every case is listed in `docs/launcher-test-map.md` with its phase and
destination. Totals (488 cases):

| Repository | Cases | Shared | Shared (duplicate) | Hook | Obsolete | Fake engine |
| --- | --- | --- | --- | --- | --- | --- |
| S | 80 | 80 | 0 | 0 | 0 | 0 |
| C | 83 | 5 | 74 | 4 | 0 | 0 |
| X | 85 | 71 | 10 | 4 | 0 | 0 |
| A | 80 | 28 | 46 | 5 | 1 | 0 |
| O | 69 | 22 | 32 | 11 | 3 | 1 |
| P | 91 | 15 | 62 | 8 | 3 | 3 |

The shared suite starts from the reference's 80 cases (family A) and adds the
cases only family B or OpenCode cover, for example `test_owned_name_is_not_a_collision`,
`test_extra_launch_records_are_not_trimmed`, `test_tmpfs_capacities_and_options`
and Pi's image freshness and build-only cases. Same-named duplicates are merged;
differently named duplicates are merged when the tests move.

### Fake engine

| | S | C | X | A | O | P |
| --- | --- | --- | --- | --- | --- | --- |
| Location | embedded in `test_wrapper.py` | embedded | embedded | `tests/fake_podman.py` | embedded | `tests/fake_podman.py` |
| Engine commands | build, create, exec, info, inspect, kill, ps, rm, start, version | as S | as S plus image, pull, run | as X | as X | as X |
| `FAKE_*` controls | 37 | 37 | 49 | 48 | 50 | 54 |

The 83 distinct controls form the union the shared fake must support where a
shared test uses them. Only OpenCode (`FAKE_CREATE_WARNING`, `FAKE_NAME_OWNER_STATUS`,
`FAKE_OWNER`, `FAKE_PS_STATUS`, `FAKE_RECOVER_IDS`) and Pi (`FAKE_BUDGET_INSPECT_STATUS`,
`FAKE_BUILD_READ_INPUT`, `FAKE_FAIL_WITH_CID`, `FAKE_LABEL_HASH`, `FAKE_ROOT`) have
controls no other fake has. The shared fake is a separate file,
`tests/fake_podman.py`, as in Antigravity and Pi, so tests and the runtime
harness can import it; it rejects unknown commands (Pi's
`test_fixture_rejects_unknown_and_preserves_records`).

## Contract

### Files

| File | Owner | Content |
| --- | --- | --- |
| `<wrapper>-container.sh` | wrapper (identical in every wrapper up to its name) | resolves its own path with GNU `readlink -f` and runs `source "$dir/launcher/core.sh" "$dir/agent/launcher.sh" "$@"`; nothing else |
| `launcher/core.sh` | shared, reference copy | the whole launcher: phases 1-7 of this document |
| `agent/launcher.sh` | wrapper | the profile data the core needs and the agent hooks |
| `agent/profile.json` | wrapper | unchanged role; new field `native.exec_tmp` (U7); `install.runtime_build` removed (U8) |
| `tests/fake_podman.py` | shared | the fake engine |
| `tests/test_launcher.py` | shared | the shared launcher tests, run with a fixture `agent/launcher.sh` |
| `tests/test_wrapper.py` | wrapper | hook and agent data tests only |

The entry script keeps its name, so `setup/launch.py`, the managed launchers
and every documented command are unchanged.

### Profile data in `agent/launcher.sh`

Plain Bash assignments, no logic. A shared alignment test loads the file in a
clean Bash and compares each value with `agent/profile.json`.

| Variable | Profile source |
| --- | --- |
| `AGENT_NAME`, `AGENT_DISPLAY_NAME` | `name`, `display_name` |
| `AGENT_WRAPPER` | `wrapper` |
| `AGENT_ENV_PREFIX` | `env_prefix` |
| `AGENT_LABEL_NAMESPACE` | `label_namespace` |
| `AGENT_IMAGE`, `AGENT_PROXY_IMAGE` | `images.agent`, `images.proxy` |
| `AGENT_HOME`, `AGENT_COMMAND` | `native.home`, `native.command` |
| `AGENT_CONFIG_DIR_ENV`, `AGENT_CONFIG_HOME` | `native.config_dir_env`, `native.config_home` |
| `AGENT_SHARED_DIRS` (array), `AGENT_PRIVATE_SHARED_DIRS` | `native.shared_dirs`, `native.private_shared_dirs` |
| `AGENT_APPROVAL_BYPASS_ENV` | `native.approval_bypass_env` (empty when absent) |
| `AGENT_EXEC_TMP` | `native.exec_tmp` (U7) |
| `AGENT_CREDENTIALS` (array of `policy_profile=credential_env`) | `auth.*` |

Agent data with no profile counterpart:

| Variable | Meaning |
| --- | --- |
| `AGENT_SESSION_ENV` (array `NAME=VALUE`) | fixed agent settings for every session |
| `AGENT_RESTRICTED_ENV` (array `NAME=VALUE`) | fixed agent settings for offline and provider sessions |
| `AGENT_UNSET_ENV` (array) | variables removed from every session (A: `DBUS_SESSION_BUS_ADDRESS`) |
| `AGENT_RESERVED_ENV` (array) | names the agent part sets; `<P>_ENV_VARS` skips them (U5) |

Derived by the core, never declared: the default network mode (`provider`
when `AGENT_CREDENTIALS` is not empty, otherwise `offline`; U1), whether
`--container-shell` is a no-op (`AGENT_COMMAND` is the shell), and every
`<P>_*` variable name.

### Hooks

Hooks are optional Bash functions in `agent/launcher.sh`. The core calls
each at one point, passes inputs as arguments and reads the outputs from the
named arrays, which the core empties before the call. A hook returns 0; any
other status stops the launch with `hook <name> failed`. A hook may call `die`,
may read the core state listed below and must not change any other variable.

| Hook | Called | Inputs | Output | Core refuses | Default |
| --- | --- | --- | --- | --- | --- |
| `agent_help` | by `--container-help`, after the common variables | - | text on stdout | - | nothing |
| `agent_validate` | after the common settings, before any engine or state operation (phase 2) | mode | none; may print notices or `die` | - | nothing |
| `agent_approval_bypass` | when `AGENT_APPROVAL_BYPASS_ENV` is enabled, not in shell mode | mode | `agent_bypass_args`, `agent_bypass_env` | `NAME` reserved by the core | bypass ignored with a notice |
| `agent_command_args` | when the application command is built, not in shell mode | mode | `agent_mode_args`, placed before the user's arguments | - | none |
| `agent_environment` | when the session environment is built (phase 5) | mode | `agent_env` (`NAME` or `NAME=VALUE`) | names the core sets (`HOME`, `USER`, `TERM`, `EDITOR`, `VISUAL`, `PATH`, the CA and proxy variables, `CONTAINER_HOST`, the config variable) | none |
| `agent_mounts` | after the state mounts (phase 5) | mode, home | `agent_mount_specs` entries `ro:<source>:<destination>` or `tmpfs:<destination>:<size>` | writable binds; relative paths; colon, CR or LF; a destination that shadows or contains `/tmp`, `/var/tmp`, `/run`, the workspace, `/toolchains`, the CA file or another mount; a missing source | none |
| `agent_build_args` | before every build and before the freshness check (U8) | - | `agent_build_args` (`NAME=VALUE`), `agent_build_inputs` (files inside the installation, added to `build-inputs-hash`) | values with CR or LF; inputs outside the installation | none |

Core state a hook may read: `network_mode`, `shell_mode`, `restricted`,
`workspace`, `workspace_mount`, `state_dir` (empty in shared mode),
`script_dir`, `caller_uid`, `caller_gid`, and every `AGENT_*` value.

Agent tmpfs mounts get `rw,noexec,nosuid,nodev,mode=0700,U` and the given
size.

### Agent-specific helpers

| Helper today | Destination |
| --- | --- |
| O `add_bind`, `valid_bind_path` | core bind builder (every mount, phase 5) |
| O `opt_in_integration` (`AGENTS_DIR`, `SYSTEM_CONFIG`) | `agent_validate` and `agent_mounts` |
| O `shared_state` | core shared state from `AGENT_SHARED_DIRS` and `AGENT_PRIVATE_SHARED_DIRS` |
| O `build_current_image` | core build |
| O `PROVIDER`, `ENV_VARS` reserved names, `OPENCODE_PERMISSION` check, XDG variables | `agent_validate`, `agent_environment`, `AGENT_RESERVED_ENV`; `ENV_VARS` itself is core (U5) |
| P `select_ca_bundle` | core CA selection, done before the build-only exit |
| P `build_runtime_image` | core build plus `agent_build_args` (`PI_VERSION` from `.version`, which is a build input) |
| P `select_setting` | removed (U2) |
| P `debug` (`PI_DEBUG`) | `agent_validate` |
| P `~/.npm` tmpfs (`PI_NPM_CACHE_SIZE`), `GITCONFIG` | `agent_validate` and `agent_mounts` |
| X protected `-c` overrides, `--no-daemon` | `agent_command_args` |
| C, A `--dangerously-skip-permissions`; X `--yolo`; O `OPENCODE_PERMISSION`; P notice | `agent_approval_bypass` |

Hooks never run during shutdown, never see the session token or container
ID, and cannot add engine flags other than those their outputs describe.

## Visible changes

Behavior that changes for users of at least one wrapper when it adopts the
core. Each entry is also a `container-launcher` delta.

| Change | Wrappers affected | Source |
| --- | --- | --- |
| A missing `<P>_NETWORK` selects `provider`; without provider settings the launch stops with setup guidance | C, X, A, O, P | U1 |
| Legacy names removed: Pi `PI_*` aliases, `PI_NETWORK`, `PI_PULL_ALWAYS`, `--wrapper-help`; OpenCode `opencode-wrapper` shim and version-variable notices | O, P | U2 |
| `--container-build` alone builds and exits | S, C, X, A, O | U3 |
| An empty `<P>_TOOLCHAINS` mounts the library (default) | A | phase 1-2 |
| `<P>_IMAGE` with whitespace or control characters is refused | S, C, X, A, P | phase 1-2 |
| `CONFIG_DIR` must be absolute without colon, CR or LF, checked before the engine | S, A | phase 1-2 |
| Antigravity shares `~/.gemini` by default; its dedicated home is no longer used | A | U4 |
| `<P>_ENV_VARS` forwards listed variable names | S, C, X, A; P renamed from `PI_ENV_VARS` | U5 |
| `<P>_READONLY_STATE` mounts existing state read-only | S, C, X, A, O; P renamed from `PI_READONLY_CONFIG` | U6 |
| Every engine query is bounded by a timeout | S, C, X, A, O | phase 3-4 |
| One temporary-storage layout; `exec` only where the profile declares it | all | U7 |
| A stale image is refused until rebuilt; Antigravity's explicit build no longer skips the cache | all | U8 |
| `TERM`, `EDITOR`/`VISUAL` (host value or `nano`) and `USER` set in every session | X, O (TERM, EDITOR); all but O (USER) | phase 5 |
| Shutdown is bounded by one 20 s deadline | X, A, P | U9 |
| Shell mode in restricted modes passes its arguments to the shell | C, X, A, O, P | phase 6 |

## Spec deltas for the implementation change

This change (`define-launcher-contract`) changes no spec. The change that
implements the core writes these deltas, so the specs move with the code.
Behavior that changes only for agent wrappers is specified by each wrapper's
adoption change; the reference rows are marked "reference: none".

| Source | Capability | Requirement | Delta |
| --- | --- | --- | --- |
| contract | `shared-launcher` (new) | One shared launcher core; Thin wrapper entry script; Agent launcher part consistent with the profile; Common launcher interface; Bounded agent hooks; Shared launcher tests; Recorded launcher differences | ADDED: the core, entry script, `agent/launcher.sh` data and hooks, common interface, hook refusal rules, shared tests with the shared fake engine |
| contract | `reference-propagation` | Exact propagation within the adopted scope | MODIFIED: the copied scope includes `launcher/`, `tests/test_launcher.py` and `tests/fake_podman.py` |
| U1 | `container-launcher` | Offline is the default runtime mode | reference: none (a profile without methods keeps `offline`); each agent adoption MODIFIES its required-mode requirement to "provider by default" |
| U2 | wrapper specs | legacy names | reference: none; O and P adoptions REMOVE their alias, shim and notice requirements |
| U3 | `container-launcher` | Predictable image operations | MODIFIED: `--container-build` alone builds and exits without a session |
| U3, U8 | `container-setup` | Mode-specific image and guard preparation; Wrapper-built runtime receives host CA trust | MODIFIED: setup always builds through the wrapper's build-only operation; `runtime_build` removed from the profile |
| U4 | `persistent-state` | Shared shell state by default | reference: none (already shared); the Antigravity adoption MODIFIES its default-state requirement |
| U5 | `container-launcher` | Extra variables forwarded by name | ADDED: `<P>_ENV_VARS` forwards listed names, never values, and skips reserved names with a notice |
| U6 | `persistent-state` | Read-only state | ADDED: `<P>_READONLY_STATE` mounts existing shared or isolated state read-only and refuses missing state |
| U7 | `container-isolation` | Ephemeral constrained temporary storage | MODIFIED: `/tmp` and `/var/tmp` 512 MiB, `/run` 32 MiB, ephemeral home 512 MiB; `noexec` unless the profile declares executable temporary storage, which applies to `/tmp` and the home only |
| U7 | `persistent-state` | Shared shell state by default | MODIFIED: shared-state sessions mount a tmpfs home below the shared directories |
| U8 | `container-launcher` | Predictable image operations | MODIFIED: images carry `build-inputs-hash`; a stale image is refused with rebuild guidance; explicit builds use the cache |
| phase 1-2 | `container-launcher` | Predictable image operations | MODIFIED: an image name with whitespace or control characters is refused before any engine operation |
| phase 1-2 | `persistent-state` | Resolved state paths and isolation scope | MODIFIED: `STATE_DIR` and the configuration override are absolute, without colon, CR or LF, checked before the engine |
| phase 3-4 | `container-launcher` | Verified launch engine | MODIFIED: every engine query is bounded by a timeout; responses with CR or extra records are refused |
| phase 5 | `container-launcher` | Transparent invocation and terminal handling | MODIFIED: `USER` is set; `EDITOR` and `VISUAL` keep the host value or default to `nano` |
| phase 1-2 (A) | wrapper specs | toolchain switch | reference: none; the Antigravity adoption treats an empty `<P>_TOOLCHAINS` as the default |
| U9 | `container-launcher` | Bounded session shutdown | reference: none (already family A); X, A and P adoptions state the shared 20 s deadline |
| phase 6 | `container-launcher` | Owned container lifecycle | MODIFIED: a failed create whose name holds this session's container is never a collision; that container is removed or reported unresolved |
| phase 6 | wrapper specs | restricted shell mode | reference: none; C, X, A, O and P adoptions pass shell-mode arguments to the shell in restricted modes |

Every row of "Visible changes" maps to a row here.
