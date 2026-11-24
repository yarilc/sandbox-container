# Tasks

## 1. Host commands with the saved worktree scope

- [x] 1.1 In `setup/launch.py`, add `--container-git-worktree` only when the first argument is not `--container-toolchain` (design D8); verify with a new `tests/test_setup.py` case where saved preferences have `worktree: true` and the managed launcher runs `--container-toolchain list` successfully, while a session launch from the same launcher still receives the worktree option
- [x] 1.2 Verify the existing managed-launcher and overlap cases still pass: `python3 -m unittest tests.test_setup tests.test_launcher`

## 2. Recipe schema 2 and multi-source extraction

- [x] 2.1 Extend recipe validation in `setup/toolchains.py` with schema 2 (`sources` list; image, URL and archive sources; `path`/`target` or `strip_components`) and normalize schema-1 recipes to it (design D2); verify with `tests/test_toolchains.py` cases for valid and rejected schema-2 recipes and an unchanged schema-1 recipe
- [x] 2.2 Extract sources in order into one staging root, merging directories, failing on a file created twice, and fetching an archive used by several sources once; verify with cases for a merged tree, a duplicate file (library unchanged) and a shared archive
- [x] 2.3 Keep `index.json` at schema 1 and every manifest key older code reads, storing the list of source records under `source` (design D3); verify with a case that asserts the index schema and manifest keys, and that the index entries and `launch-env` output for a schema-2 toolchain match those of an equivalent schema-1 toolchain

## 3. Fetches without maintenance and archive downloads

- [x] 3.1 Remove the `<P>_MAINTENANCE` requirement from image pulls in `add` and print a `Pulling <image>` line; verify with a `tests/test_toolchains.py` case using `tests/fake_podman.py` where `add` pulls a missing digest-pinned image with the variable unset, and a case where a failed pull names the image and leaves the library unchanged
- [x] 3.2 Implement HTTPS archive downloads (design D4): HTTPS only, redirect refusal to non-HTTPS, CA bundle from `<P>_CA_BUNDLE` when `<P>_TRUST_HOST_CA=1`, size limit, timeouts, hash before extraction, `Downloading <url>` line and cleanup in every case; verify with local HTTPS fixture cases for success with a private CA bundle, an `http://` URL, a redirect to `http://`, a checksum mismatch, and no `.download-*` file left after each
- [x] 3.3 Update the `--container-toolchain` help text in `launcher/core.sh` (`add <recipe.json|name>`), the README "Managing the library" section and `docs/setup.md` (pulls and downloads without maintenance, builds still under maintenance); verify with `tests/test_launcher.py` usage cases and `bash tools/shellcheck.sh`

## 4. Release catalog

- [x] 4.1 Move the recipes to `setup/toolchain-catalog/` as schema-2 recipes with image digests or HTTPS URLs and SHA-256 (Node.js and Python from the former `sources.json`), delete `docs/toolchains/`, and add the catalog to the installed manifest in `setup/common.py`; verify that `python3 -I setup/common.py --manifest` lists every catalog file and that `tests/test_alignment.py` passes
- [x] 4.2 Write the `rust` catalog recipe from the `rustc`, `cargo` and `rust-std` (host and `x86_64-unknown-linux-musl`) 1.100.0 archives of `static.rust-lang.org`, settling the exact members (design Open Questions); verify by adding it in a scratch library and building an offline musl hello world with `cargo build --offline` through `env.sh`
- [x] 4.3 Implement `add <name>` (name rule, unknown name listing the catalog) and the `available` lines of `list` (design D5); verify with `tests/test_toolchains.py` cases for add by name, an unknown name that fetches nothing, and `list` with one installed recipe
- [x] 4.4 Check the catalog in the shared `tests/test_toolchains.py`, so every wrapper checks its own copy (every image by digest, every URL HTTPS with SHA-256, remote sources only, file names matching recipe names, every file in the installed manifest, mutated recipes rejected); verify with `python3 -m unittest tests.test_toolchains`
- [x] 4.5 Update the documented-examples runtime test in `tests/test_network_runtime.py` to add each catalog recipe by name without maintenance or manual downloads; verify with `SANDBOX_TOOLCHAIN_EXAMPLES=1 bash tests/run-runtime.sh --network -k documented_toolchain`
- [x] 4.6 Rewrite the README "Recipes" section around the catalog (table of catalog recipes, `add <name>`, operator recipes by path, schema 2 keys); verify that every command in the section runs as written in a scratch library

## 5. Recipe location check

- [x] 5.1 Refuse an operator recipe inside the current directory, its parent with the saved worktree scope, or a state directory, before any fetch, exempting catalog recipes and local archives (design D6); verify with `tests/test_toolchains.py` cases for each refusal, a recipe outside the mounts, a local archive inside the workspace and a catalog name
- [x] 5.2 Document in the README that operator recipes belong outside project directories and why; verify the text names the workspace refusal and its limit

## 6. Windows paths and documentation

- [x] 6.1 Translate Windows drive paths of the recipe argument and of local `archive` values when `WRAPPER_WINDOWS_ENTRY` is set, refusing UNC, WSL and unmounted-drive paths (design D7); verify with `tests/test_toolchains.py` cases using a fake `wslpath`, including unchanged behavior without the variable
- [x] 6.2 Update the README Windows section: toolchain commands from PowerShell, Windows paths, the library living inside the Podman machine and lost when the machine is recreated, and the explicit-proxy limitation; verify the section states the library location and the effect of recreating the machine
- [x] 6.3 Add `tools/windows-validate.ps1` cases for `add <name>`, `add` with a Windows recipe path, and `list` with the saved worktree scope; verify by running the script on a Windows host with a Podman machine and recording the result

## 7. Setup re-verification

- [x] 7.1 After setup selects the new release, run the release's `verify <name>` for each installed toolchain whose verified base differs from the release base, printing one notice per failure without changing setup's status (design D9); verify with `tests/test_setup.py` cases for a changed base, a failing check and nothing to re-verify
- [x] 7.2 Document the automatic re-verification in `docs/setup.md` and the README toolchain section; verify the text matches the setup output of 7.1

## 8. Integration and validation

- [x] 8.1 Run the runner modes required by `docs/propagation.md` for `setup/` changes and for files in `SHARED_CODE` (`--shared`, `--setup`, `--setup-runtime`, `--qualification`), plus `--network`, `bash tools/shellcheck.sh` and `git diff --check`; verify all pass, apart from failures already recorded for the host
- [x] 8.2 On Linux and on Windows with a Podman machine, run setup with the saved worktree scope, add `java21` and `go` by name, and start an offline session where `java -version` and `go version` work; verify and record the results
- [x] 8.3 Record every mode, host and result in a new section of `docs/validation.md`; verify that the section names the change and lists any unavailable check as unavailable

## Workflow follow-up

- Tag a new `sandbox-ref-N` and propagate the shared files to the Claude, Codex, OpenCode, Pi and Antigravity wrappers through separate changes, following `docs/propagation.md`.
- Archive this change with the spec sync once the validation record is complete.
