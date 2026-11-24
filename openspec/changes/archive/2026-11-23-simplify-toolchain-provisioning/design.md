# Design

## Context

See proposal.md for the motivation. The current state that shapes the
approach:

- `setup/toolchains.py` implements `add`, `list`, `remove`, `verify` and the
  launcher's `launch-env`. Recipes have `schema: 1` and one `source`: an image
  subpath, pulled only with `<P>_MAINTENANCE=1`, or a local archive with its
  SHA-256. Extraction, the hardened offline check, staging, the library lock
  and atomic publication already exist and are kept.
- The library is shared by every wrapper on the host or Podman machine.
  Wrappers adopt each reference tag through separate changes, so for a while
  they run different tags, as Pi did on `sandbox-ref-25` while the others
  were on `sandbox-ref-28`; propagating this change opens such a window
  again. Older code reads the library: `launch_env` refuses an `index.json`
  whose `schema` is not 1, and `render` copies each manifest's `source` into
  the index.
- All six wrappers build their runtime image on the same digest-pinned base.
- The reviewed recipes live in `docs/toolchains/`, which is neither installed
  in a release nor shared with the wrappers. The Rust recipe needs a local
  `podman build` of `rust-musl.Containerfile`.
- `setup/launch.py` puts `--container-git-worktree` in front of every argument
  list except qualification when setup saved the worktree scope, and
  `launcher/core.sh` accepts `--container-toolchain` only as the first
  argument. Every managed toolchain command therefore fails with that scope.
- The Windows bootstrap passes arguments unchanged and exports
  `WRAPPER_WINDOWS_ENTRY`, which reaches the wrapper and its Python children.
- "Toolchain" also names the guard's GCC/musl build image in `setup/setup.py`.
  This design only concerns the toolchain library.

## Goals / Non-Goals

**Goals:**
- One operator command installs any catalog toolchain on Linux and on Windows,
  with no environment variable, no manual download and no image build.
- Wrappers on older reference tags keep reading a library that newer code
  changed.

**Non-Goals:**
- Dependency registries, complete toolchain kits, a C/C++ toolchain and a
  stronger `add` check. See proposal.md.
- Changing the session mount, `env.sh`, `toolchains.md` or the default
  environment rules.
- Removing maintenance from image builds or from `--container-build`.

## Decisions

### D1. Pinned fetches need no maintenance; builds still do

`add` pulls digest-pinned images and downloads hash-pinned archives without
`<P>_MAINTENANCE`, and never builds an image.

Rationale: the maintenance gate protects operations that run code with
unfiltered network access (image builds). A toolchain fetch runs no code:
the content is fixed by digest or SHA-256, extraction is done by the module,
and the check runs without network. Running `add` is already an explicit
operator action on the host, which the agent cannot invoke. Any process that
could run `add` with the caller's identity could already run `podman pull`.

Alternatives: keep the gate (rejected: ceremony without protection, and it
breaks the one-command experience); ask for confirmation (rejected: the
command must work non-interactively and through the Windows entry).

### D2. Recipe schema 2 with a list of sources

Schema 2 replaces `source` with `sources`, a non-empty list (at most 16).
Each source is one of:

- `{"image": "<ref>@sha256:<digest>", "path": "/abs/dir", "target": "rel"}`
- `{"url": "https://...", "sha256": "<hex>", "path": "rel/member/dir", "target": "rel"}`
- `{"archive": "/abs/file", "sha256": "<hex>", "path": "...", "target": "..."}`

For archives, `path` selects one member subtree, whose contents are placed
at `target` (default: the toolchain root). `strip_components` stays accepted
as the alternative to `path`, for schema-1 compatibility. Sources are
extracted in order into one staging root. A regular file, link or special
node that a previous source already created makes `add` fail. Directories
merge. An archive used by several sources (same SHA-256) is fetched once per
command.

Schema-1 recipes are normalized at load into one-element `sources`, so the
rest of the module handles a single format.

Alternative: one toolchain per component, joined by `requires` (rejected:
`rustc` finds its standard libraries only inside its own sysroot, so the
components must share one root).

### D3. The library format stays readable by older wrappers

`index.json` keeps `schema: 1` and its fields. Manifests keep every key that
older code reads (`name`, `version`, `default`, `commands`, `path`, `env`,
`requires`, `notes`, `check`, `source`, `verified`). The `source` key holds
the list of fetched source records: URL or archive name with SHA-256, or
image, path and image ID. Older `render` copies it into the index without
reading it. Older `verify` and `remove` work on any installed toolchain.
Older `add` rejects schema-2 recipes with its usual schema error.

Alternative: a library schema bump with migration (rejected: a wrapper on an
older tag would fail every launch until it is propagated).

### D4. Downloads with the Python standard library on the host

The module downloads with `urllib.request` (Python 3.9, like the rest of
`setup/`):
- URLs must be `https://`, and a redirect handler refuses any non-HTTPS
  target;
- the TLS context uses `<P>_CA_BUNDLE` when `<P>_TRUST_HOST_CA=1` (both set
  by the managed launcher from setup's saved preferences), and the system
  trust otherwise;
- the host's proxy variables apply as usual;
- the file streams into a private `.download-*` file inside the library, so
  it stays on the same file system and outside the workspace;
- the hash is computed while downloading, and checked before extraction;
- there are a fixed size limit (4 GiB per archive) and fixed timeouts;
- the file is removed in every case.

`add` prints `Pulling <image>` and `Downloading <url>` lines before each
fetch.

Alternatives: `curl` or `podman pull` of a wrapper image in a container
(rejected: duplicates the CA and proxy plumbing and adds an image to pin).

### D5. Catalog in a shared directory of the release

The recipes move to `setup/toolchain-catalog/<name>.json`, under a shared
directory. They propagate to every wrapper, enter the installed manifest
(`setup/common.py`), and so reach releases and the Windows installed copy.
They are agent-neutral data, so the alignment checks apply unchanged. They
are not part of the qualified code identity, because they do not affect
enforcement.

`add` rule: an argument with no `/` that does not end in `.json` is a
catalog name; anything else is a path. An unknown name fails with the list of
catalog names. `list` prints installed toolchains, then `available` lines for
catalog recipes not installed.

Catalog contents: `java21`, `maven3.9` and `go` keep their image sources.
`node24` and `python3.13` use the URLs that `sources.json` lists today. `rust`
merges the `rustc`, `cargo` and `rust-std` (host and
`x86_64-unknown-linux-musl`) archives of 1.100.0 from
`static.rust-lang.org`. `tests/test_image_pins.py` checks that every catalog
recipe pins its images by digest and its URLs by SHA-256 over HTTPS.

Alternatives: keep the recipes in `docs/` (rejected: not installed, not
shared); fetch a catalog from the Internet (rejected: unpinned input).

### D6. Recipe location check

For a path argument, `add` resolves the recipe and refuses it when it lies
inside:
- the current directory, or its parent when the release's saved preferences
  (`setup.json` next to the module) have the worktree scope on;
- the state directories that `state_directories()` already derives.

This mirrors what a session started from the same directory would mount
writable. The check runs before any fetch. Local archives are not checked,
because the recipe pins their hash.

Limitation: a recipe inside another project's directory is not detected. The
README tells operators to keep their own recipes outside project directories.

Alternative: show the sources and ask for confirmation (rejected for the
same reasons as in D1).

### D7. Windows path translation in the toolchain module

When `WRAPPER_WINDOWS_ENTRY` is set, a recipe argument or a local `archive`
value matching `^[A-Za-z]:[\\/]` is translated through the drive's mount
point. The module reads that mount point from `/proc/self/mountinfo`: the
drvfs mount of the whole drive, with `path=X:\` and root `/`. This is the
mount namespace where the file is then opened. A bind mount of a drive
subdirectory, such as the machine's `/etc/containers`, is not a drive root.
UNC paths, `\\wsl$` and `\\wsl.localhost` paths and drives without a mount are
refused with the bootstrap's wording, and a translated path that does not
exist is reported as missing. Outside the Windows entry, paths are unchanged.

The first implementation called `wslpath -a -u`, as the bootstrap does. It
worked from a shell in the machine, but failed for every drive path once the
command ran through the Windows entry, after `enter.sh`. The validation on a
Podman machine found this, and the cause was not isolated. Reading
`mountinfo` needs no external program and no WSL environment, and gives the
same result as `wslpath -a -u` for drive paths.

Alternatives: translate in the PowerShell entry (rejected: it would break the
"arguments reach Bash unchanged" requirement, and it cannot see archive paths
inside a recipe); keep `wslpath` (rejected: see above).

### D8. The managed launcher keeps host commands unchanged

`setup/launch.py` adds `--container-git-worktree` only when the first argument
is not a host management command (`--container-toolchain`). Help, setup and
qualification already bypass it. `protect_mounts()` still runs with the saved
scope, so the overlap checks of a toolchain command do not change.

Alternative: accept `--container-toolchain` anywhere in `core.sh` (rejected:
"must be the first argument" is specified and tested, and it keeps host
commands from mixing with session options).

### D9. Setup re-verifies after selecting the new release

At the end of a successful setup, after the new release is selected, setup
runs the new release's `setup/toolchains.py verify <name>` for each installed
toolchain whose recorded `verified.base` differs from the release's base. It
runs one subprocess per toolchain, with the release's runtime image, and
collects failures. Failures are printed as one notice per toolchain that names
its check, and do not change setup's status.

Running after the release is selected matters. If a later setup step failed,
the old release would stay selected while the toolchains already recorded the
new base, and launches would lose their default environment.

Alternatives: verify at launch (rejected: launches would start containers
and change the library); leave it manual (rejected: the goal is no manual
step).

## Risks / Trade-offs

- [Host downloads happen outside runtime filtering] → only pinned content,
  over HTTPS, hash checked before extraction, documented like image pulls.
- [An upstream URL disappears] → local archive sources stay supported; a
  release can update the catalog.
- [Explicit HTTP proxies on Windows: the entry forwards no proxy variable] →
  documented limitation; image pulls use the machine's Podman configuration.
- [Rust component layout differs from the image-based tree] → the documented
  example test builds and runs an offline musl program with the new recipe,
  and compares the tree layout with the old one.
- [D6 misses recipes in other projects] → documented guidance; catalog
  recipes are the common path.
- [Setup takes longer after a base change] → only toolchains verified on
  another base are rechecked, one container each.
- [Mixed reference tags] → D3; a schema-2 toolchain installed by newer code
  works in older wrappers' sessions, and older `add` refuses only schema-2
  recipes.

## Migration Plan

1. Implement on a branch in this repository, run the runner modes that
   `docs/propagation.md` requires for `setup/` changes (`--shared`, `--setup`,
   `--setup-runtime`, `--network` with `SANDBOX_TOOLCHAIN_EXAMPLES=1`) and the
   Windows validation, then record them in `docs/validation.md`.
2. Tag a new `sandbox-ref-N`, and propagate to the five wrappers through
   separate changes, as the shared-component procedure requires.
3. Rollback: revert the merge. Installed toolchains stay readable by the
   older code (D3); recipes moved to the catalog are restored in `docs/`.

## Open Questions

- The exact Rust archive members (whether the host `rust-std` is needed next
  to the musl one) are settled while writing the recipe; the requirement and
  the tests do not depend on it.
