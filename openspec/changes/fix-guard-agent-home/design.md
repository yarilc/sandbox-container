# Design

## Context

Since `sandbox-ref-19`, shared tests see the fixture profile as `PROFILE`, and tests that run the checkout's own image or wrapper use `REAL_PROFILE`, `REAL_ROOT` and `AGENT_COMMAND` from `tests/sandbox_profile.py`. `production_container` in `tests/test_guard.py` already runs `AGENT_IMAGE` (the real image) and `AGENT_COMMAND`, but still takes the home tmpfs path from `PROFILE`.

## Decisions

1. **Mount `AGENT_HOME`, the real profile's home, exposed by `tests/sandbox_profile.py`.** The mount mirrors what the wrapper's launcher gives its image, so it must follow the image, not the fixture. As with `AGENT_COMMAND`, `sandbox_profile.py` names the image's property, so `test_alignment.py` keeps rejecting direct `REAL_PROFILE` reads in shared tests. No other `PROFILE` attribute in `production_container` describes the image.
2. **No new runtime test in the reference.** In the reference the real profile is the shell profile and its command does not write to its home, so the defect is not observable here. The evidence is the OpenCode `--guard` run: it fails with the `sandbox-ref-20` file and passes with the corrected one, checked on a scratch copy of `opencode-container`.
3. **New tag `sandbox-ref-21`.** Shared files change only through a tag; the five wrappers adopt it after this change is merged.

## Risks / Trade-offs

- [The fix is not exercised by a failing reference test] → The OpenCode check in task 1.3 is the regression evidence and is recorded in `docs/validation.md`.
