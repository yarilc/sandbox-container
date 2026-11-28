# Tasks

Run working-session checks from `/mnt/d/Workspace/sandboxes/sandbox-container`. For tests requiring private native Linux permissions (`test_setup`, `test_mirror_profiles`), run inside disposable offline `localhost/docgen:1.0.0` with a private `0700` tmpfs `SANDBOX_TEST_TMPDIR`. Record results and unavailable real-host checks in `docs/validation.md` and keep host-only checks in `## Follow-up after closure`.

## 1. Proxy and runtime build contexts

- [x] 1.1 Update `network/.containerignore` to admit `!mirror.py`, `!mirror_policy.py`, `!mirror_cache.py`, and `!mirror_metadata.py`, and add `'network/.containerignore'` to `proxy_inputs` in `setup/setup.py`. Add a `test_setup.py` case verifying that modifying `network/.containerignore` invalidates proxy image reuse. Verify with `tests.test_setup` (passing with 0 failures/errors).
- [x] 1.2 Add `network/revisions.py` to root `Containerfile`'s `COPY ... /opt/sandbox-egress/` instruction and `!network/revisions.py` to root `.containerignore`. Add static tests in `tests/test_image_pins.py` checking that (a) every `COPY` source in `Containerfile`, `network/Containerfile`, and `launcher/engine/Containerfile` exists and is admitted by its sibling `.containerignore` allowlist, (b) every local `network/*.py` import of files copied into `network/Containerfile` and `Containerfile` is also copied into that image, and (c) mutating `.containerignore` or dropping a copied dependency fails the check. Verify with `python3 -B -m unittest tests.test_image_pins -v`.

## 2. Windows-drive operator mirror profiles

- [x] 2.1 Update `setup/mirrors.py` (`design.md` D3) so `resolve_profile()` accepts a regular, non-symlink operator profile file located on a mounted Windows drive (`toolchains.drive_mounts()`) when `WRAPPER_WINDOWS_ENTRY` is set, enforcing `outside_mounts()` (including the Windows entry directory), `O_NOFOLLOW`, `S_ISREG`, `st_nlink == 1`, size bounds, and `mirror_policy.profile()` without calling POSIX `common.trusted()` on drvfs ancestors, while preserving full `common.trusted()` checks for native Linux inputs, the release catalog, and the private mirror library (`open_library()`). Update `docs/setup.md` ("Dependency mirror profiles") to reflect Windows drive profile files alongside native storage.
- [x] 2.2 Extend `tests/test_mirror_profiles.py` to test: (a) adding an operator profile via an explicit Windows drive path (`C:\...`) and via a relative path on a simulated `0o777` drvfs mount when `WRAPPER_WINDOWS_ENTRY` is set, verifying atomic installation into the `0o700` native library; (b) refusing Windows-drive inputs that overlap the workspace, widened worktree, state directory, or `WRAPPER_WINDOWS_ENTRY`, or traverse a symlink; (c) still refusing a `0o777` input when `WRAPPER_WINDOWS_ENTRY` is unset or the path is outside mounted Windows drives; and (d) still refusing a library path on `0o777` storage. Verify with `tests.test_mirror_profiles` in private native storage.

## 3. Working-session integration and validation record

- [x] 3.1 Run the affected test suites and static checks (`tests.test_image_pins`, `tests.test_alignment`, `tests.test_setup`, `tests.test_mirror_profiles`, `tests.test_dependency_mirror`, `tests.test_launcher`, `tests.test_qualification`, `py_compile`, `git diff --check`, and `openspec validate fix-mirror-build-context-and-windows-profiles --strict`), verifying all pass with 0 failures and 0 errors.
- [x] 3.2 Update `tools/windows-validate.ps1` so saved `mirror` mode is recognized as a restricted installation alongside `provider` (running offline qualification before offline and session-engine checks) and verify ASCII-only, LF-only formatting with `tests.test_alignment` and `git diff --check`.
- [x] 3.3 Record the working-session and real-host Windows validation results, commands, and remaining follow-ups in `docs/validation.md`.

## Follow-up after closure

- On Windows (PowerShell 5.1 / 7) with Podman Machine: rerun `.\sandbox-container.ps1 --container-install` (or `sandbox-container --container-setup`) choosing `mirror` mode with refresh enabled, and verify `network/Containerfile` builds cleanly and qualification passes.
- On Windows PowerShell: run `sandbox-container --container-mirror add rocky9`, `add al2023`, `add C:\<outside-workspace>\custom.json`, `list`, and `verify`, confirming both catalog profiles and a Windows-drive operator profile install and verify cleanly while a profile inside the workspace is rejected.
- On WSL or native Linux host: run `bash tests/run-runtime.sh --qualification`, `bash tests/run-runtime.sh --network`, `bash tests/run-runtime.sh --setup-runtime`, `bash tools/shellcheck.sh .`, and `bash tools/powershell.sh .`, plus Windows `.\tools\windows-validate.ps1`.
- Once verified, tag `sandbox-ref-37` and propagate shared changes (including wrapper `Containerfile`/`.containerignore` updates for `network/revisions.py`) to the five agent wrappers.
