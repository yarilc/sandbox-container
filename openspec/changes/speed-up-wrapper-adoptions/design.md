# Design

## Context

`tools/propagate.py` plans and applies an adoption. Its `checklist()` returns
runner mode names from five prefix rules:
- setup;
- qualification;
- guard and network code;
- `network/agent_profile.py`;
- the always-present copy and alignment tests.

`report()` prints them as `bash tests/run-runtime.sh <mode>`. No rule covers
`launcher/`, the engine inputs, the `SHARED_CODE` qualification rule that
`docs/propagation.md` states in prose, the changed shared test modules or the
test helpers.

Claude's adoption of `sandbox-ref-36` showed where time goes (see proposal.md):
- **Hand-picked commands:** the maintainer chose the commands by hand, from
  the dry run and the diff;
- **A hand-written runner line:** the maintainer wrote the operator's
  runner line by hand, about 2,000 characters, and it lacked
  `SANDBOX_TEST_TMPDIR`;
- **A manual search:** the reference changes in the range, and their spec
  deltas, were found by hand.

Facts the design relies on:
- **Wrapper test names:** the wrappers' engine test names follow the
  reference's. Claude has `SessionEngineTests` and
  `test_offline_session_engine_has_no_external_path`. The four wrappers on
  `sandbox-ref-28` will port them in their next adoption.
- **Runner arguments:** each wrapper's `tests/run-runtime.sh` passes its extra
  arguments to `unittest discover`, so `-k` selects cases.
- **Python versions:** the Rocky 9 lab host has Python 3.9. The tests need
  3.11 (`asyncio.timeout`). The reference's unit discovery ran there in the
  runtime image, without network and with a private tmpfs, and that command
  is proven. WSL has a newer Python, and Claude's host unit tests passed there
  with `SANDBOX_TEST_TMPDIR=~/sbx-tmp`.
- **Runtime images:** a test that needs a prepared image skips with
  `prepare <image> in the engine first`.
- **Image names:** the engine image is `<images.agent>-engine:latest`, the
  runtime image `<images.agent>:latest`, and the guard toolchain
  `<images.toolchain>:development`. All three come from the target's
  `agent/profile.json`.

## Goals / Non-Goals

**Goals:**
- The tool prints the full validation perimeter of an adoption, and the
  runner executes it on one host in one line.
- A wrapper file that lists shared files is flagged before the suites run.
- The adoption change's spec deltas can be found from the tool's output.
- Everything runs on Python 3.9 and on WSL.

**Non-Goals:**
- No runner for the reference's own pre-tag runs. The reference keeps running
  its full modes, now stated for both hosts.
- No automation of Windows validation, parity-row copies, commits or pushes.
- No generation of OpenSpec artifacts. The tool only lists the reference
  changes.
- No change to the wrappers' `tests/run-runtime.sh` or to any shared file, so
  no new tag.

## Decisions

1. **The checklist becomes a list of entries.**
   - **Shape:** `checklist()` returns entries `(name, kind, command)` with the
     kinds `unit`, `mode`, `prepare`, `image` and `manual`.
   - **Uses:** `report()` prints them as "Run in the target" and as one
     template row each. `--checklist` prints them as tab-separated lines for
     the runner.
   - **Names:**
     - `unit`;
     - the mode names without `--`, and `runtime` for the default mode;
     - `runtime-engine` and `network-engine` for the `-k` selections;
     - `engine` for the image rebuild.
   - **Order:** `unit`, then `setup`, `setup-runtime`, `qualification`,
     `wrapper`, `runtime`/`runtime-engine`, `network-feasibility`, `guard`,
     `network`/`network-engine`, then manual steps.
   - **Rejected: keep mode strings and add parallel lists.** The report, the
     template and the runner would drift apart.

2. **Mapping from changed files to entries.** The rules are cumulative, and a
   selection is dropped when the same mode is named in full.

   | Changed file | Entries |
   | --- | --- |
   | any | `unit` with `tests.test_reference_copy` and `tests.test_alignment` |
   | `setup/`, `tests/test_setup.py` | `setup`, `setup-runtime` (unchanged rule) |
   | qualification files (unchanged rule), or a file in the new tag's `SHARED_CODE` | `qualification` |
   | guard, proxy, session, multiplex, TLS or policy code (unchanged rule) | `guard`, `network` |
   | `network/agent_profile.py` | `wrapper` (unchanged rule) |
   | `launcher/` outside `engine/` and `windows/` | `wrapper`, `runtime` |
   | `launcher/engine/`, `setup/engine.py` | `prepare engine`, `runtime-engine` and `network-engine` when the target defines the cases, else `runtime` and `network` |
   | `launcher/windows/`, `*.ps1` | `manual`: `tools/windows-validate.ps1` on Windows PowerShell 5.1 |
   | a shared `tests/test_*.py` | its mode from a fixed table, when the target offers that mode; otherwise the module joins `unit` |
   | a shared test helper (`tests/*.py` that is not a test module) | each target module that imports it, mapped by the row above |

   - **Mode table:**
     - `test_setup` runs in `--setup` and `test_qualification` in
       `--qualification`;
     - `test_launcher` runs in `--wrapper` and `test_guard` in `--guard`;
     - `test_network_feasibility`, `test_network_policy` and `test_mux` run
       in their own modes.
   - **Where `SHARED_CODE` comes from:** it is read from the new tag's
     `network/qualification_records.py` with `ast`, as `shared_set()` reads
     `tests/test_alignment.py`.
   - **How the engine cases are found:** a regular expression looks for
     `class SessionEngineTests` and
     `def test_offline_session_engine_has_no_external_path` in the target's
     tests.
   - **How helper imports are found:** `^\s*(from|import) <helper>\b` in the
     target's `tests/test_*.py`.
   - **Image entries:** the runtime image always, and the guard toolchain
     when `qualification`, `guard` or `network` (in full or as a selection)
     is named.
   - **Example, Claude's `sandbox-ref-35` to `sandbox-ref-36`:**
     - `unit` (copy, alignment, `test_engine`, `test_toolchains`);
     - `setup`, `setup-runtime`, `qualification` and `wrapper`;
     - the full `runtime`, because `launcher/core.sh` changed, so the
       selection `runtime-engine` is dropped;
     - `network-engine`.

     This is the set run on 2026-11-26, with the full default mode instead
     of its engine class. That costs about five more minutes on WSL, but the
     launcher core runs in every session.
   - **Rejected: run the full default mode only for engine changes.** A core
     change that is not about the engine would then get only `--wrapper`,
     which uses a fake Podman.

3. **Host unit tests get private storage in the printed command.** The report
   prints `SANDBOX_TEST_TMPDIR=<private directory> python3 -m unittest ...`
   for `unit`. The runner supplies the directory:
   - **Host:** with host Python 3.11 or later, `mktemp -d
     "$HOME/.sbx-test-XXXXXX"` (mode 0700). It is removed after the run,
     but only when the path still matches that pattern.
   - **Runtime image:** with an older Python, the reference's proven
     in-image command:
     - `--network=none --userns=keep-id`;
     - a private tmpfs at `/sandbox-test-tmp`;
     - the checkout and the reference checkout bound at their own paths,
       the latter read-only, so the sibling check of `test_reference_copy`
       runs.

     Cases that need a rootless engine skip there, and the summary lists
     them.

4. **Review warnings by directory.**
   - **Trigger:** for each added or removed shared path, with directory `D`.
   - **Needles:** the full paths of the other shared files under `D` at
     either tag.
   - **Where it searches:** every tracked file of the target from
     `git ls-files`, except:
     - the shared files and the manifest;
     - `docs/validation.md` and `CHANGELOG.md`;
     - `openspec/`.

     Undecodable files are skipped.
   - **Output:** each matching line prints as `review: <path>:<line>`, in the
     dry run and in the applied run.
   - **Measured:** Claude's checkout at `sandbox-ref-35` gives
     `tests/test_network_runtime.py:90` (the real defect) and
     `tests/run-runtime.sh:10`, a comment that is a harmless false positive.
   - **Rejected: parse Python lists or `shutil.copyfile` calls.** That is
     specific to one file shape, and still misses shell scripts.

5. **Reference changes from the range's history.**
   - **Names:** `git log --name-only --format= <old>..<new> --
     openspec/changes` in the reference gives the paths. Change names come
     from `openspec/changes/<name>/` and
     `openspec/changes/archive/<date>-<name>/`.
   - **Location at `HEAD`:** each name resolves in the reference's working
     tree, first the active directory, then the latest
     `archive/*-<name>`.
   - **Deltas:** `specs/**/spec.md` gives the capability paths, and a
     capability without `openspec/specs/<capability>/spec.md` in the target
     is marked `[not in target]`.
   - **Example, `ref-35..ref-36`:**
     - `support-nested-systemd-containers` and
       `declare-engine-image-capabilities`, both archived, both with a
       `session-container-engine` delta;
     - `keep-parity-history-in-propagation`, archived, its
       `reference-propagation` delta marked as not in the target;
     - `add-read-only-dependency-mirror`, active.
   - **Why history and not the tag's tree:** a change can be archived after
     its tag, as `declare-engine-image-capabilities` was.

6. **The runner is a Bash script driven by `--checklist`.**
   - **Shape:** `tools/adoption-run.sh [--only a,b] <wrapper> <old> <new>`
     runs `python3 -I tools/propagate.py <wrapper> <old> <new> --checklist`
     from its own checkout. A test-only `SANDBOX_ADOPTION_REFERENCE`
     variable becomes the tool's hidden `--reference`.
   - **Per entry:** a log `<name>.log`, then a summary line:
     - the exit status;
     - the last `OK` or `FAILED` line;
     - the `... skipped '<reason>'` lines;
     - `NOT PREPARED` for a reason that starts with `prepare `.
   - **Unit output:** `unit` runs with `-v`, so its skips are listed too.
   - **Shell mode:** `set -Euo pipefail` without `-e`, so a failed entry
     does not stop the run.
   - **Preparations:** they run in every run, `--only` included. The engine
     rebuild is a cache hit when nothing changed.
   - **Logs:** the directory is
     `$HOME/sbx-logs-<wrapper>-<tag>-<host>-<YYYYmmdd-HHMMSS>`, and the
     archive is the same name with `.tar.gz`.
   - **Image lists:** before and after the run. Around `setup-runtime`, the
     tags and their `diff`.
   - **Free space:** `df -Pk` of `$HOME` and `/tmp`, with a floor of 1 GiB.
   - **Exit status:** zero only with every entry at zero and nothing marked
     not prepared.
   - **Rejected: a Python runner.** Process control, `podman` and `tar` are
     simpler in Bash, and the script must not need the tests' Python 3.11.
     `tools/propagate.py` holds all the logic that needs tests.

7. **Procedure: one host for adoptions, two for the reference.**
   - **Tagging (step 1 of `docs/propagation.md`):** the reference runs the
     checklist's modes in full on WSL and on the native Linux host before
     tagging.
   - **Verification (step 3):** the wrapper runs
     `bash tools/adoption-run.sh ../<wrapper> <old> <new>` on the host where
     it is used, copies the archive, and records:
     - every entry;
     - the entries not run, citing the reference's record;
     - for the wrapper's own changed files, the mode or cases that exercise
       them.
   - **Rerun:** `--only` reruns entries after a wrapper-only fix.

## Risks / Trade-offs

- **[Selections rely on test names shared by convention]** → a target without
  the cases gets the full modes. A renamed case falls back the same way.
- **[Helper import scan misses dynamic imports]** → a helper change also
  changes a test module in the same tag in practice. A full mode remains one
  `--only` away.
- **[`tools/propagate.py` on Python 3.9]** → its syntax already parses as 3.9,
  but nothing exercises its runtime there. The Rocky acceptance run (task 4.2)
  runs `--checklist` on the host's Python 3.9.
- **[In-image unit runs skip engine cases]** → the summary lists the skips.
  Those cases are the reference's evidence, from its WSL run.
- **[Review warnings give false positives]** → they are lines to look at, not
  failures, and they print only for ranges with additions or removals.
- **[One host per adoption hides host-specific wrapper behavior]** → wrappers
  add no host-specific code to shared components, and the reference covers
  both hosts.

## Migration Plan

- **No tag and no wrapper change:** `tools/` and `docs/propagation.md` are
  reference-only.
- **First user:** the next adoption, Codex from `sandbox-ref-28` to
  `sandbox-ref-36`.
- **Rollback:** revert the commit. Until then the old `report()` output is
  only extended, so existing dry-run reading keeps working.
