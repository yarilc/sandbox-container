# Tasks

## 1. The network contract rewrite in `tools/propagate.py`

- [x] 1.1 Commit this change directory on `main`, then create the branch `keep-parity-history-in-propagation`. Verify: `openspec validate keep-parity-history-in-propagation --strict` passes and `git status` is clean on the new branch.
- [x] 1.2 Read the target's parity row in the plan, and refuse where it cannot be found (design decisions 1, 2 and 4).
  - **Profile:** read `display_name` from the target's `agent/profile.json` as JSON.
  - **Table:** find the header whose first two cells are `Wrapper` and `Contract adoption`, then the target's row and the row whose label ends in ` (reference)`.
  - **Refusals:** each raises a `PropagationError` before any write:
    - a missing or unreadable profile, or one without `display_name`;
    - no row with that label, or more than one;
    - a row whose cell count differs from the header's.

  A contract without a parity table is not refused.

  Verify with new `tests/test_propagate.py` cases on the fixture repositories:
  - each refusal exits nonzero naming its problem, and the target's snapshot is unchanged;
  - a contract without a parity table still adopts.
- [x] 1.3 Replace only the current references in `docs/network-contract.md` (design decisions 2 and 3).
  - **Parity table:** the old tag is replaced only in the contract adoption cell of the target's row and of the reference row.
  - **Outside the table:** the old tag is replaced only in `` `<old tag>` (commit `<old commit>`) ``.
  - **Old commit:** replaced anywhere in the contract.
  - **Other documents:** `README.md`, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md` keep today's whole-word rule.

  Verify:
  - The fixture contract in `tests/test_propagate.py` has the real header and three rows: the reference, the target `Pi` and another wrapper. Two of its real enforcement cells and the other wrapper's adoption cell name the old tag, and a prose line names it without its commit.
  - After `--apply`:
    - the target's and the reference's adoption cells and the reference line name the new tag and commit;
    - every other mention is byte-identical;
    - `test_apply_copies_rewrites_and_keeps_history` passes with the updated assertions.
- [x] 1.4 Report the kept mentions (design decision 5). For the network contract, the dry run and the applied run print the references to replace and the old-tag mentions kept, as `docs/network-contract.md (<replaced>, <kept> kept)`. Other documents keep `<name> (<count>)`. Verify: `test_dry_run_plans_without_writing` asserts the new documents line for the fixture contract. `test_same_tag_reports_no_changes` still passes.
- [x] 1.5 Update `docs/propagation.md`:
  - step 1, the paragraph after the tag command: the tool moves a wrapper's own contract adoption cell and the reference row's cell;
  - step 2, the list of current-state documents: the reference line with its commit, and the two cells by column. Real enforcement cells and other wrappers' rows keep their tags. The new refusal is listed with the others;
  - step 4: which cells the tool moved, and which ones the operator copies.

  Verify:
  - `grep -n 'Ported from' docs/propagation.md` finds nothing;
  - the dry-run list names the kept mentions;
  - `python3 -m unittest tests.test_propagate` passes.

## 2. Runs against the real wrappers

- [x] 2.1 Dry-run `python3 -I tools/propagate.py ../<wrapper> sandbox-ref-28 sandbox-ref-35` against `codex-container`, `antigravity-container`, `opencode-container` and `pi-container`. Verify:
  - each prints `docs/network-contract.md (3, 8 kept)`: the tag and the commit of the reference line and the wrapper's adoption cell, and the 8 history and other-wrapper mentions;
  - `git status --short` is empty in each wrapper afterwards.
- [x] 2.2 Apply the same adoption to a disposable clone of `codex-container` in a new temporary directory. Verify:
  - `git diff` of `docs/network-contract.md` changes exactly the reference line and the Codex row's contract adoption cell;
  - the README, `AGENTS.md` and `docs/setup.md` name `sandbox-ref-35`;
  - `grep -o 'sandbox-ref-28' docs/network-contract.md | wc -l` still counts the 8 kept mentions.
- [x] 2.3 Apply `sandbox-ref-34` to `sandbox-ref-35` to a disposable clone of `claude-container`, checked out at its pre-adoption commit `ae6af89`. Verify:
  - `git diff` of `docs/network-contract.md` changes only the reference row's and Claude's contract adoption cells;
  - the three real enforcement entries that `adopt-sandbox-ref-35` restored by hand still name `sandbox-ref-34`.

## 3. Checks, record and merge

- [x] 3.1 Run the checks:
  - `python3 -m unittest tests.test_propagate tests.test_alignment`;
  - `openspec validate keep-parity-history-in-propagation --strict`;
  - `git diff --check`.

  No shared, runtime or setup file changes, so no runner mode is required.

  Verify: all pass. The full unit discovery is not required for this change; record why.
- [ ] 3.2 Record the change in `docs/validation.md` with the results of tasks 1 to 3.1, as a new section at the top. Commit with the co-author trailer, then merge into `main` without a tag. Verify:
  - the section names the Codex and Claude clone diffs;
  - `git log --oneline -1 main` is the merge;
  - `python3 -m unittest tests.test_propagate` passes on `main`.

## Workflow follow-up

- The operator pushes `main`.
- Archive this change with spec sync. This updates "Current-state references only" and "Parity table names the reference" in `reference-propagation`.
- Codex, Antigravity, OpenCode and Pi then adopt `sandbox-ref-35` with the fixed tool.
