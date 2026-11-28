# Design

## Context

See `proposal.md` for motivation. Three defects surfaced when validating `sandbox-container` after `add-read-only-dependency-mirror` (`9f78976`) on a Windows Podman Machine host:

1. `network/.containerignore` is a deny-all allowlist (`**` plus `!file`), but `network/Containerfile` copies `mirror.py`, `mirror_policy.py`, `mirror_cache.py`, and `mirror_metadata.py`, causing every `mirror` or `provider` proxy build to fail at `STEP 2/4: COPY ...` (`copier: stat: "/mirror.py": no such file or directory`).
2. `network/mux.py` now imports `revisions`, and `network/session.py` bind-mounts `revisions.py` during sessions, but root `Containerfile` and `.containerignore` only copy `network/relay.py` and `network/mux.py`, leaving `/opt/sandbox-egress/mux.py` unimportable inside the standalone runtime image.
3. `setup/mirrors.py` translates Windows drive paths (`C:\...`) via `toolchains.windows_path()` when `WRAPPER_WINDOWS_ENTRY` is set, then calls `load_profile()` -> `common.trusted()`. Because WSL drvfs mounts expose mode `0777`, `common.trusted()` rejects every Windows-drive profile file while `windows_path()` rejects `\\wsl$\...`, leaving Windows operators unable to import any custom mirror profile file.

## Goals / Non-Goals

**Goals:**
- Make `network/Containerfile` and root `Containerfile` build contexts complete and self-consistent with their `.containerignore` allowlists and local Python imports.
- Prevent regressions with static unit tests checking `COPY` sources against `.containerignore` allowlists and verifying local imports of copied modules.
- Allow `--container-mirror add <file>` through the Windows entry to read regular, non-symlink operator profile files on mounted Windows drives outside writable mounts, matching the security boundary already used by `setup/toolchains.py` and `setup/common.py`'s `protect_windows_entry()`.

**Non-Goals:**
- Relaxing `trusted()` or `private()` for native Linux profile inputs, the protected release catalog, or the shared mirror library (`~/.local/share/sandbox-mirrors`), which remains strictly on protected native storage.
- Propagating changes to agent wrapper repositories or creating `sandbox-ref-37` within this change (handled via the standard propagation workflow once `sandbox-container` is verified).
- Changing mirror HTTP routing, cache behavior, or the public RPM catalog contents.

## Decisions

### D1: Complete `.containerignore` allowlists and track `network/.containerignore` in proxy reuse checks
- **Decision:** Add `!mirror.py`, `!mirror_policy.py`, `!mirror_cache.py`, and `!mirror_metadata.py` to `network/.containerignore`; add `!network/revisions.py` to root `.containerignore` and `network/revisions.py` to root `Containerfile`'s `COPY ... /opt/sandbox-egress/` line; add `'network/.containerignore'` to `proxy_inputs` in `setup/setup.py`.
- **Rationale:** Keeping explicit allowlists preserves minimal build contexts while ensuring every `COPY` source is present. Tracking `network/.containerignore` in `proxy_inputs` keeps proxy image reuse accurate when the context filter changes.
- **Alternative considered:** Removing `network/relay.py` and `network/mux.py` from the runtime `Containerfile` since `session.py` bind-mounts them. Rejected because keeping the baked-in copy consistent avoids breaking standalone image inspections and matches existing wrapper `Containerfile` structure.

### D2: Static build-context and local-import verification in `tests/test_image_pins.py`
- **Decision:** Add static tests in `tests/test_image_pins.py` (using Python's `ast` module and parsing `COPY` directives and `.containerignore` allowlists) for `Containerfile`, `network/Containerfile`, and `launcher/engine/Containerfile`:
  - Every file source copied by each `Containerfile` MUST exist and be admitted by the directory's `.containerignore` allowlist.
  - Every local `network/*.py` module imported by files copied into `network/Containerfile` and `Containerfile` MUST also be copied into that image.
- **Rationale:** These checks run in milliseconds without Podman or network access, so they execute inside guarded working sessions and catch omissions like `mirror.py` before closure.
- **Alternative considered:** Relying solely on real `podman build` during post-closure host validation. Rejected because guarded agent sessions cannot run `podman build` for `Containerfile` or `network/Containerfile`, which is exactly how this regression slipped into `main`.

### D3: Windows-drive operator input handling in `setup/mirrors.py`
- **Decision:** Introduce a helper in `setup/mirrors.py` (e.g., `windows_drive_input(path, env)`) that returns `True` only when `env.get(WINDOWS_ENTRY)` is set AND the resolved input path lies inside one of the mounted Windows drives reported by `toolchains.drive_mounts()`.
  - In `resolve_profile(argument, env, mounts)`:
    - Preserve `windows_path(argument)` translation for Windows drive/UNC arguments when `WINDOWS_ENTRY` is set.
    - Keep `outside_mounts(path, mounts)` (augmented with `Path(env[WINDOWS_ENTRY]).resolve()` when `WINDOWS_ENTRY` is set, matching `protect_windows_entry`) so no input file or symlink alias can overlap the workspace, widened worktree parent, state dirs, or Windows entry directory.
    - When `windows_drive_input(physical, env)` is `True`: refuse any symlink component (`links` non-empty) and read the file via `read_json(physical, mirror_policy.MAX_PROFILE, protected=True)` (which enforces `O_NOFOLLOW`, `O_NONBLOCK`, `S_ISREG`, `st_nlink == 1`, size limit, strict JSON) and `mirror_policy.profile(data, catalog=False)` without running POSIX `common.trusted()` on drvfs ancestors.
    - Otherwise (native Linux paths, non-Windows invocations, or any path not on a mounted Windows drive): continue calling `load_profile(physical)` with full POSIX `common.trusted()` verification.
  - Keep `load_profile(..., catalog=True)` for catalog entries and `open_library()` -> `private()` -> `trusted()` for `~/.local/share/sandbox-mirrors` completely unchanged.
- **Rationale:** Matches `setup/toolchains.py` (`resolve_recipe` + `check_recipe_location`) and the explicit comment in `setup/common.py` (`# drvfs paths cannot pass trusted(): the protection is that no mount reaches them`), while strictly confining the POSIX-permission relaxation to verified Windows-entry drvfs input files and still preventing symlinks, hardlinks, and writable-mount overlaps.
- **Alternative considered:** Requiring Windows users to place custom mirror profiles inside WSL native storage via `wsl.exe`. Rejected because it violates the existing `dependency-mirror` spec scenario ("relative file and Windows drive paths follow the host command's existing context rules") and conflicts with `windows_path()` refusing `\\wsl$\...`.

### D4: Recognize `mirror` mode in `tools/windows-validate.ps1`
- **Decision:** Treat saved `mirror` mode identically to `provider` mode in `tools/windows-validate.ps1` (restricted installation with guard prepared, running `Offline qualification` before offline session and nested session-engine checks).
- **Rationale:** Real-host validation on PowerShell 7.7.0 Core against a `mirror` installation showed `windows-validate.ps1` falling into the `unrestricted` branch, causing a false failure on `Restricted mode without a prepared installation` and unnecessary skips on `Offline session; Qualification` and `Session with library images`.

## Risks / Trade-offs

- **Risk:** Relaxing `trusted()` too broadly in `setup/mirrors.py` could allow unsafe world-writable Linux directories (such as `/tmp`) to supply operator mirror profiles.
  - **Mitigation:** Gate the relaxation strictly on BOTH `env.get(WINDOWS_ENTRY)` being set AND the resolved path residing inside an actual drvfs mount reported by `toolchains.drive_mounts()`, while still rejecting symlinks, hardlinks, and any overlap with workspace, widened worktree, state, or Windows entry mounts. Cover both positive (simulated drvfs `0o777` mount with `WINDOWS_ENTRY`) and negative (same `0o777` directory without `WINDOWS_ENTRY`, or symlink/workspace overlap with `WINDOWS_ENTRY`) cases in `tests/test_mirror_profiles.py`.
- **Risk:** Simple `.containerignore` parsing in tests could give false positives or negatives if glob syntax grows more complex later.
  - **Mitigation:** Parse the concrete allowlist pattern (`**` + `!entry`, plus directory re-exclusion like `network/**` + `!network/file`) used across all three shipped `.containerignore` files, and include mutation self-tests in `tests/test_image_pins.py` proving that omitting an entry or adding an uncopied import fails the check.
- **Risk:** Adding `network/revisions.py` to `Containerfile` and `.containerignore` is reference-only here; wrapper `Containerfile`s and `.containerignore`s will need the same one-line update when they adopt the next reference tag.
  - **Mitigation:** `tools/propagate.py` already flags `Containerfile` and `.containerignore` as review lines during wrapper adoption; record this in the validation log and propagation notes when tagging `sandbox-ref-37`.
