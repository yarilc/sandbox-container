# Proposal

## Why

The first real-host Windows Podman Machine installation of `sandbox-container` in `mirror` mode failed during `podman build network/Containerfile` because `network/.containerignore` is an allowlist that still omits the four mirror modules added in `add-read-only-dependency-mirror` (`mirror.py`, `mirror_policy.py`, `mirror_cache.py`, `mirror_metadata.py`). Auditing the same release surface before tagging `sandbox-ref-37` revealed two related gaps: the runtime image `Containerfile` copies `network/mux.py` (which now imports `revisions`) without `network/revisions.py`, and `--container-mirror add <file>` rejects every operator profile on a Windows drive because `setup/mirrors.py` runs POSIX `trusted()` on drvfs paths after translating them.

## What Changes

- Update `network/.containerignore` to admit `!mirror.py`, `!mirror_policy.py`, `!mirror_cache.py`, and `!mirror_metadata.py`, and include `network/.containerignore` in `setup/setup.py`'s `proxy_inputs` reuse check so build-context filter changes invalidate cached proxy image reuse.
- Add `network/revisions.py` to the root `Containerfile` `COPY` list and root `.containerignore` allowlist so `/opt/sandbox-egress/mux.py` and `/opt/sandbox-egress/relay.py` remain self-consistent inside the built runtime image.
- Add static verification tests in `tests/test_image_pins.py` (and/or shared alignment checks where appropriate) asserting that every `COPY` source in the shipped `Containerfile`s is admitted by its sibling `.containerignore` allowlist and that local Python imports of files copied into `network/Containerfile` and `Containerfile` are satisfied.
- Update `setup/mirrors.py` so operator profile files supplied through the Windows entry on a mounted Windows drive (both explicit drive paths such as `C:\...` and relative paths resolving onto a Windows drive mount) follow the same host-boundary protection model as `setup/toolchains.py` (regular non-symlink file outside writable workspace, widened worktree, and state mounts, without requiring POSIX mode bits that drvfs cannot represent), while preserving strict `trusted()`/`private()` checks for native Linux inputs, the protected catalog, and the private mirror library.
- Update `docs/setup.md` and `tests/test_mirror_profiles.py` to document and test Windows-drive operator mirror profile files alongside native protected inputs.
- Update `tools/windows-validate.ps1` to recognize saved `mirror` mode alongside `provider` as a restricted installation that prepares the guard and runs offline qualification before offline and session-engine checks.

## Capabilities

### New Capabilities

<!-- None: this change fixes regressions and clarifies existing contracts. -->

### Modified Capabilities

- `container-setup`: require image build-context allowlists (`.containerignore`) to admit every file copied by their `Containerfile` and include `network/.containerignore` in proxy image reuse detection.
- `dependency-mirror`: align Windows-entry operator profile file validation with host drive-mount semantics so valid profile files on Windows drives outside writable mounts can be added while keeping native inputs, the catalog, and the mirror library strictly protected.

## Impact

- Affected shared files (propagated to wrappers on the next reference tag): `network/.containerignore`, `setup/setup.py`, `setup/mirrors.py`, `tests/test_mirror_profiles.py`.
- Affected reference files: `Containerfile`, `.containerignore`, `tests/test_image_pins.py`, `tools/windows-validate.ps1`, `docs/setup.md`, `docs/validation.md`.
- Blocks tagging `sandbox-ref-37` until fixed and verified so wrapper adoptions do not inherit a broken proxy build context or unusable Windows custom mirror profile imports.
