# Design

## Context

`tools/propagate.py` handles each current-state document the same way. In the
plan, it counts the whole-word mentions of the old tag and of the old commit.
With `--apply`, it replaces all of them. For `docs/network-contract.md`, this
replaces text that the spec keeps (proposal.md, Why).

Today's contracts:
- **The parity table** has the header
  `| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |`
  in all six repositories. Each of its six rows has five cells. The row
  labels are `Sandbox (reference)`, `Claude`, `Codex`, `Antigravity`,
  `OpenCode` and `Pi`.
- **Each wrapper's `agent/profile.json`** has a `display_name` equal to its
  row label.
- **The reference line:** the contracts of Codex, Antigravity, OpenCode and
  Pi say that the shared components come from `sandbox-container` at
  `` `sandbox-ref-28` (commit `ba1ef14…`) ``. The tag and the commit are on
  the same line. Claude's and the reference's contracts have no such line.
- **Historical prose:** the OpenCode and Pi contracts name earlier tags in
  prose, for example "`sandbox-ref-5` is `sandbox-ref-2` plus three
  shared-test fixes".
- **The other current-state documents** (`README.md`, `AGENTS.md`,
  `CONTRIBUTING.md`, `docs/setup.md`) mention `sandbox-ref-28` only as the
  wrapper's current copy.

The tool and its test are reference-only (proposal.md, Impact).

## Goals / Non-Goals

**Goals:**
- An applied run changes, in the network contract, exactly what the modified
  "Current-state references only" requirement lists. The dry run shows what it
  keeps.
- The tool still never runs code from the target, and names no agent.

**Non-Goals:**
- **Rows of other wrappers.** The tool does not copy or rebuild any of
  them. Step 4 of `docs/propagation.md` still copies the reference row from
  `sandbox-container`, and the adopted wrapper's row into the other
  repositories.
- **History in other documents.** The tool does not detect history in the
  README, `AGENTS.md`, `CONTRIBUTING.md` or `docs/setup.md`. Their mentions
  of the tags still to be adopted are current (Context).
- **Wrapper-side changes.** No wrapper changes, and no new tag.

## Decisions

1. **The target's row is found by its profile's `display_name`.**
   - **How:** the tool reads the target's `agent/profile.json` as JSON. It
     imports no code from the target, as it already does for the manifest.
   - **Reference row:** the row whose label ends in ` (reference)`.
   - **Alternatives rejected:**
     - A table from directory name to row label: it would name the agents
       in the reference tool.
     - The row whose adoption cell names the old tag: it is ambiguous when
       several wrappers hold the same tag. Today four wrappers hold
       `sandbox-ref-28`.

2. **Cells are found by the table's header.**
   - **The table:** the line whose first two cells are `Wrapper` and
     `Contract adoption`. The column is located from that header.
   - **The rows:** the table's body runs to the first line that does not
     start with `|`.
   - **Cells:** a row is split on its ` | ` separators. If a row's cell
     count differs from the header's, the tool refuses: it cannot tell the
     cells apart.
   - **Replacement:** only the old tag, inside that one cell.
   - **Alternative rejected:** matching the wording `Adopted …` or
     `Ported from …`. The wording has already changed once, and the spec
     wording lagged behind.

3. **Outside the table, the old tag moves only next to its commit.**
   - **The pair:** `` `<old tag>` (commit `<old commit>`) `` becomes
     `` `<new tag>` (commit `<new commit>`) ``.
   - **The old commit alone** moves anywhere else in the contract. A full
     commit hash names only the current copy.
   - **Alternative rejected:** replacing every mention outside the table.
     OpenCode's and Pi's prose lists earlier tags as history (Context),
     which would break when one of those tags is the old tag.

4. **Refusals happen in the plan, before any write.**
   - **When it refuses:** the contract has a parity table, and either:
     - the target's profile is missing, unreadable or has no
       `display_name`;
     - the table has no row, or more than one, with that label;
     - a row has the wrong number of cells.
   - **Without a parity table**, only decision 3 applies.
   - **How:** the refusal is a `PropagationError` with its own message, as
     for the other preconditions, so the dry run refuses as well.

5. **The report names the kept mentions.**
   - **The documents line:** for the contract, `docs/network-contract.md
     (3, 8 kept)`. The other documents keep `README.md (1)`.
   - **The validation-record template:** unchanged.
   - **Why:** the operator sees in the dry run that history stays, instead
     of finding it after the apply.

6. **Validation uses the real contracts without touching the wrappers.**
   - **Unit tests:** `tests/test_propagate.py` gets a contract with the real
     header and rows (decisions 1 to 5), and a fixture `agent/profile.json`.
   - **Dry runs** against Codex, Antigravity, OpenCode and Pi, each from
     `sandbox-ref-28` to `sandbox-ref-35`, on the real checkouts. A dry run
     writes nothing.
   - **Applied runs on disposable clones**, compared line by line:
     - **Codex:** the reference line and Codex's adoption cell change, and
       the eight other mentions stay.
     - **Claude:** a clone at its pre-adoption commit `ae6af89`, from
       `sandbox-ref-34` to `sandbox-ref-35`. The reference and Claude
       adoption cells change, and the three history entries stay: the case
       restored by hand in `adopt-sandbox-ref-35`.

## Risks / Trade-offs

- **[Risk] A row label and a `display_name` drift apart.** → The tool
  refuses and names the label it looked for. All six match today (Context).
- **[Risk] A future cell contains ` | `.** → The cell count no longer
  matches the header, and the tool refuses instead of editing the wrong
  cell.
- **[Trade-off] The reference row's other cells are not refreshed.** → Step 4
  of the procedure already copies the reference row from
  `sandbox-container`, and the dry run reports the cells the tool moves.
- **[Trade-off] An adoption's own history needs a hand edit.** A wrapper's
  real enforcement cell gets no new-tag entry from the tool. → As today,
  adoption task 4 sets that cell from the validation results.

## Migration Plan

None. The tool runs only from this checkout, and the next adoption uses it.
Rollback is a revert of the change's commits.
