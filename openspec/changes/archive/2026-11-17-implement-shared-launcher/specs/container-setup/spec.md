# Spec Delta

## ADDED Requirements

### Requirement: Runtime build receives host CA trust
Setup SHALL build every runtime image through the wrapper's build-only operation. When host CA trust is enabled, setup SHALL give that operation the trust selection and the selected bundle, and the wrapper SHALL pass the bundle to its build only as a non-persisted build secret. Without host CA trust, the build SHALL receive no host CA.

#### Scenario: Runtime build with host CA trust
- **WHEN** setup prepares the runtime image with host CA trust enabled
- **THEN** the wrapper's build receives the selected bundle as the `build-ca` build secret
- **AND** the built image contains neither the bundle nor its temporary copy

#### Scenario: Runtime build without host CA trust
- **WHEN** setup prepares the runtime image with host CA trust disabled
- **THEN** the wrapper's build receives no build secret and no host CA bundle

## REMOVED Requirements

### Requirement: Wrapper-built runtime receives host CA trust
**Reason**: Every profile now builds its runtime image through the wrapper; the distinction between wrapper-built and recipe-built runtimes is gone.
**Migration**: Replaced by "Runtime build receives host CA trust".

## MODIFIED Requirements

### Requirement: Mode-specific image and guard preparation
Setup SHALL inspect or prepare the runtime image and the additional components required by the selected mode. The runtime image SHALL be built through the wrapper's build-only operation, for every profile. Restricted modes SHALL receive a validated static guard and digest manifest; provider mode, available only for profiles with authentication methods, SHALL also receive a valid selected policy, private runtime directory and immutable proxy image identity. Existing suitable artifacts SHALL be reused unless refresh is approved.

#### Scenario: Fresh provider setup
- **WHEN** provider setup is approved with no prepared artifacts for a profile with authentication methods
- **THEN** setup prepares the pinned build inputs, toolchain, runtime and proxy images, compiles the guard and validates its manifest and policy
- **AND** launch preferences refer to an inspected immutable proxy image rather than an unresolved local tag

#### Scenario: Offline or unrestricted setup
- **WHEN** setup prepares offline mode, as the reference does by default
- **THEN** it prepares the runtime and guard without requiring a provider proxy image or authentication
- **AND** unrestricted setup requires neither the restricted guard nor provider proxy components

#### Scenario: Preparation fails
- **WHEN** an image build, image inspection, guard compilation or validation fails
- **THEN** setup reports the failed stage and leaves the last working installation selected
- **AND** it does not substitute a different policy, toolchain or network mode

### Requirement: Protected complete installation
Setup SHALL prepare all files needed for the selected workflow in a native installation outside writable workspace, worktree-parent and state trees, including the shared launcher core and the agent launcher part. It SHALL validate ownership, ancestor permissions and overlaps, create missing private directories, and refuse unsafe existing paths without recursive permission repair, credential imports, relabeling or added privileges. Managed launches SHALL verify the entry script, the launcher core and the agent launcher part as protected files. Setup and its smoke checks SHALL ignore host values of `SANDBOX_CONTAINER_ENV_VARS` and `SANDBOX_CONTAINER_READONLY_STATE`.

#### Scenario: Checkout on a Windows mount
- **WHEN** setup runs from a checkout on a permission-emulating Windows filesystem and the user selects a valid native installation
- **THEN** it copies the required installation inputs to native storage and validates them there
- **AND** it does not require executing a compiled guard on the source mount

#### Scenario: Unsafe installation or state path
- **WHEN** a chosen path has unsafe ancestors, cannot enforce private permissions or overlaps an application-writable mount
- **THEN** setup identifies the path and fails without modifying existing permissions or claiming completion

#### Scenario: Installed launcher core
- **WHEN** setup completes an installation
- **THEN** the release contains `launcher/core.sh` and `agent/launcher.sh` as protected files, and a managed launch refuses a release where either is writable by others
