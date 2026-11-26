# Tasks

## 1. Checklist entries by component

- [x] 1.1 Make `checklist()` in `tools/propagate.py` return entries `(name, kind, command)`, and make `report()` print them (design decision 1).
  - **Kinds and names:** as in design decision 1, in its fixed order.
  - **Report:**
    - "Run in the target" lists the commands;
    - `unit` reads `SANDBOX_TEST_TMPDIR=<private directory> python3 -m unittest ...`;
    - the template has one row per entry;
    - a last line names `bash tools/adoption-run.sh <target> <old> <new>`.
  - **Tests:** `test_checklist_follows_the_changed_files_and_runner` and the dry-run assertions of `tests/test_propagate.py` follow the new output.
  - **Verify:** `python3 -m unittest tests.test_propagate` passes.
- [x] 1.2 Add the component mappings of design decision 2 to `checklist()`.
  - **New rules:**
    - `launcher/` core;
    - the engine inputs, with case detection and the `prepare engine` entry;
    - `SHARED_CODE`, read with `ast` from the new tag's `network/qualification_records.py`;
    - shared test modules and their mode table;
    - helper imports;
    - Windows manual steps;
    - image entries for the runtime image and the guard toolchain, named from the target's profile.
  - **Order and duplicates:** each entry once, and no `-k` selection beside its full mode.
  - **Tests:** one test per scenario of "Checklist commands by changed component", except the real-repository scenario, on the disposable repositories of `tests/test_propagate.py`.
  - **Verify:** `python3 -m unittest tests.test_propagate` passes, and each new test fails when its rule is removed.
- [x] 1.3 Add `--checklist` to `tools/propagate.py` (spec "Checklist of an adopted target").
  - **Target:** its manifest must name the new tag and its commit. A dirty tree is accepted, and nothing is written.
  - **Output:** one tab-separated `kind<TAB>name<TAB>command` line per entry, preparation, image and manual step.
  - **Tests:** the target before adoption is refused and prints no entry; a target with an uncommitted edit is accepted; the target is unchanged afterwards.
  - **Verify:** `python3 -m unittest tests.test_propagate` passes.
- [x] 1.4 Update `docs/propagation.md` for the new checklist.
  - **Step 1:**
    - the table of changed files and commands, with design decision 2's rows;
    - the `SHARED_CODE` rule as a row;
    - the reference's runs on WSL and on the native Linux host, in full.
  - **Step 2:** the dry run's "runner modes" item becomes the commands with their entry names.
  - **Verify:** the table matches `checklist()`, row by row; `git diff --check` passes.

## 2. Review warnings and reference changes

- [x] 2.1 Add the review warnings of design decision 4 to `plan()` and `report()`.
  - **Output:** `review: <path>:<line>` lines, in the dry and the applied run.
  - **Tests:**
    - an added file under a shared directory, with a target file naming its sibling: the line is listed;
    - a range without additions or removals: no warning;
    - the excluded paths (shared files, manifest, `docs/validation.md`, `CHANGELOG.md`, `openspec/`) are never listed;
    - the run still completes.
  - **Verify:** `python3 -m unittest tests.test_propagate` passes.
- [x] 2.2 Add the reference changes of design decision 5 to `plan()` and `report()`.
  - **Output:** a `reference changes:` block, one line per change, with its location, its delta capabilities and `[not in target]` marks.
  - **Tests:** a fixture reference whose range touches three changes:
    - one archived after the new tag;
    - one still active;
    - one with a capability the target lacks.
  - **Verify:** `python3 -m unittest tests.test_propagate` passes.
- [x] 2.3 Describe both outputs in step 2 of `docs/propagation.md`: what a review line asks the adopter to check, and how the adoption change takes its spec deltas from the listed changes.
  - **Verify:** a dry run on a fresh clone of `claude-container` at `339bddc` (its `sandbox-ref-35` state) prints:
    - `review: tests/test_network_runtime.py:90` and `review: tests/run-runtime.sh:10`;
    - the four reference changes of design decision 5.

    The clone sits in a new temporary directory, which is removed afterwards.

## 3. Adoption runner

- [x] 3.1 Write `tools/adoption-run.sh` (design decisions 3 and 6, spec `adoption-runner`).
  - **Header:** usage; the test-only variables `SANDBOX_ADOPTION_REFERENCE`, `SANDBOX_ADOPTION_HOST_PYTHON` and `SANDBOX_ADOPTION_MIN_FREE_KIB`.
  - **Order:**
    1. `--checklist`, refusing on its error;
    2. `--only` validation;
    3. the log directory;
    4. the preflight record and checks;
    5. the preparations;
    6. the entries, with logs, the summary, and tags around `setup-runtime`;
    7. the image list after the entries;
    8. the archive.
  - **Exit status:** as the spec "Full logs and a summary" says.
  - **Safety:** the private temporary directory is removed only when its path matches `$HOME/.sbx-test-*`.
  - **Verify:** `bash -n tools/adoption-run.sh` passes.
- [x] 3.2 Add `tests/test_adoption_run.py`, reference-only.
  - **Fixtures:**
    - a disposable reference and a target adopted at the new tag, built with the helpers of `tests/test_propagate.py`;
    - stub `podman` and `tests/run-runtime.sh` scripts on `PATH`;
    - a temporary `HOME`.
  - **Cases:**
    - every entry passes: exit 0, one log per entry, a summary line each, and an archive whose name holds the wrapper, the tag and the host;
    - a failing middle entry: the later ones still run, and the exit is nonzero;
    - a `prepare ...` skip: `NOT PREPARED` and a nonzero exit;
    - a missing image, and free space under the floor: no entry runs, but the summary and the archive are written;
    - an engine input in the range: the stub records the engine build before the first runtime entry;
    - `--only unit`: only `unit` runs, in a new directory;
    - an unknown `--only` name: refused before anything runs;
    - host Python older than 3.11: the stub records the in-image command;
    - after every run: the target's `git status --porcelain` is unchanged.
  - **Verify:** `python3 -m unittest tests.test_adoption_run` passes.
- [x] 3.3 Document the runner.
  - **`docs/propagation.md`, step 3:**
    - run the runner on the host where the wrapper is used, and copy the archive;
    - record every entry, and the entries not run with the reference's record as evidence;
    - for the wrapper's own changed files, run the mode or cases that exercise them;
    - rerun entries with `--only`.
  - **`AGENTS.md` and the README's propagation paragraph:** name the runner and `tests/test_adoption_run.py`.
  - **Verify:** `git diff --check` passes, and the documents name the same options as the script's usage text.

## 4. Validation

- [x] 4.1 Run the checks in this environment, then commit on the branch `speed-up-wrapper-adoptions`, without merging.
  - **Unit checks:** `python3 -m unittest tests.test_propagate tests.test_adoption_run tests.test_alignment`.
  - **Other checks:**
    - `openspec validate speed-up-wrapper-adoptions --strict`;
    - `git diff --check`.
  - **Real repositories, read-only:**
    - `python3 -I tools/propagate.py ../claude-container sandbox-ref-35 sandbox-ref-36 --checklist` prints exactly the entries of the spec scenario "Claude's adoption of sandbox-ref-36", plus the engine preparation and the two images;
    - a dry run against `../codex-container` from `sandbox-ref-28` to `sandbox-ref-36` succeeds. Its review lines and reference changes are recorded for the Codex adoption.
  - **Verify:** all pass.
- [ ] 4.2 Have the operator run the runner on both hosts, from the branch in `~/sandboxes/sandbox-container`, against `~/sandboxes/claude-container` on `main` (`sandbox-ref-36`).
  - **WSL:**
    - `bash tools/adoption-run.sh ../claude-container sandbox-ref-35 sandbox-ref-36`;
    - then `--only unit`;
    - then `bash tools/shellcheck.sh .`.
  - **Rocky 9 lab host:**
    - check the free space first;
    - run the same command with `--only unit,setup,qualification`.
  - **Expected:**
    - on WSL, every entry passes, the summary lists only the expected skips, and the rerun writes a new archive;
    - ShellCheck finds nothing;
    - on Rocky, `--checklist` runs on Python 3.9, `unit` runs in the runtime image and its engine-case skips are listed, and `setup` and `qualification` pass.
- [ ] 4.3 Record the change in `docs/validation.md`, with:
  - the results of 4.1 and 4.2;
  - the runner's run times;
  - the operator's steps compared with the manual run of 2026-11-26.

  Commit, then merge into `main`.
  - **Verify:** `python3 -m unittest tests.test_propagate tests.test_adoption_run` passes on `main`.

## Workflow follow-up

- The operator pushes `main` and the branch.
- Archive this change with spec sync: it creates `adoption-runner` and updates `reference-propagation`.
- First real use: Codex adopts `sandbox-ref-36` from `sandbox-ref-28` with the new dry run and the runner.
