# Spec Delta

## MODIFIED Requirements

### Requirement: Workflow questionnaire with explicit defaults
Setup SHALL explain and collect network mode, state sharing, installation paths, host CA trust and workspace scope. It SHALL offer `provider` and ask for an authentication method only when the profile declares authentication methods, and ask about permission bypass only when the profile declares an approval-bypass variable. First-run defaults SHALL select provider networking with the first method when methods exist, otherwise `offline`, with shared state and disabled optional authority. Saved choices SHALL be offered on rerun. When no same-host launch service is available, the network choice SHALL follow the rule for setup without a launch service instead.

#### Scenario: First setup choices
- **WHEN** the user reviews first-run defaults with the reference profile, which declares no authentication method and no approval-bypass variable, on a host where a same-host launch service is reachable or can be started
- **THEN** network options are only offline and unrestricted, and offline is proposed
- **AND** no authentication, residual-exfiltration or permission-bypass question is asked
- **AND** shared host state, isolated fresh state and worktree-parent exposure are explained before selection

#### Scenario: Provider selected
- **WHEN** setup runs with a profile that declares authentication methods, as the shared tests do with the fixture profile, and a same-host launch service is reachable or can be started
- **THEN** network options also offer provider, the first-run default is provider with the first declared method, and choosing a method selects its protected policy profile without requiring an API key

#### Scenario: Previously saved network mode
- **WHEN** setup is rerun with a saved configuration, including explicit offline mode, and a same-host launch service is reachable or can be started
- **THEN** the saved network mode remains the proposed choice instead of the first-run default

## ADDED Requirements

### Requirement: Setup without a launch service offers only unrestricted networking
Before asking for the network mode, setup SHALL check, read-only, whether a same-host Unix launch service answers at `CONTAINER_HOST`, the saved endpoint or the default endpoint, and whether a usable systemd user manager could start one. When neither holds, setup SHALL offer only unrestricted networking, explain why, require explicit confirmation, and offer no delegation.

#### Scenario: Host without systemd user manager or service
- **WHEN** setup runs where no launch service answers and `systemctl --user` is missing or fails, as in a Podman machine distribution on WSL
- **THEN** setup states that offline and provider networking need a same-host service and that none is available or startable
- **AND** it asks for explicit confirmation of unrestricted networking, does not ask about delegation, and saves the local engine as the launch endpoint

#### Scenario: Local endpoint leaves CONTAINER_HOST unset
- **WHEN** the saved launch endpoint is the local engine
- **THEN** the smoke check and managed launches run Podman without `CONTAINER_HOST`, and the launcher treats an empty `CONTAINER_HOST` or `CONTAINER_CONNECTION` as unset, because Podman treats a set variable as a remote context even when it is empty

#### Scenario: Confirmation declined
- **WHEN** the user declines unrestricted networking in that situation
- **THEN** setup ends with status 1 without changes and explains how to make a service available: start a same-host Podman service, or set `CONTAINER_HOST` to its Unix endpoint, then rerun setup

#### Scenario: Saved restricted mode without a service
- **WHEN** setup is rerun with saved offline networking and no service is reachable or startable any longer
- **THEN** setup does not propose offline, states that the saved mode cannot be kept, and changes to unrestricted only after explicit confirmation

#### Scenario: Service reachable or startable
- **WHEN** a launch service answers at one of the checked endpoints, or a usable systemd user manager exists
- **THEN** setup offers every mode the profile allows, as before

#### Scenario: Explanation names no runtime directory
- **WHEN** setup explains how to make a service available
- **THEN** the explanation refers to the setup guide and names no socket path derived from `XDG_RUNTIME_DIR`

### Requirement: Installation inputs with carriage returns are refused
Before copying installation inputs into a new release, setup SHALL refuse any input file that contains a carriage return byte. The refusal SHALL name the file, explain that release files must have LF line endings, point to the repository's `.gitattributes` and the renormalization step, and leave the last working installation selected.

#### Scenario: CRLF checkout
- **WHEN** an installation input in the checkout contains CRLF line endings
- **THEN** setup stops with status 1 naming that file and the renormalization step, before creating the release

#### Scenario: LF checkout
- **WHEN** every installation input has LF line endings
- **THEN** setup copies the inputs as before
