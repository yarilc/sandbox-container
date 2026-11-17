# Design

## Context

`tests/test_alignment.py` scans the shared files with `violations(root, PROFILE.identifiers)`. In the reference, the profile's only identifier is `sandbox-container`.

## Decisions

1. **Neutral names that keep each test's intent.**
   - `OTHER_AGENT_YOLO` stands for another agent's approval variable. The shell profile must ignore it (help, missing-tool and composition cases).
   - `OTHER_AGENT_BASE_URL` stands for another agent's variable that a toolchain may set for the shell profile.
   - `agent-alias` is the symlink name.
2. **Sibling identifiers.** The siblings are `ROOT.parent/*/agent/profile.json`, excluding the checkout itself. Each is loaded with `agent_profile.load`, which fails on an invalid sibling profile instead of ignoring it. The union of their identifiers is scanned by the existing `violations()`, so the `ALLOWED` list applies to both checks. With no siblings the test is skipped, as `tests/test_reference_copy.py` does in the wrappers.

   In a wrapper, the same test also sees the reference and the other wrappers. That is intended: no shared file may name any agent.

   Alternative rejected: a hard-coded identifier list. It would have to be updated by hand for every new wrapper.

## Risks / Trade-offs

- [A sibling identifier also occurs as an ordinary word] → Today the scan finds exactly the seven lines this change fixes. A future false positive gets a reviewed `ALLOWED` entry.
