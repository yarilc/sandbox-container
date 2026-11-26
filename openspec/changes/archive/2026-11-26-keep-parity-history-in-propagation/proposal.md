# Proposal

## Why

`tools/propagate.py --apply` replaces every mention of the old tag in a
wrapper's `docs/network-contract.md`. The spec already limits that rewrite to
the reference line and the reference and adoption cells, but the tool does not
follow it. In the parity table, the tool changes:
- history entries in the real enforcement cells, which name the tag each
  check ran at;
- the adoption cells of other wrappers that hold the same tag.

Claude's adoption of `sandbox-ref-35` showed the first case: three history
entries moved from `sandbox-ref-34` to `sandbox-ref-35`, and they were
restored by hand. A dry run against Codex from `sandbox-ref-28` to
`sandbox-ref-35` counts 11 references in the contract. Only 3 are current:
- the tag and the commit in the reference line;
- Codex's adoption cell.

The other 8 are:
- the history entries of five rows;
- the adoption cells of Antigravity, OpenCode and Pi, which would claim a
  tag those wrappers have not adopted.

Codex, Antigravity, OpenCode and Pi still have to adopt `sandbox-ref-35`, so
the tool must be fixed first.

## What Changes

- **The network contract rewrite follows the table.** In
  `docs/network-contract.md`, the tool:
  - replaces the old tag only where the reference line names it with its
    commit;
  - replaces the old commit wherever it appears;
  - in the parity table, replaces the old tag only in the contract adoption
    cell of two rows: the target's own row and the reference row.

  It finds the target's row by the `display_name` of the target's
  `agent/profile.json`, and the columns by the table's header. Real
  enforcement cells, other wrappers' rows and the other columns keep their
  text.
- **A missing row is refused.** If the contract has a parity table without a
  row for the target, or the target's profile has no `display_name`, the tool
  refuses before writing and names the problem.
- **The dry run shows what stays.** For the contract, it reports the
  references it will replace and the mentions of the old tag it keeps.
- **Matching documentation.** `docs/propagation.md` describes the cells the
  tool moves, by column instead of by the old wording `Ported from`. The
  parity requirement describes the table as it is today:
  - the reference row's contract adoption cell is `Reference (...)`;
  - each wrapper's cell is `Adopted sandbox-ref-N: ...`;
  - real enforcement cells name the tag each result ran at.
- `tests/test_propagate.py` covers these cases.
- The other current-state documents keep today's rule: `README.md`,
  `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reference-propagation`:
  - "Current-state references only" points to the new "Network contract
    references", which defines the network contract rewrite by the reference
    line and the table's cells, with the report of kept mentions;
  - the new "Unreadable parity table is refused" adds the refusal;
  - "Parity table names the reference" describes the cells as the tables
    have them, and says that real enforcement entries keep their tags.

## Impact

- **Code:** `tools/propagate.py` and `tests/test_propagate.py`. Both are
  reference-only and are never copied to wrappers. No shared file changes, so
  no new `sandbox-ref-N` tag is needed, and no wrapper has to adopt anything.
- **Documentation:** `docs/propagation.md`, and the record in
  `docs/validation.md`.
- **Wrappers:** none changes. The next adoptions use the fixed tool:
  Codex, Antigravity, OpenCode and Pi to `sandbox-ref-35`. Each target's
  `agent/profile.json` already has the `display_name` its row uses: Claude,
  Codex, Antigravity, OpenCode and Pi.
- **Validation:** runs here, without an engine:
  - `tests/test_propagate.py`;
  - a dry run against each wrapper;
  - an applied run on disposable clones of Codex and Claude, compared with
    the expected diff.
