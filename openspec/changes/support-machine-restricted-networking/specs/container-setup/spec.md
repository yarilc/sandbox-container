# Spec Delta

## ADDED Requirements

### Requirement: Restricted modes propose a service endpoint
When the selected workflow needs a same-host Unix service and the saved launch endpoint is the local engine, setup SHALL propose `default` as the launch endpoint instead of the saved value.

#### Scenario: From unrestricted to offline
- **WHEN** a rerun moves an installation that saved unrestricted networking and the local endpoint to offline networking, and the user accepts the proposed endpoint
- **THEN** setup saves the `default` endpoint without refusing the answer first

#### Scenario: Unrestricted rerun
- **WHEN** a rerun keeps unrestricted networking without delegation
- **THEN** setup still proposes the saved local endpoint
