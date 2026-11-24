# Proposal

## Why

The toolchain library exists so that restricted sessions can use extra
language toolchains without Podman delegation or an unrestricted network.
Adding a toolchain is still a manual chore: the operator sets
`<P>_MAINTENANCE=1` for every image pull, downloads and checksums archives by
hand, edits absolute paths into recipe copies, and builds a local image for
Rust. On Windows the same command fails on Windows paths, and with the saved
worktree scope every managed `--container-toolchain` command fails, on Linux
too. Adding a toolchain must be one command that prepares everything itself.

## What Changes

- `--container-toolchain add` pulls digest-pinned images without
  `<P>_MAINTENANCE`. Image builds stay under maintenance, and `add` never
  builds an image.
- Archive sources can name an HTTPS URL with its SHA-256. `add` downloads,
  verifies and extracts them itself, trusting the host CA bundle saved by
  setup. Local archive files stay accepted for hosts without network access.
- A recipe can merge several sources into one toolchain root. The Rust recipe
  uses the official distribution archives instead of a locally built image,
  and `docs/toolchains/rust-musl.Containerfile` and `sources.json` are
  removed.
- The reviewed recipes move from `docs/toolchains/` into a catalog in the
  protected release (`setup/toolchain-catalog/`), shared by every wrapper and
  copied by the Windows installer. `add <name>` installs a catalog recipe; a
  path still installs an operator recipe.
- An operator recipe inside a writable mount that a session started from the
  current directory would have (the workspace or a state directory) is
  refused, because the agent could have written it.
- From the Windows entry, a recipe path or a local archive path written as a
  Windows drive path is translated to its drive mount in the machine.
- The managed launcher no longer puts the saved worktree scope in front of
  host management commands, so `--container-toolchain` works whatever scope
  setup saved.
- After setup prepares a runtime image, it reruns `verify` for the installed
  toolchains, so default toolchains keep their environment without a manual
  step; a failed check is reported, not fatal.
- Documentation: the README Toolchains and Windows sections (including the
  library living inside the Podman machine), `docs/setup.md` and the
  validation record.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolchain-library`: pinned pulls without maintenance, downloaded and
  multi-source archives, the release catalog and `add <name>`, refusal of
  recipes in writable mounts, Windows path translation, and the documented
  Windows library location.
- `container-setup`: the saved worktree scope applies only to session
  launches, and setup re-verifies the installed toolchains after preparing the
  runtime image.

## Impact

- Shared code (new `sandbox-ref` tag, then propagation to the Claude, Codex,
  OpenCode, Pi and Antigravity wrappers through separate changes):
  `setup/toolchains.py`, `setup/launch.py`, `setup/setup.py`,
  `setup/common.py` (installed manifest), the new
  `setup/toolchain-catalog/`, `launcher/core.sh` (help text), and the shared
  tests `tests/test_toolchains.py` and `tests/test_setup.py`.
- Reference-only files: `README.md`, `docs/setup.md`, `docs/validation.md`,
  `tests/test_launcher.py`, `tests/test_image_pins.py`,
  `tests/test_network_runtime.py` (documented examples), and
  `tools/windows-validate.ps1`.
- Removed: `docs/toolchains/` (moved to the catalog),
  `docs/toolchains/rust-musl.Containerfile` and `docs/toolchains/sources.json`.
- Network boundary: unchanged. Downloads and pulls happen on the host, outside
  runtime filtering, as image pulls already do. Sessions gain no network,
  IPC or privilege capability.
- Compatibility: installed toolchains and schema-1 recipes stay valid.
- Out of scope: dependency registries (`add-read-only-dependency-mirror`),
  complete toolchain kits and a C/C++ toolchain, and a stronger `add` check.
