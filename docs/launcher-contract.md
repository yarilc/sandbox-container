# Launcher contract

> Implemented by change `implement-shared-launcher` (`launcher/core.sh`,
> `tests/test_launcher.py`); the agent wrappers adopt it by tag.

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
| `MAINTENANCE` scope | image preparation | image preparation and proxy pulls | image builds and proxy pulls, including a missing image | as X | as X | as X |
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
| Approval bypass variable | n/a | `CLAUDE_YOLO` | `CODEX_YOLO` adds `--yolo` | `ANTIGRAVITY_YOLO` | `OPENCODE_CONTAINER_YOLO`, refused with `OPENCODE_PERMISSION`, applied in shell mode too | `PI_CONTAINER_YOLO`, notice only | union: the core validates the profile's `approval_bypass_env` and never applies it in shell mode (visible for O) | `agent_approval_bypass` |
| `STATE_DIR` with the native config variable | conflict with `CONFIG_DIR` | conflict with `CLAUDE_CONFIG_DIR` | conflict with `CODEX_HOME` | checked later | conflict | conflict | same: conflict with the profile's `config_dir_env` | - |
| Configuration override (`config_dir_env`) absolute, no colon, CR or LF | never | never (`CLAUDE_CONFIG_DIR`) | never (`CODEX_HOME`) | here | here | here | union, checked here for every profile's `config_dir_env` (M14) | - |
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
  From the Windows entry the guidance names the Windows setup step
  ("Bootstrap" under "Windows entry" below).
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
| Windows folders on a drive mount (`Users`, every profile, its `Documents`, `OneDrive` and `OneDrive/Documents`, everything in its `AppData`, `Windows`, `Program Files`, `Program Files (x86)`, `ProgramData`) refused case-insensitively | no | no | no | no | no | no | added for Windows support: exact roots only, same override | - |
| Host tool checks | podman, GNU timeout, GNU readlink | as S | podman; timeout checked later, no GNU check | podman, timeout without GNU check | podman (exit 127), GNU timeout | podman, timeout, stat, readlink, sha256sum in one loop | union: one early check of every host tool the core uses (podman, GNU timeout, GNU readlink, stat, sha256sum when building) | - |
| `CONTAINER_CONNECTION` refused; `CONTAINER_HOST` only absolute `unix://` beyond `/` | yes | yes | yes | yes | yes | yes | same | - |
| Engine response capture | `capture_response`: keeps final LF, one record | as S | `capture_engine_info`: one LF stripped, CR refused | as X, also refuses several records | `capture_response` plus CR and record checks | as X, every query bounded by `timeout 10s` | union: one capture function that strips one final LF, refuses CR and extra records, and bounds every query with a timeout (P) | - |
| Launch engine check (rootless, Linux, `ServiceIsRemote` true or false, remote only with explicit `unix://`) | whole-string compare | as S | field parse, extra field refused | regex | regex | field parse | same: field parse with extra fields refused (X, P) | - |
| Cgroup controllers, budget flags, notices for unenforced budgets | yes | yes | yes | yes | yes | yes | same | - |
| Restricted modes: host Python, same-host service, backend, version, platform queries; probe needs restricted | yes | yes | yes | yes | yes | yes | same | - |
| Podman delegation socket: override, `unix://` `CONTAINER_HOST`, XDG default; resolved; rootless and host path from the service | yes | yes | yes, clearer messages | yes, regex | yes | yes | same: resolve before the access check (X, O, P); the reported host path is never slash-only and, when visible to the wrapper, must be a socket (`verify-delegated-socket-path`) | - |
| `STATE_DIR` lexical check (absolute, no colon, CR or LF) before the engine | no | no | no | yes | yes | yes | union | - |
| `STATE_DIR` must not overlap the workspace (physical paths) | `readlink -m` | as S | as S | parent-aware resolution | as A | as A | same: parent-aware resolution (A, O, P) | - |
| Private directory rule (owner, `077` clear, created with `umask 077`, never repaired) | `private_directory` | as S | `private_state` with per-variable hints | `validate_private` | `check_private_dir` | `validate_state` | same: one function, X's messages | - |
| Default state when `STATE_DIR` is unset | shared native directories | shared | shared (`CODEX_HOME` or `~/.codex`) | **dedicated isolated home** `~/.local/share/antigravity-container/home` | shared (four OpenCode directories) | shared (`~/.pi`, `~/.agents`) | user (U4): shared native directories from the profile for every wrapper; `STATE_DIR` selects an isolated home | - |
| Empty `STATE_DIR` | same as unset | same | same | shared state | same as unset | same as unset | same as unset (U4) | - |
| Shared state sources | profile `config_home` and `shared_dirs` | as S | as S | `.gemini` | as S, `private_shared_dirs` | as S, `private_shared_dirs` | same: from profile data | - |
| `CONFIG_DIR` override of the configuration directory | `SANDBOX_CONTAINER_CONFIG_DIR` | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` | `<P>_CONFIG_DIR`, shared state only | `<P>_CONFIG_DIR` | `<P>_CONFIG_DIR` (`.pi` only) | same: the profile's `config_dir_env` | - |
| Isolated home children and CA mount parent resolved before creation | children contained; `.config/openspec` privacy not checked; `ca` created without containment check | as S | contained, private | `.gemini`: only `! -L`, privacy not checked, existing 0755 kept | `mkdir -p`, no containment check | private, containment not checked | union (M4): every child contained and private | - |
| Read-only state (`PI_READONLY_CONFIG`) | no | no | no | no | no | yes | user (U6): `<P>_READONLY_STATE` in the core for every wrapper | - |
| `ENV_VARS` extra variables by name (`<P>_ENV_VARS`, `PI_ENV_VARS`) | no | no | no | no | yes | yes | user (U5): `<P>_ENV_VARS` in the core for every wrapper; reserved names are core and profile data | - |
| Workspace-derived container name prefix | phase 6 | phase 6 | sanitized basename here | phase 6 | `sanitize_name` here | phase 6 | see phase 6 | - |
| Pi build-only exit before the cgroup checks | n/a | n/a | n/a | n/a | n/a | yes | follows U3: the build-only path needs only the engine check | - |

Covering tests: `test_sensitive_workspaces_refused_before_engine`,
`test_windows_system_and_profile_folders_refused_before_engine`, `test_state_*`,
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
| Native configuration variable inside the session | `SANDBOX_CONTAINER_CONFIG_DIR`, `HISTFILE` | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` | `<P>_CONFIG_DIR` | XDG variables and `<P>_CONFIG_DIR` | `PI_CONTAINER_CONFIG_DIR=/pi-home/.pi` | same: the profile's `config_dir_env` points at `<home>/<config_home>`; other fixed variables through data | `agent_environment` |
| `TERM` forwarded | with a terminal | with a terminal | no | with a terminal | whenever set (base allowlist with `COLORTERM`, `LANG`, `LC_ALL`) | with a terminal | union (U11): `TERM`, `COLORTERM`, `LANG`, `LC_ALL` whenever set | - |
| `EDITOR`, `VISUAL` | `nano` | `nano` | unset | `nano` | unset | host value or `nano` | user (U15): always `nano`, as the `runtime-image` spec requires | - |
| `USER` | unset | unset | unset | unset | host user name | unset | union | - |
| CA bundle at `<home>/ca/bundle.pem` with the four CA variables | yes | yes | yes | yes | yes | yes | same | - |
| Fixed agent settings (telemetry, update, traffic switches) | `HISTFILE` (and the config variable) | provider mode (6 variables) | none | always (`AGY_CLI_DISABLE_AUTO_UPDATE`, `--unsetenv DBUS_SESSION_BUS_ADDRESS`) | restricted modes (`OPENCODE_DISABLE_*`) | restricted modes (`PI_OFFLINE`, `PI_SKIP_VERSION_CHECK`, `PI_TELEMETRY`) | same: data in `agent/launcher.sh` per scope (always, restricted, provider; M2), applied after every forwarded variable so they win; S declares `HISTFILE` in `AGENT_SESSION_ENV` | - |
| Podman delegation mount at `/run/podman/podman.sock`, `CONTAINER_HOST` set; otherwise unset | yes | yes | yes | yes | yes | yes, also unsets `CONTAINER_CONNECTION` | union: unset both | - |
| Credential forwarding | n/a | own `--env ANTHROPIC_API_KEY` in provider mode, both policy profiles; none unrestricted | own `--env OPENAI_API_KEY` for `openai-api` and `openai-api-docs`; none unrestricted | profile credential; `GEMINI_API_KEY` unrestricted | profile credential; `PROVIDER` names unrestricted | profile credential; `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` unrestricted | user (U10): provider forwards the `credential_env` of the selected policy profile's method only; unrestricted forwards none (use `<P>_ENV_VARS`) | `agent_environment` (O `PROVIDER`) |
| Opt-in read-only host files (O `AGENTS_DIR`, `SYSTEM_CONFIG`; P `GITCONFIG`) | no | no | no | no | yes | yes | hook | `agent_mounts` |
| OpenCode native-variable allowlist (`OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR`, `OPENCODE_CONFIG_CONTENT`, `OPENCODE_PERMISSION`, `OPENCODE_SERVER_USERNAME`, `OPENCODE_SERVER_PASSWORD`, `OPENCODE_DISABLE_*` outside restricted modes) forwarded by name | no | no | no | no | yes | no | hook (H-g) | `agent_environment` (`NAME` entries) |
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
| Name prefix: sanitized workspace basename with a numeric suffix | fallback wrapper name | as S | as S, computed in phase 3 | as S | `sanitize_name` (also strips `_`), fallback `workspace` | as S, truncated to 64 characters with `LC_ALL=C` | same: S, fallback `AGENT_NAME`, truncated to 64 characters (P) | - |
| Ownership label `io.<wrapper>.session=<token>` on create | yes | yes | yes | yes | yes, plus `io.opencode-container.*` labels | yes | same; O's extra labels dropped (unused by any check) | - |
| Private session directory (provider mode: inside `NETWORK_RUNTIME_DIR`) | `mktemp -d` | as X | yes | yes | yes | yes | same | - |
| Network mode notice on stderr | yes | yes | yes | yes | yes | yes | same | - |
| Restricted launch requires a current qualification (`qualify.py check`) | yes | yes | yes | yes | yes | yes | same | - |
| Provider proxy started by `session.py start` in its own process group | n/a | yes | yes | yes | yes | yes | same | - |
| Application command | `/bin/bash` + args in every mode | shell: `/bin/bash`, args dropped in every mode; agent restricted: `/usr/local/bin/claude` + args; agent unrestricted: image `ENTRYPOINT` | shell as C; agent restricted: `codex --no-daemon -c sandbox_mode=...` plus provider-only `-c` overrides | shell as C; agent restricted: `/usr/local/bin/antigravity-entrypoint` (D-Bus, keyring, remote sign-in) | as C (`/usr/local/bin/opencode`) | as C (`/usr/local/bin/pi`) | U14: shell mode runs the shell with the arguments in every mode; H2: restricted agent sessions run `AGENT_EXEC`, unrestricted ones the image `ENTRYPOINT` | `agent_command_args` (mode-specific protected arguments, X) |
| Provider credential variable | n/a | `ANTHROPIC_API_KEY` | `OPENAI_API_KEY` for the API profiles | profile credential | profile credential | profile credential | U10: from `AGENT_CREDENTIALS`, keyed by policy profile | - |
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
| Shutdown budget | 20 s shared deadline; each engine call at most 2 s within it (`control`) | as S | 20 s for the proxy stop; each engine call a fixed 5 s timeout | as X | as S | as X | user (U9): one 20 s deadline; each shutdown engine call bounded by min(2 s, time left minus the reserve for local clients) (M1) | - |
| Signal forwarded to an attached session, then forced removal | `podman kill`, 5 s grace | as S | as S | as S | as S | as S | same | - |
| Owned container removed (`rm --force --time 0 --ignore`), failures reported without changing the status | yes | yes | yes | yes | yes | yes | same | - |
| Recovery of an interrupted creation: CID record, create output, then ownership label lookup confirmed by inspect | yes | yes | CID record, then label lookup | as X | CID record cross-checked with the create output ("inconsistent creation IDs"), then label lookup | as X | same: S's order, X's record validation, O's cross-check | - |
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
  at once, and every shutdown engine call is bounded by min(2 s, time left in
  one 20 s deadline minus the reserve for local clients). It adds family B's CID record validation and its explicit handling
  of this session's own container behind a failed create. The signal, stall
  and collision tests of both families become shared core tests.

## Wrapper tests

Every case is listed in `docs/launcher-test-map.md` with its phase and
destination. Totals (488 cases):

| Repository | Cases | Shared | Shared (rewrite) | Shared (duplicate) | Hook | Obsolete | Fake engine |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S | 80 | 73 | 7 | 0 | 0 | 0 | 0 |
| C | 83 | 4 | 9 | 67 | 3 | 0 | 0 |
| X | 85 | 64 | 8 | 10 | 3 | 0 | 0 |
| A | 80 | 26 | 7 | 45 | 2 | 0 | 0 |
| O | 69 | 21 | 5 | 30 | 10 | 2 | 1 |
| P | 91 | 15 | 5 | 59 | 6 | 3 | 3 |

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
| `<wrapper>-container.sh` | wrapper (identical in every wrapper up to its name) | sets `set -Eeuo pipefail`, keeps the invoked path in `WRAPPER_INVOKED=${BASH_SOURCE[0]}`, resolves its own directory with GNU `readlink -f` or, when readlink is missing, with `${BASH_SOURCE[0]%/*}` (the core reports the missing tool later, in S's order; H-b), and runs `source "$dir/launcher/core.sh" "$dir/agent/launcher.sh" "$@"`; nothing else |
| `launcher/core.sh` | shared, reference copy | the whole launcher: phases 1-7 of this document |
| `agent/launcher.sh` | wrapper | the profile data the core needs and the agent hooks |
| `agent/profile.json` | wrapper | unchanged role; new fields `native.exec_tmp` (U7) and `native.exec` (H2); `install.runtime_build` removed (U8); validated by `network/agent_profile.py` |
| `setup/common.py` `MANIFEST` | shared | adds `launcher/core.sh` and `agent/launcher.sh`, so installations contain the core (H1) |
| `network/qualification_records.py` `code_files` | shared | binds `launcher/core.sh` (in `SHARED_CODE`) and `agent/launcher.sh`, so a core or agent-part change invalidates qualification (H1) |
| `network/control.py` preflight, `setup/launch.py` trust checks | shared | also require `launcher/core.sh` and `agent/launcher.sh` to be protected files (H-e) |
| `network/qualify.py`, `network/qualification_records.py`, `setup/common.py` | shared | derive a missing `<P>_NETWORK` from the profile (`provider` with authentication methods, otherwise `offline`); the core also exports the resolved mode to every Python helper it starts (H-a) |
| `network/agent_profile.py` `SUFFIXES`, `setup/common.py` `runtime_environment` | shared | know `ENV_VARS` and `READONLY_STATE`; setup and smoke runs drop host values of both (M3) |
| `tests/test_alignment.py`, `tests/test_setup.py`, `tests/test_agent_profile.py` | shared | follow the thin entry script, `agent/launcher.sh`, the new profile fields and the removed `runtime_build` (see `docs/launcher-test-map.md`) |
| `tests/fake_podman.py` | shared | the fake engine |
| `tests/test_launcher.py` | shared | the shared launcher tests, run with a fixture `agent/launcher.sh` |
| `tests/test_wrapper.py` | wrapper | hook and agent data tests only |

The entry script keeps its name, so `setup/launch.py`, the managed launchers
and every documented command are unchanged.

### Profile data in `agent/launcher.sh`

Plain Bash assignments, no logic. A shared alignment test loads the file in a
clean Bash and compares each value with `agent/profile.json`. The file starts
with `# shellcheck shell=bash disable=SC2034,SC2154`: the core sources it, reads
its data and hook outputs, and defines the core state the hooks read, which
ShellCheck cannot see when it checks the file alone
(`lint-shared-launcher-shellcheck`).

| Variable | Profile source |
| --- | --- |
| `AGENT_NAME`, `AGENT_DISPLAY_NAME` | `name`, `display_name` |
| `AGENT_WRAPPER` | `wrapper` |
| `AGENT_ENV_PREFIX` | `env_prefix` |
| `AGENT_LABEL_NAMESPACE` | `label_namespace` |
| `AGENT_IMAGE`, `AGENT_PROXY_IMAGE` | `images.agent`, `images.proxy` |
| `AGENT_HOME`, `AGENT_COMMAND` | `native.home`, `native.command` |
| `AGENT_EXEC` | `native.exec`: absolute in-container application path for restricted agent sessions (default `/usr/local/bin/<command>`; A: `/usr/local/bin/antigravity-entrypoint`) |
| `AGENT_CONFIG_DIR_ENV`, `AGENT_CONFIG_HOME` | `native.config_dir_env`, `native.config_home` |
| `AGENT_SHARED_DIRS` (array), `AGENT_PRIVATE_SHARED_DIRS` | `native.shared_dirs`, `native.private_shared_dirs` |
| `AGENT_APPROVAL_BYPASS_ENV` | `native.approval_bypass_env` (empty when absent) |
| `AGENT_EXEC_TMP` | `native.exec_tmp` (U7) |
| `AGENT_CREDENTIALS` (array of `policy_profile=credential_env`, empty value for account methods) | every policy profile in `agent/policies/default.json`, through its `authentication` method's `credential_env` (X `openai-api-docs` included) |

Agent data with no profile counterpart:

| Variable | Meaning |
| --- | --- |
| `AGENT_SESSION_ENV` (array `NAME=VALUE`) | fixed agent settings for every session |
| `AGENT_RESTRICTED_ENV` (array `NAME=VALUE`) | fixed agent settings for offline and provider sessions |
| `AGENT_PROVIDER_ENV` (array `NAME=VALUE`) | fixed agent settings for provider sessions only (C, M2) |
| `AGENT_UNSET_ENV` (array) | variables removed from every session (A: `DBUS_SESSION_BUS_ADDRESS`) |
| `AGENT_RESERVED_ENV` (array) | names the agent part sets; `<P>_ENV_VARS` skips them (U5) |

Derived by the core, never declared: the default network mode (`provider`
when the profile declares authentication methods, that is when
`AGENT_CREDENTIALS` is not empty, account methods included; otherwise
`offline`; U1, M10), shell profiles (H-c: when `AGENT_COMMAND` is a shell,
the session is always in shell mode, runs `/bin/<command>` with the arguments,
and `--container-shell` is a no-op), and every `<P>_*` variable name.

`native.exec` is an optional absolute path (default `/usr/local/bin/<command>`;
unused for shell profiles); `native.exec_tmp` is an optional boolean (default
`false`). The alignment test also compares `AGENT_CREDENTIALS` with
`agent/policies/default.json`. An operator policy profile absent from the
default policy forwards no credential, as today.

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
| `agent_environment` | when the session environment is built (phase 5) | mode | `agent_env` (`NAME` or `NAME=VALUE`) | names the core sets (`HOME`, `USER`, `TERM`, `EDITOR`, `VISUAL`, `PATH`, the CA variables, `CONTAINER_HOST`, `CONTAINER_NAME`, the config variable); the proxy variables in restricted modes (U11); another method's credential in provider mode (U13) | none |
| `agent_mounts` | after the state mounts (phase 5) | mode, home | `agent_mount_specs` entries `ro:<source>:<destination>` or `tmpfs:<destination>:<size>` | writable binds; relative paths; colon, CR or LF; a destination equal to, or containing, `/tmp`, `/var/tmp`, `/run`, the workspace, `/toolchains`, the home, the CA file or another mount (destinations below the home are allowed, M7); a missing source; a size not matching `[1-9][0-9]{0,5}[kmgKMG]` | none |
| `agent_build_args` | before every build and before the freshness check (U8) | - | `agent_build_args` (`NAME=VALUE`), `agent_build_inputs` (files inside the installation, added to `build-inputs-hash`) | values with CR or LF; inputs outside the installation | none |

Core state a hook may read: `network_mode`, `network_profile` (selected policy profile, empty outside provider mode), `shell_mode`, `restricted`, `podman_access`, `qualification_probe`,
`workspace`, `workspace_mount`, `state_dir` (empty in shared mode),
`script_dir`, `caller_uid`, `caller_gid`, every `AGENT_*` value, and any host variable that is not a core `<P>_*` setting (for example `PI_NPM_CACHE_SIZE`, `OPENCODE_PERMISSION`).

Agent tmpfs mounts get `rw,noexec,nosuid,nodev,mode=0700,U` and the given
size.

### Core rules added by the review

- **Ordering (M6).** Application arguments: `agent_mode_args`, then
  `agent_bypass_args`, then the user's arguments. Environment, where the last
  value wins: toolchain variables; core forwarding (`TERM`, `COLORTERM`,
  `LANG`, `LC_ALL`, and the proxy variables in unrestricted mode, U11);
  `agent_env`; `<P>_ENV_VARS`; `agent_bypass_env`; core-set variables (`HOME`,
  `USER`, `EDITOR`, `VISUAL`, the config variable, the CA variables,
  `CONTAINER_NAME`, `CONTAINER_HOST`); fixed agent settings (session, then
  restricted, then provider); finally `--unsetenv` for `AGENT_UNSET_ENV`,
  `CONTAINER_CONNECTION` and, without delegation, `CONTAINER_HOST`. The output
  of `session.py agent-args` (its proxy `--unsetenv`, provider proxy values and
  guard `--entrypoint`) follows every core engine argument; the core adds no
  `--entrypoint` in restricted modes.
- **Reserved names for `<P>_ENV_VARS` (M5, U13).** Always: every name the core
  sets, `AGENT_RESERVED_ENV`, `AGENT_UNSET_ENV`. Restricted modes: also the
  proxy and CA variables and the names in `AGENT_RESTRICTED_ENV` and
  `AGENT_PROVIDER_ENV`. Provider mode: also every `credential_env` other than
  the selected profile's. Each skipped name gets one notice.
- **Credentials (U10, H3).** Provider mode forwards the selected policy
  profile's `credential_env` by name when set. Offline and unrestricted forward
  no credential; `<P>_ENV_VARS` may name one in unrestricted mode.
- **Pi features made common (U12, H5).** Unrestricted sessions add `--init`
  (restricted ones cannot: the guard rejects its mount below `/run`). Each
  create attempt sets `CONTAINER_NAME=<name>`. With delegation the core adds
  tmpfs `/var/lib/containers` (256m) and `/run/containers` (64m), `noexec`,
  `mode=0700,U`. Builds use `--format docker` and no build timeout.
- **Build (H6, M11, U8).** `build-inputs-hash` covers `Containerfile`,
  `.containerignore`, `network/relay.py`, `network/mux.py`, the profile's
  `install.files` and `agent_build_inputs`, in that order; the CA bundle is
  excluded. A build first pulls any missing exact `FROM` base, then runs
  `podman build --pull=never --format docker` with `</dev/null`, as setup's
  recipe build does today; `create` also runs with `</dev/null` (L9).
- **Build-only path (U3, M11, U16, U17).** `--container-build` with no
  application argument (`--container-git-worktree` and `--container-shell` do
  not count) builds and exits. It first validates every launch setting: mode,
  maintenance, budgets, lifetime, image name, state and configuration paths
  (lexically), delegation settings and socket, host tools, the launch engine
  and CA selection. It skips the workspace refusal, state creation, toolchains,
  cgroup checks, restricted preparation and the session. With an application
  argument, `--container-build` builds and then starts the session.
- **Build hash (M12).** `build-inputs-hash` is the SHA-256 of the lines
  `<relative path> <sha256 of content>` for each input, in the order above,
  each path once.
- **Probe (M1).** `--container-qualify-probe` follows the restricted session
  path without the toolchain library, the qualification check, the application
  command, `agent_command_args`, `agent_approval_bypass` and `<P>_ENV_VARS`;
  every other core step and hook applies.
- **Variable syntax (U18).** `<P>_ENV_VARS` is split on whitespace; a name that
  is not `[A-Za-z_][A-Za-z0-9_]*` stops the launch; unset or empty variables are
  not forwarded. `<P>_READONLY_STATE` is a `boolean()`. U11's proxy set is
  `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and their lowercase
  forms.
- **Help (M8).** The core prints the usage line from `AGENT_WRAPPER`, a
  description from `AGENT_DISPLAY_NAME`, the common options and variables, and
  the provider disclosure with each base policy profile's hosts from
  `agent/policies/default.json`; `agent_help` adds the agent part after the
  common variables.
- **Shutdown slicing (U9).** As S's `control()`: a call is skipped when less
  than 2 s remain before the deadline minus a 2 s reserve; otherwise its
  duration is min(2 s, remaining minus 1 s).
- **Agent mount sources.** The core resolves each `ro` source physically and
  requires an existing file or directory (as O and P do).
- **Messages.** A missing `podman` uses `die` (O's exit 127 ends); cleanup
  warnings name the proxy ID when one exists (C); an unresolvable `HOME` falls
  back to its lexical path (S, not P's stop); `PI_DEBUG` output is dropped
  except what `agent_validate` prints.
- **Reported delegation socket (`verify-delegated-socket-path`, `sandbox-ref-25`).**
  The service's `Host.RemoteSocket.Path`, after removing `unix://`, must be
  absolute and not consist only of slashes. When that path exists in the
  wrapper's own namespace (`-e` or a dangling link), it must be a Unix socket
  (`-S`, following links). A path the wrapper cannot see is accepted: it is the
  remapped socket of a wrapper that runs in a container, and the service's
  answer is trusted there. Guided setup applies the same rule.
- **Engine query timeouts (M8).** Every read-only engine query (`info`,
  `version`, `ps`, `image exists`, `image inspect`, `container exists`,
  `inspect`, the delegation socket query) runs under `timeout --kill-after=1s
  10s`. `create`, `start`, `build` and `pull` are not bounded; shutdown calls
  follow U9.
- **Read-only state (U6, M9).** With `<P>_READONLY_STATE=1` the core mounts
  the configuration directory and every shared directory read-only below the
  tmpfs home, from shared state or from the isolated home. They must already
  exist; owner and privacy checks are skipped, and they are not writable inputs
  of restricted preparation. The isolated home itself is not mounted.
- **Isolated home children (M4).** Every child and the CA mount parent is
  resolved before creation, must stay inside the home, and must be private.
- **Temporary mount modes (L7).** `/tmp`, `/var/tmp` and the ephemeral home are
  `mode=1777`; `/run` is `noexec` in every wrapper (X's executable `/run` ends).

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
| O native-variable allowlist | `agent_environment` (H-g) |
| O toolchain-environment filter | dropped: redundant with `setup/toolchains.py` protected names |
| P `debug` (`PI_DEBUG`) | `agent_validate` |
| P `~/.npm` tmpfs (`PI_NPM_CACHE_SIZE`), `GITCONFIG` | `agent_validate` and `agent_mounts` |
| X protected `-c` overrides, `--no-daemon` | `agent_command_args` |
| C, A `--dangerously-skip-permissions`; X `--yolo`; O `OPENCODE_PERMISSION`; P notice | `agent_approval_bypass` |

Hooks never run during shutdown, never see the session token or container
ID, and cannot add engine flags other than those their outputs describe.

## Visible changes

Behavior that changes for users of at least one wrapper when it adopts the
core. Each entry has a row in "Spec deltas for the implementation change".

| Change | Wrappers affected | Source |
| --- | --- | --- |
| A missing `<P>_NETWORK` selects `provider`; without provider settings the launch stops with setup guidance | C, X, A, O, P | U1 |
| Legacy names removed: Pi `PI_*` aliases, `PI_NETWORK`, `PI_PULL_ALWAYS`, `--wrapper-help`; OpenCode `opencode-wrapper` shim and version-variable notices | O, P | U2 |
| `--container-build` alone builds and exits | S, C, X, A, O | U3 |
| An empty `<P>_TOOLCHAINS` mounts the library (default) | A | phase 1-2 |
| `<P>_IMAGE` with whitespace or control characters is refused | S, C, X, A, P | phase 1-2 |
| `CONFIG_DIR` must be absolute without colon, CR or LF, checked before the engine | S | phase 1-2 |
| Antigravity shares `~/.gemini` by default; its dedicated home is no longer used | A | U4 |
| `<P>_ENV_VARS` forwards listed variable names | S, C, X, A; P renamed from `PI_ENV_VARS` | U5 |
| `<P>_READONLY_STATE` mounts existing state read-only | S, C, X, A, O; P renamed from `PI_READONLY_CONFIG` | U6 |
| Every engine query is bounded by a timeout | S, C, X, A, O | phase 3-4 |
| One temporary-storage layout; `exec` only where the profile declares it | all | U7 |
| A stale image is refused until rebuilt; Antigravity's explicit build no longer skips the cache | all | U8 |
| `TERM` and `USER` set in every session; `EDITOR`/`VISUAL` always `nano` | X, O (`TERM`, `EDITOR`); P (host `EDITOR`/`VISUAL` no longer kept, U15); all but O (`USER`) | phase 5 |
| Claude's provider sessions forward `ANTHROPIC_API_KEY` only with the API policy profile | C | U10 |
| Unrestricted sessions forward no API key unless listed in `<P>_ENV_VARS` | A, P (O: `PROVIDER` stays as an agent hook) | U10 |
| Unrestricted sessions forward the proxy variables, `COLORTERM`, `LANG` and `LC_ALL` | S, C, X, A (P: `COLORTERM`, `LANG`, `LC_ALL`) | U11 |
| `--init` in unrestricted sessions, `CONTAINER_NAME` in every session, delegation tmpfs mounts, `--format docker` builds | S, C, X, A, O | U12 |
| No build timeout | P | U12 |
| `<P>_ENV_VARS` cannot forward another method's credential in provider mode | O | U13 |
| Isolated home children must be contained and private | A, O, P | M4 |
| `/run` is not executable | X | L7 |
| A missing `<P>_NETWORK` resolves to the same mode in the launcher and in every Python helper | C, X, A, O, P | H-a |
| `STATE_DIR` and the configuration override are refused before the engine when not absolute or with colon, CR or LF | S, C, X (`CLAUDE_CONFIG_DIR`, `CODEX_HOME` included) | phase 3-4, M14 |
| OpenCode's approval bypass no longer applies in shell mode | O | phase 1-2 |
| OpenCode's `io.opencode-container.*` labels are dropped | O | phase 6 |
| `.config/openspec` and the CA parent in an isolated home must be private and contained | S, C | M4 |
| `--container-build` without application arguments validates every setting, builds and exits, also through a worktree launcher | all | U16, U17 |
| Invalid `<P>_ENV_VARS` names stop the launch; `<P>_READONLY_STATE` accepts `boolean()` values; `ALL_PROXY` is forwarded in unrestricted mode | O, P | U18 |
| Missing `podman` exits 1 instead of 127; an unresolvable `HOME` no longer stops P; `PI_DEBUG` output is dropped | O, P | low findings |
| Shutdown is bounded by one 20 s deadline | X, A, P | U9 |
| Shell mode passes its arguments to the shell in every mode | C, X, A, O, P | U14 |

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
| U3, U16, U17 | `container-launcher` | Predictable image operations | MODIFIED: `--container-build` with no application argument builds and exits without a session, after validating every launch setting |
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
| phase 5 | `container-launcher` | Transparent invocation and terminal handling | MODIFIED: `USER` is set; `TERM` is forwarded; `EDITOR` and `VISUAL` are `nano` (the `runtime-image` editor requirement is unchanged, U15) |
| phase 1-2 (A) | wrapper specs | toolchain switch | reference: none; the Antigravity adoption treats an empty `<P>_TOOLCHAINS` as the default |
| U9 | `container-launcher` | Bounded session shutdown | reference: none (already family A); X, A and P adoptions state the shared 20 s deadline |
| H1 | `container-setup` | Protected complete installation | MODIFIED: the installation contains `launcher/core.sh` and `agent/launcher.sh` |
| H1 | `network-egress` | Credential-free local enforcement qualification | MODIFIED: qualification evidence binds `launcher/core.sh` and `agent/launcher.sh` |
| H2, U7, U8 | `network-egress` | Single protected agent profile | MODIFIED: the profile declares `native.exec` and `native.exec_tmp`; `install.runtime_build` is gone |
| U1 | `network-egress` | Runtime modes with an offline default | reference: none; each agent adoption MODIFIES it to a provider default |
| phase 3-4 | `container-launcher` | Single-record launch verification response | MODIFIED: every read-only engine query is bounded and refuses CR and extra records |
| U10, U11, U13 | `container-launcher` | Transparent invocation and terminal handling | MODIFIED: unrestricted sessions forward `TERM`, `COLORTERM`, `LANG`, `LC_ALL` and the proxy variables, and no credential; provider sessions forward only the selected method's credential; `<P>_ENV_VARS` reserved names |
| U12 | `container-launcher` | Owned container lifecycle | MODIFIED: unrestricted sessions run with `--init`; every create attempt sets `CONTAINER_NAME` |
| U12 | `container-podman-access` | Access policy applies across launch modes | MODIFIED: delegated sessions get private tmpfs `/var/lib/containers` and `/run/containers` |
| U12 | `container-launcher` | Predictable image operations | MODIFIED: builds use `--format docker`, pull missing exact bases, then `--pull=never`; no build timeout |
| M4 | `persistent-state` | Resolved state paths and isolation scope | MODIFIED: every isolated-home child is contained and private |
| H-a | `container-launcher` | Restricted launches require current local qualification | MODIFIED: qualification checks use the mode the launcher resolved, including a profile's provider default |
| H-e | `network-egress` | Profile-bound restricted identity | MODIFIED: preflight requires the core and agent launcher files to be protected |
| H-e | `container-setup` | Protected complete installation | MODIFIED: managed launches verify the core and agent launcher files as protected (with H1) |
| M8 | `network-egress` | Residual exfiltration disclosure | MODIFIED: the core prints each base policy profile's hosts from the default policy |
| U16, U17 | `container-launcher` | Predictable image operations | (see U3 row) |
| U18 | `container-launcher` | Extra variables forwarded by name | (part of the U5 ADDED requirement: syntax and invalid names) |
| H-c | `container-launcher` | Transparent invocation and terminal handling | reference: none (S stays a Bash session); shell profiles are always in shell mode |
| phase 6 | `container-launcher` | Owned container lifecycle | MODIFIED: a failed create whose name holds this session's container is never a collision; that container is removed or reported unresolved |
| U14 | wrapper specs | shell mode | reference: none; C, X, A, O and P adoptions pass shell-mode arguments to the shell in every mode |

Every row of "Visible changes" maps to a row here.

## Review findings

An independent read-only review (2026-11-16) checked this document against the
six launchers, their tests, the profiles and the reference specs. The user took
decisions U10-U14 on the findings that needed one:

- **U10.** Provider sessions forward the `credential_env` of the selected
  policy profile's method only (C's account profile no longer receives
  `ANTHROPIC_API_KEY`). Unrestricted sessions forward no credential; a user who
  wants one lists it in `<P>_ENV_VARS`, so a key in the host shell never
  silently changes how an agent authenticates.
- **U11.** Unrestricted sessions forward the proxy variables (both cases),
  `TERM`, `COLORTERM`, `LANG` and `LC_ALL`; restricted modes never forward the
  proxy variables.
- **U12.** Pi's `--init` (unrestricted), per-attempt `CONTAINER_NAME`,
  delegation tmpfs mounts and `--format docker` builds become core behavior for
  every wrapper; Pi's 300 s build timeout is dropped.
- **U13.** `<P>_ENV_VARS` cannot forward another method's credential in
  provider mode, nor proxy, CA or protected settings in restricted modes.
- **U14.** Shell mode passes its arguments to the shell in every mode.

| Finding | Resolution |
| --- | --- |
| H1 core files missing from installation and qualification | Files table (`MANIFEST`, `code_files`); deltas for `container-setup` and `network-egress` |
| H2 Antigravity runs its entrypoint script | `AGENT_EXEC` (`native.exec`); unrestricted agent sessions use the image `ENTRYPOINT`; phase 6 row corrected |
| H3 credential cells and model | U10; `AGENT_CREDENTIALS` keyed by every policy profile; phase 5 and 6 rows corrected |
| H4 unrestricted proxy and locale forwarding | U11; `agent_environment` refuses proxy names only in restricted modes; `TERM` row corrected |
| H5 Pi features with no hook | U12; `podman_access` readable by hooks |
| H6 `build-inputs-hash` input set | Core rules: Build |
| M1 shutdown slicing | U9 text and Shutdown budget row: min(2 s, time left) |
| M2 Claude provider-only settings | `AGENT_PROVIDER_ENV` |
| M3 shell-mode arguments | U14 |
| M4 isolated home children | union; Core rules |
| M5 mode-dependent reserved names | U13; Core rules: Reserved names |
| M6 ordering | Core rules: Ordering |
| M7 bind rules and tmpfs size | `agent_mounts` refusal rules |
| M8 query timeouts | Core rules: Engine query timeouts |
| M9 read-only layout | Core rules: Read-only state |
| M10 credential format and default mode | `AGENT_CREDENTIALS` format; derived default mode |
| M11 build-only path and base pulls | Core rules: Build-only path, Build |
| M12 entry-script contract | Files: entry script |
| M13 test-map notes | `docs/launcher-test-map.md`: "shared (rewrite)" destination and notes |
| L1-L5 cell accuracy | rows corrected (P config variable, `CONFIG_DIR` check, C maintenance scope, O recovery, name prefix) |
| L6 visible changes and deltas | rows added; `TERM`, single-record and profile-schema deltas |
| L7 mount modes | Core rules: Temporary mount modes |
| L8 test-map phases | `docs/launcher-test-map.md` regenerated |
| L9 `</dev/null` for create and build | Core rules: Build |

### Second review

A second independent review (2026-11-16) checked the corrected document and
found 7 high, 14 medium and 13 low findings. The user decided:

- **U15.** `EDITOR` and `VISUAL` are always `nano`, as the `runtime-image`
  editor requirement states; the host value is not kept (changes P).
- **U16.** The build-only path validates every launch setting before building
  and skips only workspace refusal, state creation, toolchains, cgroups,
  restricted preparation and the session.
- **U17.** `--container-build` builds and exits when no application argument
  is given; `--container-git-worktree` (added by managed worktree launchers) and
  `--container-shell` do not count.
- **U18.** `<P>_ENV_VARS` is whitespace-separated, an invalid name stops the
  launch and empty variables are not forwarded; `<P>_READONLY_STATE` is a
  `boolean()`; the unrestricted proxy set includes `ALL_PROXY`.

| Finding | Resolution |
| --- | --- |
| H-a missing mode is offline in the Python helpers | Files: Python helpers derive the mode from the profile; the core exports the resolved mode; delta |
| H-b entry script without readlink | Files: entry falls back to `${BASH_SOURCE[0]%/*}`; the core keeps S's diagnosis order |
| H-c reference command | shell profiles are always in shell mode and run `/bin/<command>` |
| H-d build-only versus tests | U16, U17; tests marked "shared (rewrite)" |
| H-e preflight and managed-launch trust lists | Files: `control.py`, `setup/launch.py`; deltas |
| H-f editor versus `runtime-image` spec | U15 |
| H-g OpenCode native-variable allowlist | phase 5 row and helper table: `agent_environment` |
| M1 probe path | Core rules: Probe |
| M2 combined build flags | U17 |
| M3 setup unaware of new variables | Files: `agent_profile.py`, `common.py` |
| M4 variable syntax | U18 |
| M5 credential tests classified as hook | test map: "shared (rewrite)" U10 with the hook part noted |
| M6 S tests depending on U7 and U16 | test map: "shared (rewrite)" |
| M7 non-wrapper tests | Files row and test map section "Other shared test files" |
| M8 help composition | Core rules: Help; delta |
| M9 `session.py agent-args` ordering | Core rules: Ordering |
| M10 OpenCode bypass in shell mode | Visible changes |
| M11 data for hooks | readable state: `network_profile`, `qualification_probe`, agent host variables |
| M12 build-hash construction | Core rules: Build hash |
| M13 profile field types and policy credentials | profile data paragraph |
| M14 `CONFIG_DIR` check scope | phase 1-2 row; Visible changes |
| Low findings | visible-change rows added; S cells (CA parent, `HISTFILE`) corrected; fallback name `AGENT_NAME`; U9 slicing stated; agent mount sources resolved; `ALL_PROXY` (U18); messages (`exit 127`, proxy ID, `HOME`, `PI_DEBUG`); O toolchain filter dropped; P `IMAGE` default tag follows the profile image with `:latest` |

## Windows entry

Windows users start the sandbox from PowerShell. The shared shim runs the
managed installation inside the Podman machine's WSL distribution through the
release's bootstrap, and sessions and setup run in the machine's systemd
namespaces through the namespace helper. The OpenSpec changes
`support-windows-podman-machine` and `support-machine-restricted-networking`
specify the details. This section lists the rules that the shared launcher
files enforce.

### Thin entry and shim

`<name>.ps1` is the thin PowerShell entry. Its text is the same in every
wrapper, and `tests/test_alignment.py` holds it. It runs
`launcher/windows/core.ps1` with its own directory, `$args` and
`$MyInvocation.ExpectingInput`, and exits with the shim's status. Both files are
ASCII, because Windows PowerShell 5.1 reads files without a byte order mark as
ANSI.

The shim reads its checkout's `agent/profile.json`: the name, the Bash entry,
the variable prefix and the configuration-directory and approval-bypass
variables. Values come from the environment, and an empty value counts as
unset. The shim then handles the call in this order:

1. `--container-help`, anywhere in the arguments, takes precedence. The shim
   prints the Windows part, then runs the checkout's wrapper help in the
   distribution. Without a registered and running distribution or an
   existing user it prints the machine guidance instead and exits 0.
2. It refuses with status 1, before running `wsl.exe`:
   - pipeline input. Windows PowerShell 5.1 also reports standard input that
     `cmd.exe` redirects to `powershell -File <name>.ps1` as pipeline input;
     the shim accepts it when standard input is redirected and the process
     runs the entry itself with `-File`, which no PowerShell pipeline can feed;
   - an argument that is a PowerShell list, from an unquoted comma, or that
     contains NUL;
   - an invalid `<P>_WSL_DISTRO`, `<P>_WSL_USER` (letters, digits, `.`, `_`
     and `-`) or `<P>_WSL_INSTALLATION` (an absolute path of the same
     characters and `/`);
   - `--container-setup` with other arguments;
   - `<P>_PODMAN=1`: Podman delegation is unsupported on Podman machine.
     `<P>_NETWORK` and `--container-qualify` reach the launcher, which checks
     them as on Linux.
3. `--container-setup` checks the LF line endings of the Bash entry,
   `launcher/core.sh`, `agent/launcher.sh` and `launcher/windows/enter.sh`,
   that the distribution is registered and running, and that the user's
   runtime directory `/run/user/<uid>` is a writable directory there
   (`sh -c 'test -d /run/user/$(id -u) -a -w /run/user/$(id -u)'`). It then runs
   `wsl.exe -d <distro> -u <user> --cd <entry directory> --exec /bin/bash launcher/windows/enter.sh <name> /bin/bash <entry>.sh --container-setup`,
   with only `WRAPPER_WINDOWS_SETUP=1` in `WSLENV`, so that setup leaves out
   its Linux shell guidance. Help runs the wrapper directly, because it
   queries no engine.
   The entry directory must be a folder on a Windows drive.
4. A launch refuses a location outside the FileSystem provider, encodes the
   arguments, checks that the distribution is registered and running, and runs
   `wsl.exe -d <distro> -u <user> --exec /bin/sh -c 'cd && exec /bin/bash <bootstrap>'`.
   The bootstrap path is `.local/lib/<name>/current/launcher/windows/bootstrap.sh`
   relative to the user's home, or `<P>_WSL_INSTALLATION/current/...`.
5. After a failure, exit code -1 or 255 leads to a user probe
   (`--exec /bin/true`). A missing user stops with status 1, and so does -1
   from `wsl.exe` itself; a 255 from the session is returned. Exit code 127
   leads to an installation probe (`sh -c 'cd && test -f <bootstrap>'`). A
   missing installation stops with status 1 and asks to rerun
   `<name>.ps1 --container-setup`; otherwise 127 is returned. Every other code
   is returned unchanged.

A launch forwards these names, each with `/u` in `WSLENV` and only with a
nonempty value:

- `<P>_*` names of letters, digits and `_`, except `<P>_WSL_*`; another
  name gets a notice, because `:` or `/` would split `WSLENV`;
- the profile's configuration-directory variable, only with a distribution
  path (starting with `/`); a Windows path gets a notice;
- the profile's approval-bypass variable;
- the valid names listed in `<P>_ENV_VARS`.

It never forwards `WSLENV`, `WRAPPER_WINDOWS_*`, `BASH_ENV`, `ENV`,
`SHELLOPTS`, `BASHOPTS`, `CDPATH`, `GLOBIGNORE`, `IFS`, `PS4`, `LD_*`,
`PYTHON*`, `PATH`, `HOME`, `USER`, `LOGNAME`, `SHELL`, `PWD`, `OLDPWD`,
`TMPDIR`, `XDG_*`, `WSL_*`, `CONTAINER_*` or `CONTAINERS_*`. It prints one
notice for each such name listed in `<P>_ENV_VARS`.

The shim never starts a stopped distribution: `wsl.exe -l --running -q`, then
`wsl.exe -l -q` tell a running, stopped or missing distribution apart without
starting it. A stopped one is refused with `podman machine start`, because a
distribution that `wsl.exe` starts lacks `/run/user/<uid>`, and no `podman`
command works there. The bootstrap refuses that state for every ordinary
launch, before any Podman command, and asks to run `wsl --terminate <distro>`
and then start the machine with Podman.

The encoded arguments and `WSLENV` are limited to 32766 characters each. The
shim sets the `WRAPPER_WINDOWS_*` variables and `WSLENV` for the child only.
When `wsl.exe` returns, it restores the previous values and removes the
variables that were absent. The user's `WSLENV` is replaced, not extended.
Setup, help and the probes run without `WSLENV`.

Covering tests: `tests/windows/shim_tests.ps1`, run by `tools/powershell.sh`
with a fake `wsl.exe`; `test_powershell_entry_is_the_fixed_thin_entry` and
`test_powershell_files_are_ascii` in `tests/test_alignment.py`.

### Installer

`--container-install` and `--container-uninstall` must each be the only
argument. Uninstall works from the installed copy and from a checkout, before
the mode checks. An install runs the setup checks first: drive path, line
endings, a running machine started by Podman. It then reads the payload list:
setup's own `MANIFEST`, from
`wsl.exe ... --cd <checkout> --exec python3 -I -B setup/common.py --manifest`
(NUL-terminated names on standard output only; `wsl.exe` warnings on standard
error are ignored, and `-B` writes no bytecode into the source), plus the entry
and the `launcher/windows/*.ps1` files with a plain lowercase name. With
that list it calls `launcher/windows/install.ps1`, then runs setup from the
installed copy.

| Path | Content |
| --- | --- |
| `%LOCALAPPDATA%\Programs\<name>\` | the payload, at its relative paths |
| `...\<name>\install.json` | `state` (`incomplete` or `complete`), `files`, `source`, `time` |
| `%LOCALAPPDATA%\Programs\<name>.lock` | held exclusively while an install or uninstall runs |

`install.ps1` refuses a source inside the target and a target that is a
reparse point, takes the lock, then refuses before writing:

- a parent of the target that is a reparse point;
- on Windows, a target owned by an account other than the user or
  `BUILTIN\Administrators` (an elevated session of the same user);
- an existing non-empty target without `install.json`;
- an invalid name;
- a missing or non-regular input;
- an input with a carriage return;
- a user `PATH` that would exceed 32766 characters.

Names read back from `install.json` must pass the same name rule as the
inputs, so a damaged list cannot point outside the folder. File names are
compared case-insensitively on Windows. It writes `install.json` as
`incomplete` with the union of the old and new lists. It writes each file through `<file>.new`, replaces it (`File.Replace`
or `File.Move`) and checks its SHA-256. It removes the files that are no
longer listed and their empty folders, and writes `install.json` as
`complete`. It then reads the user `PATH` again and adds the folder through
`launcher/windows/user-path.ps1`, which keeps the registry value kind and
broadcasts `WM_SETTINGCHANGE`. The installed files are new local files, without
the Mark of the Web.

The shim refuses launches and setup from a folder whose `install.json` is not
`complete`. It refuses an install from the installed copy itself.

Uninstall removes the `PATH` entry first, then the listed files, the
`__pycache__` folders beside them that hold only `.pyc` files (setup runs
Python from the installed copy) and the empty folders. `install.json` goes
last, with the folder, so that a second uninstall still knows what to remove;
an empty folder without it is removed too. An unexpected error ends either
action with the wrapper's prefix and status 1.

The lock covers installs and uninstalls only. A setup or a launch that starts
from the installed copy while an update replaces its files can read a mix of
old and new files: run updates when no setup runs from the installed copy. It names the machine installation that stays. It reports
anything that remains, with `wsl --shutdown` as the way to release a folder in
use, and then exits with status 1. A target without `install.json` is never
deleted.

Covering tests: `tests/windows/shim_tests.ps1` (installer cases, with
`LOCALAPPDATA` in a temporary folder and a file instead of the registry) and
`tests/test_setup.py` (`--manifest`).

### Bootstrap

`launcher/windows/bootstrap.sh` is installed in every release, like the core.
The shim starts it from the release with `/bin/bash`, as the selected user of
the machine distribution, never from a checkout. It needs Bash 4.4 or later,
`base64`, `od`, `tail`, `wslpath`, `python3`, `readlink` and `id`, and it
stops naming a missing one.

Inputs, all in the environment:

| Variable | Content |
| --- | --- |
| `WRAPPER_WINDOWS_ARGS` | base64 of the UTF-8 arguments, each followed by NUL; unset or empty when there are none |
| `WRAPPER_WINDOWS_CWD` | raw Windows path of the PowerShell location |
| `WRAPPER_WINDOWS_ENTRY` | raw Windows path of the entry's directory |

The bootstrap reads two values from its own release: the profile name, used
as the prefix of its messages, and the managed command, from `setup.json`. It
then runs these steps, and stops with status 1, before running anything else,
at the first one that fails:

1. A release whose `setup.json` or profile cannot be read stops with
   `the installation in <release> is incomplete; rerun setup from Windows with --container-setup`.
2. A release whose `setup.json` saved Podman delegation stops and asks to
   rerun setup from Windows. The shim refuses only the Windows variable, and
   saved preferences apply to every launch without one. Saved network modes
   are the launcher's to check.
3. A missing or read-only `/run/user/<uid>` stops with
   `the WSL distribution <distro> runs without the Podman machine: ...`, which
   asks to run `wsl --terminate <distro>` and then start the machine with
   Podman Desktop or `podman machine start`.
4. A missing `WRAPPER_WINDOWS_CWD` or `WRAPPER_WINDOWS_ENTRY` stops with
   `start sessions with the Windows entry`.
5. The arguments are validated and decoded. Data that is not base64, or whose
   last record has no NUL terminator, stops with
   `malformed argument transport`. NUL termination is what tells no arguments
   apart from one empty argument.
6. Both paths are classified, case-insensitively, before translation. A refused
   path stops with the message for its kind:

   | Raw path | Result |
   | --- | --- |
   | `\\wsl$\...`, `\\wsl.localhost\...` | `... is inside a WSL distribution` |
   | `\\?\...`, `\\.\...`, other `\\...` | `... is a network or device path` |
   | `X:\...` or `X:/...` | translated with `wslpath -a -u`; `... is on drive X:, which this distribution does not mount, or does not exist` when the result is not a directory |
   | anything else, such as `HKCU:\Software` | `... is not a Windows file system path` |

7. The bootstrap changes to the translated working directory and exports the
   translated `WRAPPER_WINDOWS_ENTRY`. It unsets `WRAPPER_WINDOWS_ARGS`,
   `WRAPPER_WINDOWS_CWD` and `WSLENV`, then runs the managed command with the
   decoded arguments through the release's namespace helper:
   `/bin/bash <release>/launcher/windows/enter.sh <name> <command> <arguments>`.

From that point the managed launch applies its usual checks, including the
rule below and the core's sensitive-workspace rules.

The core's setup guidance follows the entry. When `WRAPPER_WINDOWS_ENTRY` is
not empty, both "setup required" refusals (a restricted mode without a
protected installation, and a default provider launch without its saved
settings) name `run <AGENT_NAME>.ps1 --container-setup from Windows`;
otherwise they name `run bash <invoked wrapper> --container-setup and use the
managed launcher`. The variable is internal to the Windows path: a Linux
launch that exports it gets the Windows step, and nothing else changes.
Covering tests: `test_setup_guidance_from_the_windows_entry_names_the_windows_step`
and `test_provider_setup_guidance_from_the_windows_entry` in
`tests/test_launcher.py`.

Covering tests: `tests/test_windows_bootstrap.py`.

### Namespace helper

The Podman machine starts systemd in PID and mount namespaces of its own
(`unshare --pid --mount`). The user's systemd manager, `podman.socket`, the
Podman service and Podman's own connections run there, and the machine's
login shells enter with `/usr/local/bin/enterns`. A `wsl.exe --exec` session
stays outside: its podman would start a second rootless user namespace on the
same storage, which cannot run commands in the service's containers.
`launcher/windows/enter.sh`, installed in every release like the bootstrap, runs
`bash enter.sh <prefix> <command> [args...]` as the calling user inside
systemd's namespaces:

1. When PID 1 is `systemd`, it runs the command directly, with
   `XDG_RUNTIME_DIR=/run/user/<uid>`.
2. Otherwise the target is the lowest root process named `systemd` whose
   `NSpid` is `<pid> 1`. Without one it stops with status 1 and the machine
   guidance (`wsl --terminate <distro>`, then `podman machine start`).
3. It needs `sudo` and `nsenter`, and stops naming a missing one.
   `sudo -n true` must succeed; otherwise it stops with status 1, because the
   machine's user needs `sudo` without a password.
4. It writes the environment (`env -0`) to a new mode-0600 file
   `env.<pid>.<random>` in the private directory
   `/run/user/<uid>/windows-entry`. `<pid>` is its own process, which `exec`
   hands to `sudo`; a file whose process no longer runs was left by a failed
   start and is removed first.
5. It runs `sudo -n -- nsenter --target <pid> --mount --pid --wd=<directory> -- sudo -n -u <user> -- /bin/bash <helper> --inner <prefix> <file> <command> [args...]`.
6. The inner part accepts only a regular file of that directory that it owns.
   It reads the file, removes it, and runs
   `env -i -- <saved variables> XDG_RUNTIME_DIR=/run/user/<uid> <command> [args...]`.

The arguments stay an argument vector at every step, and the environment
never reaches root's command line. The working directory, the standard
streams, the terminal (`sudo` relays a new pseudo-terminal) and the exit status
stay the same.

Covering tests: `tests/test_windows_enter.py`, with a synthetic `/proc` and
fake `sudo` and `nsenter`.

### Writable mounts never reach the Windows entry

The bootstrap exports `WRAPPER_WINDOWS_ENTRY`: the directory of the Windows
entry, translated into the distribution, for example
`/mnt/c/Work/wrapper-checkout`. The shim runs from that directory on every
launch, so the session must never be able to write it.

`protect_mounts` in `setup/common.py` therefore refuses a managed launch, with
status 1 and before any engine query, when that directory and any writable
mount overlap in either direction. The writable mounts are:

- the workspace;
- the worktree parent, whether it comes from the argument or from the saved
  preference;
- the state directory or the configuration and shared directories.

Paths on WSL drive mounts (`/mnt/<letter>/...`) are compared without regard to
letter case, as drvfs does. Other paths are compared exactly.

The directory gets no ownership check, because drvfs cannot pass one. A value
that is not absolute is refused. `setup/launch.py` prints the overlap message
as is, so the user sees which mount reaches the entry. Every other managed
configuration error keeps the generic message.

Covering tests: `test_writable_mounts_must_not_reach_the_windows_entry`,
`test_windows_entry_comparison_ignores_case_only_on_drive_mounts`,
`test_managed_launch_names_the_overlapping_windows_entry`.
