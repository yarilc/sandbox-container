# Launcher test map

Every `tests/test_wrapper.py` case of the six repositories on `sandbox-ref-21`,
mapped to a phase of `docs/launcher-contract.md` and to its destination when
the wrapper adopts the shared core:

- **shared** - becomes a shared launcher test (first occurrence, reference order S, C, X, A, O, P);
- **shared (rewrite)** - becomes a shared test, rewritten for the decision named in the note;
- **shared (duplicate)** - same behavior as an earlier shared test; merged into it, not kept;
- **hook** - tests an agent hook or agent data; stays in the wrapper;
- **obsolete** - behavior removed by a contract decision (U2, U4, phase 6);
- **fake engine** - tests the fake engine or the test harness; moves with the shared fake.

The classification is by test name and behavior. Duplicates are detected only
between tests with the same name; family B tests with other names (for example
`test_attached_signals_both_modes` and `test_term_forwarding`) often cover the
same behavior and are merged when the change that implements the core moves them.
The shared case `test_agent_profile_defaults_to_provider_and_needs_setup` covers U1.

The "Shared case" column names the shared case in `tests/test_launcher.py` that covers each
"shared" and "shared (rewrite)" case. Cases from the agent wrappers marked "to verify at
adoption" are matched by name only: each adoption runs its old `tests/test_wrapper.py`
against the new core, and every lost behavior becomes a shared case through the reference.

| Repository | Test | Phase | Destination | Note | Shared case |
| --- | --- | --- | --- | --- | --- |
| S | `test_help_without_podman_or_side_effects` | 1-2 | shared |  | `test_help_without_podman_or_side_effects` |
| S | `test_missing_mode_defaults_to_offline_and_needs_an_installation` | 1-2 | shared |  | `test_missing_mode_defaults_to_offline_and_needs_an_installation` |
| S | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` | 1-2 | shared |  | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` |
| S | `test_setup_diagnostic_quotes_invoked_symlink_and_runs_from_other_workspace` | 6 | shared |  | `test_setup_diagnostic_quotes_invoked_symlink_and_runs_from_other_workspace` |
| S | `test_network_preflight_rejections_precede_image_operations` | 5 | shared |  | `test_network_preflight_rejections_precede_image_operations` |
| S | `test_maintenance_is_separate_from_runtime_mode` | 5 | shared |  | `test_maintenance_is_separate_from_runtime_mode` |
| S | `test_restricted_unprotected_installation_fails_before_image_operations` | 7 | shared |  | `test_restricted_unprotected_installation_fails_before_image_operations` |
| S | `test_argument_forwarding_and_defaults` | 6 | shared |  | `test_argument_forwarding_and_defaults` |
| S | `test_delegation_only_follows_the_exact_opt_in` | 3-4 | shared |  | `test_delegation_only_follows_the_exact_opt_in` |
| S | `test_boolean_forms_and_invalid_values` | 1-2 | shared |  | `test_boolean_forms_and_invalid_values` |
| S | `test_shell_option_is_equivalent` | 1-2 | shared |  | `test_shell_option_is_equivalent` |
| S | `test_workspace_worktree_and_symlink` | 3-4 | shared |  | `test_workspace_worktree_and_symlink` |
| S | `test_read_only_identity_and_no_extra_host_mounts` | 5 | shared |  | `test_read_only_identity_and_no_extra_host_mounts` |
| S | `test_toolchain_command_dispatch` | 5 | shared |  | `test_toolchain_command_dispatch` |
| S | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared |  | `test_toolchain_library_created_private_and_mounted_read_only` |
| S | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared |  | `test_unsafe_toolchain_library_stops_before_engine_operations` |
| S | `test_toolchain_mount_can_be_disabled` | 5 | shared |  | `test_toolchain_mount_can_be_disabled` |
| S | `test_default_toolchain_environment_is_appended` | 5 | shared |  | `test_default_toolchain_environment_is_appended` |
| S | `test_toolchain_variables_and_protected_session_variables` | 5 | shared |  | `test_toolchain_variables_and_protected_session_variables` |
| S | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared |  | `test_restricted_sessions_declare_the_toolchain_mount` |
| S | `test_hardening_and_budgets_in_every_mode` | 5 | shared |  | `test_hardening_and_budgets_in_every_mode` |
| S | `test_budget_overrides_and_rejections_precede_engine` | 3-4 | shared |  | `test_budget_overrides_and_rejections_precede_engine` |
| S | `test_budget_rules_match_shared_python_module` | 1-2 | shared |  | `test_budget_rules_match_shared_python_module` |
| S | `test_budgets_follow_delegated_controllers` | 3-4 | shared |  | `test_budgets_follow_delegated_controllers` |
| S | `test_engine_default_secrets_are_masked_in_every_mode` | 5 | shared |  | `test_engine_default_secrets_are_masked_in_every_mode` |
| S | `test_agent_dev_layout_attaches_terminals_in_every_mode` | 6 | shared |  | `test_agent_dev_layout_attaches_terminals_in_every_mode` |
| S | `test_ignored_budgets_stop_before_start_and_remove_owned_container` | 6 | shared |  | `test_ignored_budgets_stop_before_start_and_remove_owned_container` |
| S | `test_lifetime_notice_preserves_status` | 6 | shared |  | `test_lifetime_notice_preserves_status` |
| S | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared |  | `test_sensitive_workspaces_refused_before_engine` |
| S | `test_wsl_drive_roots_refused_but_subdirectories_accepted` | 3-4 | shared |  | `test_wsl_drive_roots_refused_but_subdirectories_accepted` |
| S | `test_insecure_existing_state_rejected` | 3-4 | shared |  | `test_insecure_existing_state_rejected` |
| S | `test_tty_allocated_for_terminal` | 6 | shared |  | `test_tty_allocated_for_terminal` |
| S | `test_socket_only_required_when_enabled` | 3-4 | shared |  | `test_socket_only_required_when_enabled` |
| S | `test_socket_engine_must_be_rootless` | 3-4 | shared |  | `test_socket_engine_must_be_rootless` |
| S | `test_rootful_and_remote_rejected_local_unix_accepted` | 3-4 | shared |  | `test_rootful_and_remote_rejected_local_unix_accepted` |
| S | `test_build_location_refresh_and_missing_image` | 5 | shared (rewrite) | decision U3, U8 | `test_build_location_refresh_and_missing_image` |
| S | `test_runtime_build_receives_host_ca_only_when_trusted` | 5 | shared |  | `test_runtime_build_receives_host_ca_only_when_trusted` |
| S | `test_build_and_image_inspection_errors` | 5 | shared |  | `test_build_and_image_inspection_errors` |
| S | `test_exit_status_and_owned_cleanup` | 7 | shared |  | `test_exit_status_and_owned_cleanup` |
| S | `test_successful_restart_check_is_informational_and_real_errors_remain` | 6 | shared |  | `test_successful_restart_check_is_informational_and_real_errors_remain` |
| S | `test_cleanup_failure_or_stall_preserves_application_status` | 7 | shared |  | `test_cleanup_failure_or_stall_preserves_application_status` |
| S | `test_ignored_signals_force_owned_removal` | 7 | shared |  | `test_ignored_signals_force_owned_removal` |
| S | `test_stalled_controls_and_repeated_signal_are_bounded` | 7 | shared |  | `test_stalled_controls_and_repeated_signal_are_bounded` |
| S | `test_interrupted_creation_recovers_only_owned_identity` | 7 | shared |  | `test_interrupted_creation_recovers_only_owned_identity` |
| S | `test_interrupted_creation_rejects_foreign_recovery_result` | 7 | shared |  | `test_interrupted_creation_rejects_foreign_recovery_result` |
| S | `test_interrupted_creation_recovery_calls_are_bounded` | 7 | shared |  | `test_interrupted_creation_recovery_calls_are_bounded` |
| S | `test_collision_reconciliation_can_be_interrupted` | 7 | shared |  | `test_collision_reconciliation_can_be_interrupted` |
| S | `test_failed_create_after_id_publication_is_cleaned` | 6 | shared |  | `test_failed_create_after_id_publication_is_cleaned` |
| S | `test_failed_signal_delivery_still_removes_owned_container` | 7 | shared |  | `test_failed_signal_delivery_still_removes_owned_container` |
| S | `test_timeout_prerequisite_and_independent_help` | 3-4 | shared |  | `test_timeout_prerequisite_and_independent_help` |
| S | `test_healthy_build_and_session_outlive_shutdown_budget` | 7 | shared |  | `test_healthy_build_and_session_outlive_shutdown_budget` |
| S | `test_existing_names_and_collision_retry` | 6 | shared |  | `test_existing_names_and_collision_retry` |
| S | `test_create_failure_preserved_without_cleanup_of_other_containers` | 7 | shared |  | `test_create_failure_preserved_without_cleanup_of_other_containers` |
| S | `test_term_forwarding` | 7 | shared |  | `test_term_forwarding` |
| S | `test_launch_verification_fails_before_image_operations` | 5 | shared |  | `test_launch_verification_fails_before_image_operations` |
| S | `test_verification_preserves_exact_record_boundaries_and_status` | 6 | shared (rewrite) | decision U16, U17 | `test_verification_preserves_exact_record_boundaries_and_status` |
| S | `test_delegated_response_rejects_carriage_returns_before_image_operations` | 5 | shared |  | `test_delegated_response_rejects_carriage_returns_before_image_operations` |
| S | `test_response_validation_composes_with_launch_modes` | 3-4 | shared |  | `test_response_validation_composes_with_launch_modes` |
| S | `test_delegated_cr_response_preserves_query_failure_and_disabled_access` | 3-4 | shared |  | `test_delegated_cr_response_preserves_query_failure_and_disabled_access` |
| S | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` | 3-4 | shared |  | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` |
| S | `test_help_with_pathless_launch_endpoint` | 3-4 | shared |  | `test_help_with_pathless_launch_endpoint` |
| S | `test_shared_state_default_and_override` | 3-4 | shared |  | `test_shared_state_default_and_override` |
| S | `test_state_conflict_fails_without_engine` | 3-4 | shared |  | `test_state_conflict_fails_without_engine` |
| S | `test_state_overlapping_the_workspace_fails_without_engine` | 3-4 | shared |  | `test_state_overlapping_the_workspace_fails_without_engine` |
| S | `test_private_creation_does_not_change_host_command_umask` | 6 | shared |  | `test_private_creation_does_not_change_host_command_umask` |
| S | `test_shell_state_and_history_location` | 3-4 | shared |  | `test_shell_state_and_history_location` |
| S | `test_state_alias_and_configuration_escape` | 3-4 | shared |  | `test_state_alias_and_configuration_escape` |
| S | `test_private_existing_configuration_and_wrong_owner` | 3-4 | shared |  | `test_private_existing_configuration_and_wrong_owner` |
| S | `test_inaccessible_state_and_ignored_permissions` | 3-4 | shared |  | `test_inaccessible_state_and_ignored_permissions` |
| S | `test_socket_disabled_values_skip_delegation_checks` | 3-4 | shared |  | `test_socket_disabled_values_skip_delegation_checks` |
| S | `test_socket_precedence_and_remapping` | 3-4 | shared |  | `test_socket_precedence_and_remapping` |
| S | `test_podman5_unix_url_host_socket_is_bound_as_path` | 3-4 | shared |  | `test_podman5_unix_url_host_socket_is_bound_as_path` |
| S | `test_socket_fallback_and_invalid_sources` | 3-4 | shared (rewrite) | decision U16 | `test_socket_fallback_and_invalid_sources` |
| S | `test_invalid_delegation_results_gate_explicit_build` | 5 | shared (rewrite) | decision U16 | `test_invalid_delegation_results_gate_explicit_build` |
| S | `test_composition_and_independence_in_both_state_modes` | 3-4 | shared (rewrite) | decision U7 | `test_composition_and_independence_in_both_state_modes` |
| S | `test_disabled_delegation_preserves_host_launch_endpoint` | 3-4 | shared (rewrite) | decision U16, U17 | `test_disabled_delegation_preserves_host_launch_endpoint` |
| S | `test_ca_mount_and_security_policy` | 5 | shared (rewrite) | decision U7 | `test_ca_mount_and_security_policy` |
| S | `test_symlink_invocation_and_native_permissions` | 3-4 | shared |  | `test_symlink_invocation_and_native_permissions` |
| S | `test_collision_exhaustion_and_diagnostic_cleanup` | 7 | shared |  | `test_collision_exhaustion_and_diagnostic_cleanup` |
| S | `test_int_and_hup_forwarding` | 7 | shared |  | `test_int_and_hup_forwarding` |
| C | `test_shipped_inventories_are_exact` | 1-2 | hook |  | - |
| C | `test_removed_account_hosts_require_a_separate_profile` | 1-2 | hook |  | - |
| C | `test_help_without_podman_or_side_effects` | 1-2 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_missing_network_mode_requires_setup_without_side_effects` | 1-2 | shared (rewrite) | decision U1 | `test_help_without_podman_or_side_effects` (to verify at adoption) |
| C | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` | 1-2 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_setup_diagnostic_quotes_invoked_symlink_and_runs_from_other_workspace` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_network_preflight_rejections_precede_image_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_maintenance_is_separate_from_runtime_mode` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_restricted_unprotected_installation_fails_before_image_operations` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_argument_forwarding_and_defaults` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_four_independent_permission_combinations` | 1-2 | hook |  | - |
| C | `test_boolean_forms_and_invalid_values` | 1-2 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_shell_does_not_receive_yolo_or_cli_arguments` | 1-2 | shared (rewrite) | decision U14 | `test_shell_mode_skips_the_agent_arguments_and_bypass` (to verify at adoption) |
| C | `test_workspace_worktree_and_symlink` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_read_only_identity_and_no_extra_host_mounts` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_toolchain_cannot_set_claude_variables` | 5 | shared |  | `test_toolchain_variables_and_protected_session_variables` (to verify at adoption) |
| C | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_hardening_and_budgets_in_every_mode` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_budget_overrides_and_rejections_precede_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_budget_rules_match_shared_python_module` | 1-2 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_engine_default_secrets_are_masked_in_every_mode` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_agent_dev_layout_attaches_terminals_in_every_mode` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_ignored_budgets_stop_before_start_and_remove_owned_container` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_lifetime_notice_preserves_status` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_wsl_drive_roots_refused_but_subdirectories_accepted` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_proxy_hardening_failure_never_starts_agent` | 5 | shared |  | to verify at adoption |
| C | `test_proxy_probe_timeout_and_interruption_clean_only_proxy` | 7 | shared |  | to verify at adoption |
| C | `test_insecure_existing_state_rejected` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_tty_allocated_for_terminal` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_socket_only_required_when_enabled` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_socket_engine_must_be_rootless` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_rootful_and_remote_rejected_local_unix_accepted` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_build_location_refresh_and_missing_image` | 5 | shared (rewrite) | decision U3, U8 | `test_build_location_refresh_and_missing_image` |
| C | `test_runtime_build_receives_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_build_and_image_inspection_errors` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_exit_status_and_owned_cleanup` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_successful_restart_check_is_informational_and_real_errors_remain` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_cleanup_failure_or_stall_preserves_application_status` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_ignored_signals_force_owned_removal` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_stalled_controls_and_repeated_signal_are_bounded` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_interrupted_creation_recovers_only_owned_identity` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_interrupted_creation_rejects_foreign_recovery_result` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_interrupted_creation_recovery_calls_are_bounded` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_collision_reconciliation_can_be_interrupted` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_failed_create_after_id_publication_is_cleaned` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_failed_signal_delivery_still_removes_owned_container` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_timeout_prerequisite_and_independent_help` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_healthy_build_and_session_outlive_shutdown_budget` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_existing_names_and_collision_retry` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_create_failure_preserved_without_cleanup_of_other_containers` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_term_forwarding` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_launch_verification_fails_before_image_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_verification_preserves_exact_record_boundaries_and_status` | 6 | shared (rewrite) | decision U16, U17 | `test_verification_preserves_exact_record_boundaries_and_status` |
| C | `test_delegated_response_rejects_carriage_returns_before_image_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_response_validation_composes_with_launch_modes` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_delegated_cr_response_preserves_query_failure_and_disabled_access` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_help_with_pathless_launch_endpoint` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_shared_state_default_and_override` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_state_conflict_fails_without_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_state_overlapping_the_workspace_fails_without_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_private_creation_does_not_change_host_command_umask` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_state_alias_and_configuration_escape` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_private_existing_claude_and_wrong_owner` | 3-4 | shared |  | `test_private_existing_configuration_and_wrong_owner` (to verify at adoption) |
| C | `test_inaccessible_state_and_ignored_permissions` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_socket_disabled_values_skip_delegation_checks` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_socket_precedence_and_remapping` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_podman5_unix_url_host_socket_is_bound_as_path` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_socket_fallback_and_invalid_sources` | 3-4 | shared (rewrite) | decision U16 | `test_socket_fallback_and_invalid_sources` |
| C | `test_invalid_delegation_results_gate_explicit_build` | 5 | shared (rewrite) | decision U16 | `test_invalid_delegation_results_gate_explicit_build` |
| C | `test_composition_and_independence_in_both_state_modes` | 3-4 | shared (rewrite) | decision U7 | `test_composition_and_independence_in_both_state_modes` |
| C | `test_disabled_delegation_preserves_host_launch_endpoint` | 3-4 | shared (rewrite) | decision U16, U17 | `test_disabled_delegation_preserves_host_launch_endpoint` |
| C | `test_ca_mount_and_security_policy` | 5 | shared (rewrite) | decision U7 | `test_ca_mount_and_security_policy` |
| C | `test_symlink_invocation_and_native_permissions` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_collision_exhaustion_and_diagnostic_cleanup` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| C | `test_int_and_hup_forwarding` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_help_without_engine_or_state` | 3-4 | shared |  | `test_state_paths_are_checked_before_the_engine` (to verify at adoption) |
| X | `test_help_without_podman_installed` | 7 | shared |  | `test_help_without_podman_or_side_effects` (to verify at adoption) |
| X | `test_valid_launch_engine_without_delegation` | 3-4 | shared |  | `test_disabled_delegation_preserves_host_launch_endpoint` (to verify at adoption) |
| X | `test_explicit_build_and_image_override` | 5 | shared (rewrite) | decision U3 | `test_image_freshness_and_build_arguments` (to verify at adoption) |
| X | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared |  | `test_runtime_build_receives_host_ca_only_when_trusted` (to verify at adoption) |
| X | `test_engine_failure_matrix_before_image_operations` | 5 | shared |  | `test_launch_verification_fails_before_image_operations` (to verify at adoption) |
| X | `test_unsupported_contexts` | 3-4 | shared |  | to verify at adoption |
| X | `test_explicit_unix_launch_connection` | 3-4 | shared |  | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` (to verify at adoption) |
| X | `test_slash_only_endpoints_rejected_before_podman` | 3-4 | shared |  | to verify at adoption |
| X | `test_verification_normal_terminators_and_socket_spaces` | 3-4 | shared |  | to verify at adoption |
| X | `test_extra_launch_records_are_not_trimmed` | 3-4 | shared |  | `test_engine_records_reject_carriage_returns_and_extra_records` (to verify at adoption) |
| X | `test_extra_delegation_records_are_not_trimmed` | 3-4 | shared |  | `test_engine_records_reject_carriage_returns_and_extra_records` (to verify at adoption) |
| X | `test_failed_queries_with_valid_looking_raw_output` | 1-2 | shared |  | to verify at adoption |
| X | `test_yolo_case_insensitive_and_delegation_independent` | 3-4 | hook |  | - |
| X | `test_all_names_decimal_bounds_and_listing_error` | 6 | shared |  | to verify at adoption |
| X | `test_root_prefix_and_numeric_upper_bound` | 6 | shared |  | to verify at adoption |
| X | `test_collision_retries_and_exhaustion` | 6 | shared |  | `test_collision_exhaustion_and_diagnostic_cleanup` (to verify at adoption) |
| X | `test_creation_and_collision_query_failures` | 6 | shared |  | to verify at adoption |
| X | `test_owned_name_is_not_a_collision` | 6 | shared |  | `test_owned_name_behind_a_failed_create_is_not_a_collision` (to verify at adoption) |
| X | `test_interrupted_creation_is_recovered_by_label` | 7 | shared |  | `test_interrupted_creation_recovery_calls_are_bounded` (to verify at adoption) |
| X | `test_application_status_and_cleanup_failure` | 7 | shared |  | `test_cleanup_failure_or_stall_preserves_application_status` (to verify at adoption) |
| X | `test_signals_during_creation` | 7 | shared (rewrite) | decision U9 | `test_creation_records_are_validated` (to verify at adoption) |
| X | `test_permanently_stalled_creation_signal_matrix` | 7 | shared (rewrite) | decision U9 | `test_signal_matrix_is_bounded_in_creation_and_attachment` (to verify at adoption) |
| X | `test_interrupted_creation_invalid_identity_and_control_failures` | 7 | shared |  | `test_interrupted_creation_recovers_only_owned_identity` (to verify at adoption) |
| X | `test_stopped_creation_client_is_cancelled` | 6 | shared |  | to verify at adoption |
| X | `test_unreapable_client_reports_without_waiting` | 7 | shared |  | to verify at adoption |
| X | `test_attached_signals_both_modes` | 7 | shared |  | `test_composition_and_independence_in_both_state_modes` (to verify at adoption) |
| X | `test_stubborn_application_and_stalled_cleanup_are_bounded` | 7 | shared (rewrite) | decision U9 | `test_stalled_read_only_query_is_bounded` (to verify at adoption) |
| X | `test_terminal_matrix` | 6 | shared |  | `test_tty_allocated_for_terminal` (to verify at adoption) |
| X | `test_pipe_and_file_input_reach_eof` | 6 | shared |  | to verify at adoption |
| X | `test_image_and_build_status_matrix` | 6 | shared |  | `test_image_freshness_and_build_arguments` (to verify at adoption) |
| X | `test_tmpfs_capacities_and_options` | 5 | shared (rewrite) | decision U7 | to verify at adoption |
| X | `test_state_overlapping_the_workspace_fails_without_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_private_state_creation_and_mask` | 6 | shared |  | `test_private_creation_does_not_change_host_command_umask` (to verify at adoption) |
| X | `test_existing_state_relative_symlink_and_spaces` | 3-4 | shared |  | `test_insecure_existing_state_rejected` (to verify at adoption) |
| X | `test_invalid_state_before_image_operations` | 5 | shared |  | `test_launch_verification_fails_before_image_operations` (to verify at adoption) |
| X | `test_inaccessible_state` | 3-4 | shared |  | `test_inaccessible_state_and_ignored_permissions` (to verify at adoption) |
| X | `test_wrong_owner_controlled_fixture` | 3-4 | shared |  | `test_private_existing_configuration_and_wrong_owner` (to verify at adoption) |
| X | `test_non_enforcing_modes_controlled_fixture` | 1-2 | shared |  | to verify at adoption |
| X | `test_default_state_and_help_with_invalid_state` | 3-4 | shared |  | `test_shared_state_default_and_override` (to verify at adoption) |
| X | `test_socket_override_and_remapped_source` | 3-4 | shared |  | to verify at adoption |
| X | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared |  | `test_podman5_unix_url_host_socket_is_bound_as_path` (to verify at adoption) |
| X | `test_socket_fallbacks_and_symlink` | 3-4 | shared |  | `test_workspace_worktree_and_symlink` (to verify at adoption) |
| X | `test_invalid_socket_paths` | 3-4 | shared |  | `test_socket_fallback_and_invalid_sources` (to verify at adoption) |
| X | `test_inaccessible_socket` | 3-4 | shared |  | `test_socket_precedence_and_remapping` (to verify at adoption) |
| X | `test_service_failures_before_image_operations` | 5 | shared |  | `test_launch_verification_fails_before_image_operations` (to verify at adoption) |
| X | `test_permissions_independent_and_exact_opt_in` | 3-4 | hook |  | - |
| X | `test_workspace_parent_symlink_and_mount_boundary` | 5 | shared |  | `test_workspace_worktree_and_symlink` (to verify at adoption) |
| X | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared |  | to verify at adoption |
| X | `test_hardening_and_default_budgets_in_every_mode` | 5 | shared |  | `test_hardening_and_budgets_in_every_mode` (to verify at adoption) |
| X | `test_budget_overrides` | 1-2 | shared |  | `test_budget_overrides_and_rejections_precede_engine` (to verify at adoption) |
| X | `test_invalid_budgets_and_lifetime_rejected_before_engine` | 6 | shared |  | to verify at adoption |
| X | `test_budget_mismatch_and_inspection_failure_stop_before_start` | 6 | shared |  | to verify at adoption |
| X | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared |  | to verify at adoption |
| X | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared |  | to verify at adoption |
| X | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared |  | to verify at adoption |
| X | `test_lifetime_argument_and_notice` | 6 | shared |  | `test_lifetime_notice_preserves_status` (to verify at adoption) |
| X | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_wsl_drive_roots` | 3-4 | shared |  | `test_wsl_drive_roots_refused_but_subdirectories_accepted` (to verify at adoption) |
| X | `test_unsafe_workspace_override_is_exact` | 3-4 | shared |  | to verify at adoption |
| X | `test_help_documents_hardening` | 5 | shared |  | `test_hardening_and_budgets_in_every_mode` (to verify at adoption) |
| X | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_toolchain_cannot_set_codex_variables` | 5 | shared (duplicate) | duplicate of C | as the duplicated case |
| X | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| X | `test_missing_mode_stops_before_engine_state_and_other_checks` | 3-4 | shared (rewrite) | decision U1 | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` (to verify at adoption) |
| X | `test_mode_and_delegation_rejections_precede_engine` | 3-4 | shared |  | `test_budget_overrides_and_rejections_precede_engine` (to verify at adoption) |
| X | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared |  | `test_help_composes_profile_provider_and_agent_parts` (to verify at adoption) |
| X | `test_maintenance_gates_every_build` | 5 | shared |  | to verify at adoption |
| X | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared |  | to verify at adoption |
| X | `test_isolated_home_mounts_and_privacy` | 5 | shared |  | to verify at adoption |
| X | `test_host_ca_trust_modes` | 5 | shared |  | `test_runtime_build_receives_host_ca_only_when_trusted` (to verify at adoption) |
| X | `test_offline_order_arguments_and_status` | 6 | shared |  | to verify at adoption |
| X | `test_provider_order_protected_overrides_and_api_key` | 5 | shared (rewrite) | decision U10 (protected overrides stay a hook test) | to verify at adoption |
| X | `test_api_key_follows_the_policy_authentication_method` | 1-2 | shared (rewrite) | decision U10 | to verify at adoption |
| X | `test_failed_qualification_stops_before_session_resources` | 1-2 | shared |  | `test_provider_session_starts_and_stops_the_proxy_with_the_selected_credential` (to verify at adoption) |
| X | `test_interrupted_restricted_helpers_are_bounded_and_clean_owned_proxy` | 7 | shared |  | `test_interrupted_creation_recovery_calls_are_bounded` (to verify at adoption) |
| X | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared |  | to verify at adoption |
| X | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared |  | to verify at adoption |
| X | `test_unrestricted_codex_keeps_its_own_sandbox` | 1-2 | hook |  | - |
| X | `test_qualification_entry_points` | 1-2 | shared |  | to verify at adoption |
| A | `test_help_without_podman_or_side_effects` | 1-2 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_argument_forwarding_and_defaults` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_four_independent_permission_combinations` | 1-2 | hook |  | - |
| A | `test_boolean_forms_and_invalid_values` | 1-2 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_shell_does_not_receive_yolo_or_cli_arguments` | 1-2 | shared (rewrite) | decision U14 | `test_shell_mode_skips_the_agent_arguments_and_bypass` (to verify at adoption) |
| A | `test_workspace_worktree_and_symlink` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_read_only_identity_and_no_extra_host_mounts` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_insecure_existing_state_rejected` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_state_preflight_failures_before_images` | 5 | shared |  | to verify at adoption |
| A | `test_private_state_symlink_and_scoped_umask` | 3-4 | shared |  | `test_private_creation_does_not_change_host_command_umask` (to verify at adoption) |
| A | `test_delegation_does_not_retarget_launch_connection` | 3-4 | shared |  | `test_disabled_delegation_preserves_host_launch_endpoint` (to verify at adoption) |
| A | `test_explicit_temporary_mount_arguments` | 5 | shared |  | to verify at adoption |
| A | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_tty_allocated_for_terminal` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_socket_only_required_when_enabled` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_socket_engine_must_be_rootless` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_rootful_and_remote_rejected_local_unix_accepted` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_exact_delegation_cli_and_shell` | 3-4 | shared |  | `test_delegation_only_follows_the_exact_opt_in` (to verify at adoption) |
| A | `test_complete_socket_response_required` | 3-4 | shared |  | `test_socket_only_required_when_enabled` (to verify at adoption) |
| A | `test_inaccessible_socket_rejected` | 3-4 | shared |  | `test_socket_precedence_and_remapping` (to verify at adoption) |
| A | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_socket_selection_canonicalization_and_host_remapping` | 3-4 | shared |  | `test_socket_precedence_and_remapping` (to verify at adoption) |
| A | `test_relative_existing_and_missing_socket_rejected_before_delegation_query` | 3-4 | shared |  | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` (to verify at adoption) |
| A | `test_complete_launch_response_required` | 3-4 | shared |  | `test_response_validation_composes_with_launch_modes` (to verify at adoption) |
| A | `test_launch_endpoint_rejected_before_query` | 3-4 | shared |  | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` (to verify at adoption) |
| A | `test_build_location_refresh_and_missing_image` | 5 | shared (rewrite) | decision U3, U8 | `test_build_location_refresh_and_missing_image` |
| A | `test_every_build_requires_exact_maintenance` | 5 | shared |  | to verify at adoption |
| A | `test_build_and_image_inspection_errors` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_exit_status_and_owned_cleanup` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_existing_names_and_collision_retry` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_create_failure_preserved_without_cleanup_of_other_containers` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_diagnostic_cleanup_all_exit_paths` | 7 | shared |  | `test_exit_status_and_owned_cleanup` (to verify at adoption) |
| A | `test_diagnostic_cleanup_on_startup_signals` | 7 | shared |  | `test_collision_exhaustion_and_diagnostic_cleanup` (to verify at adoption) |
| A | `test_private_cid_ownership_and_collision_errors` | 6 | shared |  | to verify at adoption |
| A | `test_owned_name_is_not_a_collision` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_interrupted_creation_is_recovered_by_label` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_creation_signal_ownership_races` | 7 | shared |  | `test_signal_matrix_is_bounded_in_creation_and_attachment` (to verify at adoption) |
| A | `test_stalled_creation_cancellation_is_bounded` | 7 | shared |  | `test_stalled_read_only_query_is_bounded` (to verify at adoption) |
| A | `test_attached_signal_matrix` | 7 | shared |  | `test_signal_matrix_is_bounded_in_creation_and_attachment` (to verify at adoption) |
| A | `test_stubborn_sessions_and_control_failures_are_bounded` | 7 | shared (rewrite) | decision U9 | to verify at adoption |
| A | `test_application_status_survives_cleanup_failure` | 7 | shared |  | `test_cleanup_failure_or_stall_preserves_application_status` (to verify at adoption) |
| A | `test_timeout_prerequisite_without_help_side_effects` | 3-4 | shared |  | `test_timeout_prerequisite_and_independent_help` (to verify at adoption) |
| A | `test_key_forwarded_by_name_without_value_in_argv` | 5 | shared |  | to verify at adoption |
| A | `test_term_forwarding` | 7 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_hardening_and_default_budgets_in_every_mode` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_budget_overrides` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_invalid_budgets_and_lifetime_rejected_before_engine` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_budget_mismatch_and_inspection_failure_stop_before_start` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_lifetime_argument_and_notice` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_wsl_drive_roots` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_unsafe_workspace_override_is_exact` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_help_documents_hardening` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_missing_mode_stops_before_engine` | 3-4 | shared (rewrite) | decision U1 | `test_engine_default_secrets_are_masked_in_every_mode` (to verify at adoption) |
| A | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_mode_state_and_delegation_rejections_precede_engine` | 3-4 | shared |  | `test_budget_overrides_and_rejections_precede_engine` (to verify at adoption) |
| A | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_state_choices_and_configuration_directory` | 3-4 | shared (rewrite) | decision U4 | `test_state_alias_and_configuration_escape` (to verify at adoption) |
| A | `test_host_ca_trust` | 5 | shared |  | `test_runtime_build_receives_host_ca_only_when_trusted` (to verify at adoption) |
| A | `test_offline_order_arguments_and_forwarding` | 7 | shared |  | `test_unrestricted_environment_order_forwarding_and_hooks` (to verify at adoption) |
| A | `test_provider_order_and_profile_credentials` | 5 | shared (rewrite) | decision U10 (agent settings stay a hook test) | `test_help_composes_profile_provider_and_agent_parts` (to verify at adoption) |
| A | `test_unrestricted_keeps_forwarding_without_bus` | 5 | shared (rewrite) | decision U10, U11 | `test_unrestricted_environment_order_forwarding_and_hooks` (to verify at adoption) |
| A | `test_failed_qualification_and_interrupted_helpers_clean_up` | 7 | shared |  | to verify at adoption |
| A | `test_qualification_entry_points` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| A | `test_restricted_credentials_match_the_agent_profile` | 5 | shared |  | `test_help_composes_profile_provider_and_agent_parts` (to verify at adoption) |
| A | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_toolchain_cannot_set_agent_variables` | 5 | shared (duplicate) | duplicate of C | as the duplicated case |
| A | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| A | `test_antigravity_settings_win_over_toolchain_variables` | 5 | hook |  | - |
| A | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_baseline_fixture` | 1-2 | fake engine |  | - |
| O | `test_help_and_arguments` | 1-2 | shared |  | `test_timeout_prerequisite_and_independent_help` (to verify at adoption) |
| O | `test_modes` | 1-2 | shared |  | `test_response_validation_composes_with_launch_modes` (to verify at adoption) |
| O | `test_launch_validation` | 3-4 | shared |  | `test_response_validation_composes_with_launch_modes` (to verify at adoption) |
| O | `test_exact_delegation_and_remapping` | 3-4 | shared |  | `test_delegation_only_follows_the_exact_opt_in` (to verify at adoption) |
| O | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_socket_validation_and_precedence` | 3-4 | shared |  | `test_socket_precedence_and_remapping` (to verify at adoption) |
| O | `test_private_xdg_and_umask` | 5 | hook |  | - |
| O | `test_state_files_broken_links_and_resolution` | 3-4 | shared |  | to verify at adoption |
| O | `test_host_xdg_variables_do_not_relocate_state` | 5 | hook |  | - |
| O | `test_config_override_conflicts_with_isolated_state` | 3-4 | shared |  | `test_shared_state_default_and_override` (to verify at adoption) |
| O | `test_mount_paths_and_boundaries` | 5 | shared |  | to verify at adoption |
| O | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_tmpfs_and_named_environment` | 5 | hook |  | - |
| O | `test_claude_state_is_never_mounted` | 5 | hook |  | - |
| O | `test_integrations_require_exact_opt_in` | 5 | hook |  | - |
| O | `test_missing_opted_in_integration_fails_early` | 5 | hook |  | - |
| O | `test_provider_profiles` | 5 | hook |  | - |
| O | `test_unsupported_provider_fails_early` | 5 | hook |  | - |
| O | `test_unselected_provider_forwards_nothing_and_notifies` | 5 | hook |  | - |
| O | `test_extra_environment_names` | 6 | shared (rewrite) | decision U5, U13 | `test_agent_environment_cannot_set_core_names` (to verify at adoption) |
| O | `test_home_layout` | 5 | shared |  | to verify at adoption |
| O | `test_deprecated_shim` | 1-2 | obsolete |  | - |
| O | `test_labels_use_common_namespace` | 6 | obsolete |  | - |
| O | `test_image_and_ignored_version_variables` | 5 | shared (rewrite) | decision IMAGE refusal kept, U2 notices removed | to verify at adoption |
| O | `test_isolated_state_directory` | 3-4 | shared |  | to verify at adoption |
| O | `test_budgets` | 1-2 | shared |  | `test_hardening_and_budgets_in_every_mode` (to verify at adoption) |
| O | `test_budget_inspection_failures` | 6 | shared |  | to verify at adoption |
| O | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_lifetime` | 6 | shared |  | `test_lifetime_notice_preserves_status` (to verify at adoption) |
| O | `test_sensitive_workspaces` | 3-4 | shared |  | `test_sensitive_workspaces_refused_before_engine` (to verify at adoption) |
| O | `test_yolo_switch` | 1-2 | hook |  | - |
| O | `test_image_inspection_and_build` | 5 | shared |  | `test_build_and_image_inspection_errors` (to verify at adoption) |
| O | `test_stalled_creation_cancellation_is_bounded` | 7 | shared (duplicate) | duplicate of A | as the duplicated case |
| O | `test_attached_signal_matrix` | 7 | shared (duplicate) | duplicate of A | as the duplicated case |
| O | `test_stubborn_sessions_and_control_failures_are_bounded` | 7 | shared (rewrite) | decision U9 | to verify at adoption |
| O | `test_application_status_survives_cleanup_failure` | 7 | shared (duplicate) | duplicate of A | as the duplicated case |
| O | `test_owned_name_is_not_a_collision` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_names_failures_and_owned_records` | 6 | shared |  | to verify at adoption |
| O | `test_creation_signals` | 7 | shared |  | `test_creation_records_are_validated` (to verify at adoption) |
| O | `test_tty_and_mixed_streams` | 6 | shared |  | `test_tty_allocated_for_terminal` (to verify at adoption) |
| O | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| O | `test_toolchain_cannot_override_protected_variables` | 5 | shared |  | `test_toolchain_variables_and_protected_session_variables` (to verify at adoption) |
| O | `test_toolchain_cannot_set_agent_variables` | 5 | shared (duplicate) | duplicate of C | as the duplicated case |
| O | `test_missing_mode_stops_before_engine_state_and_other_checks` | 3-4 | shared (rewrite) | decision U1 | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` (to verify at adoption) |
| O | `test_mode_and_delegation_rejections_precede_engine` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_maintenance_gates_every_build` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_host_ca_trust_modes` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_offline_order_arguments_and_status` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_provider_order_credentials_and_protected_values` | 5 | shared (rewrite) | decision U10 (OpenCode flags stay a hook test) | to verify at adoption |
| O | `test_restricted_modes_reserve_network_variables` | 1-2 | shared |  | to verify at adoption |
| O | `test_failed_qualification_stops_before_session_resources` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_interrupted_restricted_helpers_are_bounded_and_clean_owned_proxy` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_qualification_entry_points` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_restricted_credentials_match_the_agent_profile` | 5 | shared (duplicate) | duplicate of A | as the duplicated case |
| O | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| O | `test_session_names_the_effective_configuration_directory` | 6 | shared |  | to verify at adoption |
| P | `test_fixture_rejects_unknown_and_preserves_records` | 3-4 | fake engine |  | - |
| P | `test_help_without_engine_or_state` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_help_without_podman_installed` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_valid_launch_engine_without_delegation` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_engine_failure_matrix_before_image_operations` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_unsupported_contexts` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_explicit_unix_launch_connection` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_slash_only_endpoints_rejected_before_podman` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_verification_normal_terminators_and_socket_spaces` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_extra_launch_records_are_not_trimmed` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_extra_delegation_records_are_not_trimmed` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_failed_queries_with_valid_looking_raw_output` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_all_names_decimal_bounds_and_listing_error` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_collision_retries_and_exhaustion` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_creation_and_collision_query_failures` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_owned_name_is_not_a_collision` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_interrupted_creation_is_recovered_by_label` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_application_status_and_cleanup_failure` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_signals_during_creation` | 7 | shared (rewrite) | decision U9 | `test_creation_records_are_validated` (to verify at adoption) |
| P | `test_permanently_stalled_creation_signal_matrix` | 7 | shared (rewrite) | decision U9 | `test_signal_matrix_is_bounded_in_creation_and_attachment` (to verify at adoption) |
| P | `test_interrupted_creation_invalid_identity_and_control_failures` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_stopped_creation_client_is_cancelled` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_unreapable_client_reports_without_waiting` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_attached_signals_both_modes` | 7 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_stubborn_application_and_stalled_cleanup_are_bounded` | 7 | shared (rewrite) | decision U9 | `test_stalled_read_only_query_is_bounded` (to verify at adoption) |
| P | `test_terminal_matrix` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_pipe_and_file_input_reach_eof` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_image_and_build_status_matrix` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_private_state_creation_and_mask` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_invalid_state_before_image_operations` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_inaccessible_state` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_wrong_owner_controlled_fixture` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_non_enforcing_modes_controlled_fixture` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_socket_override_and_remapped_source` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_socket_fallbacks_and_symlink` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_invalid_socket_paths` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_inaccessible_socket` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_service_failures_before_image_operations` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_modes_image_override_and_native_help` | 5 | shared |  | to verify at adoption |
| P | `test_help_missing_version_and_runtime` | 1-2 | hook |  | - |
| P | `test_exact_delegation_and_connection_forwarding` | 7 | shared |  | `test_delegation_only_follows_the_exact_opt_in` (to verify at adoption) |
| P | `test_physical_state_both_directories_and_readonly` | 3-4 | shared |  | `test_composition_and_independence_in_both_state_modes` (to verify at adoption) |
| P | `test_workspace_parent_identity_tmpfs_and_controls` | 5 | shared |  | to verify at adoption |
| P | `test_hash_inspection_build_inputs_and_failures` | 5 | shared |  | `test_agent_build_inputs_join_the_hash` (to verify at adoption) |
| P | `test_dedicated_home_layout` | 5 | shared |  | to verify at adoption |
| P | `test_isolated_state_directory` | 3-4 | shared (duplicate) | duplicate of O | as the duplicated case |
| P | `test_prefix_fallback_identity_records_and_attempt_environment` | 6 | shared |  | to verify at adoption |
| P | `test_build_cannot_consume_session_input` | 5 | shared |  | `test_healthy_build_and_session_outlive_shutdown_budget` (to verify at adoption) |
| P | `test_missing_successful_cid_reports_unresolved` | 6 | shared |  | to verify at adoption |
| P | `test_runtime_runner_prerequisites_and_smoke_image_guard` | 5 | fake engine |  | - |
| P | `test_retained_editors_gitconfig_and_secrets` | 5 | hook |  | - |
| P | `test_gitconfig_requires_exact_opt_in` | 5 | hook |  | - |
| P | `test_gitconfig_opt_in_without_regular_file` | 5 | hook |  | - |
| P | `test_gitconfig_deprecated_alias` | 5 | obsolete |  | - |
| P | `test_suite_leaves_no_scratch_directories` | 1-2 | fake engine |  | - |
| P | `test_common_names_and_deprecated_aliases` | 1-2 | obsolete |  | - |
| P | `test_yolo_has_no_effect` | 1-2 | hook |  | - |
| P | `test_budget_validation` | 1-2 | shared |  | to verify at adoption |
| P | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S | as the duplicated case |
| P | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_budget_inspection` | 6 | shared |  | `test_build_and_image_inspection_errors` (to verify at adoption) |
| P | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_lifetime_notice` | 6 | shared |  | `test_lifetime_notice_preserves_status` (to verify at adoption) |
| P | `test_sensitive_workspaces` | 3-4 | shared (duplicate) | duplicate of O | as the duplicated case |
| P | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| P | `test_toolchain_cannot_set_agent_variables` | 5 | shared (duplicate) | duplicate of C | as the duplicated case |
| P | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S | as the duplicated case |
| P | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| P | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| P | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S | as the duplicated case |
| P | `test_restricted_sessions_declare_the_toolchain_mount_and_keep_pi_settings` | 5 | hook |  | - |
| P | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_missing_mode_and_removed_network_stop_before_engine` | 3-4 | obsolete |  | - |
| P | `test_mode_and_delegation_rejections_precede_engine` | 3-4 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_maintenance_gates_every_build` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_invalid_ca_bundle_stops_build_only_before_image_operations` | 5 | shared |  | `test_runtime_build_receives_host_ca_only_when_trusted` (to verify at adoption) |
| P | `test_build_only_refresh` | 5 | shared |  | `test_build_only_operation_builds_and_exits` (to verify at adoption) |
| P | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_config_override_session_value_and_host_ca` | 5 | shared |  | to verify at adoption |
| P | `test_offline_order_arguments_and_forwarding` | 7 | shared (duplicate) | duplicate of A | as the duplicated case |
| P | `test_provider_order_and_profile_credentials` | 5 | shared (rewrite) | decision U10 (agent settings stay a hook test) | `test_help_composes_profile_provider_and_agent_parts` (to verify at adoption) |
| P | `test_unrestricted_keeps_forwarding` | 5 | shared (rewrite) | decision U10, U11 | `test_unrestricted_environment_order_forwarding_and_hooks` (to verify at adoption) |
| P | `test_failed_qualification_and_interrupted_helpers_clean_up` | 7 | shared (duplicate) | duplicate of A | as the duplicated case |
| P | `test_qualification_entry_points` | 1-2 | shared (duplicate) | duplicate of X | as the duplicated case |
| P | `test_restricted_credentials_match_the_agent_profile` | 5 | shared (duplicate) | duplicate of A | as the duplicated case |

## Other shared test files

These shared files change with the core; they are not wrapper tests and are not counted above.

| File | Change |
| --- | --- |
| `tests/test_alignment.py` | checks `agent/launcher.sh` and the thin entry script instead of profile values inside the wrapper; compares `agent/launcher.sh` with `agent/profile.json` and `AGENT_CREDENTIALS` with `agent/policies/default.json` |
| `tests/test_agent_profile.py` | `native.exec`, `native.exec_tmp`; `install.runtime_build` removed |
| `tests/test_setup.py` | setup builds through the wrapper only (`runtime_build` removed); setup and smoke drop `ENV_VARS` and `READONLY_STATE` |
| `tests/test_qualification.py` | a missing mode resolves to the profile default |
