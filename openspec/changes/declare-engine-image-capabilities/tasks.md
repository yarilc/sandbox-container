# Tasks

## 1. The engine image's capability label

- [x] 1.1 Commit this change directory on `main`, then create the branch `declare-engine-image-capabilities`. Verify: `openspec validate declare-engine-image-capabilities --strict` passes, and `git status` is clean on the new branch.
- [x] 1.2 Add `LABEL io.containers.capabilities="SETUID,SETGID,SYS_CHROOT,CHOWN"` to `launcher/engine/Containerfile`, beside `USER podman`, with a comment that names `container_options()` in `setup/engine.py` (design decisions 1 and 2). In `tests/test_engine.py`, the recipe check compares the label with the `--cap-add=` value of `engine.container_options()`. Verify:
  - `python3 -m unittest tests.test_engine` passes. Where no rootless engine runs and the tests cannot start as root, the startup program, cgroup and entrypoint cases fail as they do on `main`; they run in the host discovery (tasks 2.1 and 2.2);
  - new mutation cases fail the check: a recipe without the label, a label with `KILL` added, and a label without `CHOWN`.
- [x] 1.3 In the README's hardening exceptions paragraph (Container tests), say that the engine image declares the same four capabilities, so that Podman reports no capability error (design decision 3). Verify:
  - the paragraph names `io.containers.capabilities`;
  - `python3 -m unittest tests.test_alignment tests.test_engine` and `git diff --check` pass;
  - commit on the branch.

## 2. Validation on the native hosts

- [ ] 2.1 Have the operator run the branch on WSL. Full logs go to files, collected in one archive in the workspace root.
  - **Before:** build the branch's recipe twice (design decision 4):
    - without its label line, as `localhost/sandbox-container-engine:before-label`;
    - as it is, as `localhost/sandbox-container-engine:latest`, which the runner uses.
  - **Image comparison:** for both images, `podman run --rm --cap-drop=all --cap-add=SETUID,SETGID,SYS_CHROOT,CHOWN --security-opt=no-new-privileges --entrypoint sh <image> -c "grep CapBnd /proc/self/status"`, with standard error kept.
  - **Modes:**
    - the unit discovery in the runtime image;
    - the default runtime mode;
    - `--network` and `--qualification`.

  Verify:
  - the new image prints no `Capabilities requested` error;
  - both images report `CapBnd: 00000000000400c1`;
  - every mode passes, or fails only as already recorded for this host.
- [x] 2.2 Have the operator run the same on the Rocky 9 lab host.
  - **Before:** check the free space in `/home` and the guard toolchain image.
  - **Sessions:** add two unrestricted sessions that start an engine, from the checkout, where the toolchain library holds image toolchains: `SANDBOX_CONTAINER_NETWORK=unrestricted ./sandbox-container.sh -c true`, once with `SANDBOX_CONTAINER_ENGINE_IMAGE=localhost/sandbox-container-engine:before-label` and once with the default image.

  Verify:
  - the image without the label prints the error and the new one does not, both with `CapBnd: 00000000000400c1`;
  - only the session with the image without the label prints a `Capabilities requested` line, and both sessions exit with status 0;
  - the modes pass, with the guarded terminal tests unavailable as recorded for `sandbox-ref-35`.

- [ ] 2.3 Have the operator run `--setup` and `--setup-runtime` on both hosts, from the branch. `sandbox-ref-36` also carries `support-nested-systemd-containers`, which changed `setup/common.py`, `setup/engine.py` and `setup/toolchains.py`. For those files the propagation checklist names these two modes, and that change's records do not list them (`reference-propagation`, "Reference runs the adoption suites before tagging"). Verify:
  - both modes pass on WSL and on the Rocky 9 lab host;
  - `podman images --format '{{.Repository}}:{{.Tag}}'` is identical before and after `--setup-runtime`.

## 3. Record, merge and tag

- [ ] 3.1 Record and tag.
  - **Record:** the section "Reference tag `sandbox-ref-36`" at the top of `docs/validation.md`, with the results of tasks 1 and 2: Podman versions, image IDs, the comparison output, and every mode.
  - **Parity:** the reference row's contract adoption cell and its real enforcement entry name `sandbox-ref-36`.
  - **Merge and tag:** commit with the co-author trailer, merge into `main`, and create the annotated tag `sandbox-ref-36` on the merge commit.

  Verify:
  - `git tag -n1 sandbox-ref-36` names the merge commit;
  - the dry run `python3 -I tools/propagate.py ../claude-container sandbox-ref-35 sandbox-ref-36` lists `launcher/engine/Containerfile` and `tests/test_engine.py` as modified.

## Workflow follow-up

- The operator pushes `main` and the tag.
- Archive this change with spec sync, which adds "Engine image declares its capabilities" to `session-container-engine`.
- Claude adopts `sandbox-ref-36` from `sandbox-ref-35`. Codex, Antigravity, OpenCode and Pi adopt it from `sandbox-ref-28`.
