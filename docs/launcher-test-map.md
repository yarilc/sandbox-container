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
No test covers U1 (provider default) yet; the implementation change adds one.

| Repository | Test | Phase | Destination | Note |
| --- | --- | --- | --- | --- |
| S | `test_help_without_podman_or_side_effects` | 1-2 | shared |  |
| S | `test_missing_mode_defaults_to_offline_and_needs_an_installation` | 1-2 | shared |  |
| S | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` | 1-2 | shared |  |
| S | `test_setup_diagnostic_quotes_invoked_symlink_and_runs_from_other_workspace` | 6 | shared |  |
| S | `test_network_preflight_rejections_precede_image_operations` | 5 | shared |  |
| S | `test_maintenance_is_separate_from_runtime_mode` | 5 | shared |  |
| S | `test_restricted_unprotected_installation_fails_before_image_operations` | 7 | shared |  |
| S | `test_argument_forwarding_and_defaults` | 6 | shared |  |
| S | `test_delegation_only_follows_the_exact_opt_in` | 3-4 | shared |  |
| S | `test_boolean_forms_and_invalid_values` | 1-2 | shared |  |
| S | `test_shell_option_is_equivalent` | 1-2 | shared |  |
| S | `test_workspace_worktree_and_symlink` | 3-4 | shared |  |
| S | `test_read_only_identity_and_no_extra_host_mounts` | 5 | shared |  |
| S | `test_toolchain_command_dispatch` | 5 | shared |  |
| S | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared |  |
| S | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared |  |
| S | `test_toolchain_mount_can_be_disabled` | 5 | shared |  |
| S | `test_default_toolchain_environment_is_appended` | 5 | shared |  |
| S | `test_toolchain_variables_and_protected_session_variables` | 5 | shared |  |
| S | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared |  |
| S | `test_hardening_and_budgets_in_every_mode` | 5 | shared |  |
| S | `test_budget_overrides_and_rejections_precede_engine` | 3-4 | shared |  |
| S | `test_budget_rules_match_shared_python_module` | 1-2 | shared |  |
| S | `test_budgets_follow_delegated_controllers` | 3-4 | shared |  |
| S | `test_engine_default_secrets_are_masked_in_every_mode` | 5 | shared |  |
| S | `test_agent_dev_layout_attaches_terminals_in_every_mode` | 6 | shared |  |
| S | `test_ignored_budgets_stop_before_start_and_remove_owned_container` | 6 | shared |  |
| S | `test_lifetime_notice_preserves_status` | 6 | shared |  |
| S | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared |  |
| S | `test_wsl_drive_roots_refused_but_subdirectories_accepted` | 3-4 | shared |  |
| S | `test_insecure_existing_state_rejected` | 3-4 | shared |  |
| S | `test_tty_allocated_for_terminal` | 6 | shared |  |
| S | `test_socket_only_required_when_enabled` | 3-4 | shared |  |
| S | `test_socket_engine_must_be_rootless` | 3-4 | shared |  |
| S | `test_rootful_and_remote_rejected_local_unix_accepted` | 3-4 | shared |  |
| S | `test_build_location_refresh_and_missing_image` | 5 | shared (rewrite) | decision U3, U8 |
| S | `test_runtime_build_receives_host_ca_only_when_trusted` | 5 | shared |  |
| S | `test_build_and_image_inspection_errors` | 5 | shared |  |
| S | `test_exit_status_and_owned_cleanup` | 7 | shared |  |
| S | `test_successful_restart_check_is_informational_and_real_errors_remain` | 6 | shared |  |
| S | `test_cleanup_failure_or_stall_preserves_application_status` | 7 | shared |  |
| S | `test_ignored_signals_force_owned_removal` | 7 | shared |  |
| S | `test_stalled_controls_and_repeated_signal_are_bounded` | 7 | shared |  |
| S | `test_interrupted_creation_recovers_only_owned_identity` | 7 | shared |  |
| S | `test_interrupted_creation_rejects_foreign_recovery_result` | 7 | shared |  |
| S | `test_interrupted_creation_recovery_calls_are_bounded` | 7 | shared |  |
| S | `test_collision_reconciliation_can_be_interrupted` | 7 | shared |  |
| S | `test_failed_create_after_id_publication_is_cleaned` | 6 | shared |  |
| S | `test_failed_signal_delivery_still_removes_owned_container` | 7 | shared |  |
| S | `test_timeout_prerequisite_and_independent_help` | 3-4 | shared |  |
| S | `test_healthy_build_and_session_outlive_shutdown_budget` | 7 | shared |  |
| S | `test_existing_names_and_collision_retry` | 6 | shared |  |
| S | `test_create_failure_preserved_without_cleanup_of_other_containers` | 7 | shared |  |
| S | `test_term_forwarding` | 7 | shared |  |
| S | `test_launch_verification_fails_before_image_operations` | 5 | shared |  |
| S | `test_verification_preserves_exact_record_boundaries_and_status` | 6 | shared (rewrite) | decision U16, U17 |
| S | `test_delegated_response_rejects_carriage_returns_before_image_operations` | 5 | shared |  |
| S | `test_response_validation_composes_with_launch_modes` | 3-4 | shared |  |
| S | `test_delegated_cr_response_preserves_query_failure_and_disabled_access` | 3-4 | shared |  |
| S | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` | 3-4 | shared |  |
| S | `test_help_with_pathless_launch_endpoint` | 3-4 | shared |  |
| S | `test_shared_state_default_and_override` | 3-4 | shared |  |
| S | `test_state_conflict_fails_without_engine` | 3-4 | shared |  |
| S | `test_state_overlapping_the_workspace_fails_without_engine` | 3-4 | shared |  |
| S | `test_private_creation_does_not_change_host_command_umask` | 6 | shared |  |
| S | `test_shell_state_and_history_location` | 3-4 | shared |  |
| S | `test_state_alias_and_configuration_escape` | 3-4 | shared |  |
| S | `test_private_existing_configuration_and_wrong_owner` | 3-4 | shared |  |
| S | `test_inaccessible_state_and_ignored_permissions` | 3-4 | shared |  |
| S | `test_socket_disabled_values_skip_delegation_checks` | 3-4 | shared |  |
| S | `test_socket_precedence_and_remapping` | 3-4 | shared |  |
| S | `test_podman5_unix_url_host_socket_is_bound_as_path` | 3-4 | shared |  |
| S | `test_socket_fallback_and_invalid_sources` | 3-4 | shared (rewrite) | decision U16 |
| S | `test_invalid_delegation_results_gate_explicit_build` | 5 | shared (rewrite) | decision U16 |
| S | `test_composition_and_independence_in_both_state_modes` | 3-4 | shared (rewrite) | decision U7 |
| S | `test_disabled_delegation_preserves_host_launch_endpoint` | 3-4 | shared (rewrite) | decision U16, U17 |
| S | `test_ca_mount_and_security_policy` | 5 | shared (rewrite) | decision U7 |
| S | `test_symlink_invocation_and_native_permissions` | 3-4 | shared |  |
| S | `test_collision_exhaustion_and_diagnostic_cleanup` | 7 | shared |  |
| S | `test_int_and_hup_forwarding` | 7 | shared |  |
| C | `test_shipped_inventories_are_exact` | 1-2 | hook |  |
| C | `test_removed_account_hosts_require_a_separate_profile` | 1-2 | hook |  |
| C | `test_help_without_podman_or_side_effects` | 1-2 | shared (duplicate) | duplicate of S |
| C | `test_missing_network_mode_requires_setup_without_side_effects` | 1-2 | shared (rewrite) | decision U1 |
| C | `test_missing_mode_precedes_options_prerequisites_and_other_configuration` | 1-2 | shared (duplicate) | duplicate of S |
| C | `test_setup_diagnostic_quotes_invoked_symlink_and_runs_from_other_workspace` | 6 | shared (duplicate) | duplicate of S |
| C | `test_network_preflight_rejections_precede_image_operations` | 5 | shared (duplicate) | duplicate of S |
| C | `test_maintenance_is_separate_from_runtime_mode` | 5 | shared (duplicate) | duplicate of S |
| C | `test_restricted_unprotected_installation_fails_before_image_operations` | 7 | shared (duplicate) | duplicate of S |
| C | `test_argument_forwarding_and_defaults` | 6 | shared (duplicate) | duplicate of S |
| C | `test_four_independent_permission_combinations` | 1-2 | hook |  |
| C | `test_boolean_forms_and_invalid_values` | 1-2 | shared (duplicate) | duplicate of S |
| C | `test_shell_does_not_receive_yolo_or_cli_arguments` | 1-2 | shared (rewrite) | decision U14 |
| C | `test_workspace_worktree_and_symlink` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_read_only_identity_and_no_extra_host_mounts` | 5 | shared (duplicate) | duplicate of S |
| C | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S |
| C | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S |
| C | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S |
| C | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S |
| C | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S |
| C | `test_toolchain_cannot_set_claude_variables` | 5 | shared |  |
| C | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S |
| C | `test_hardening_and_budgets_in_every_mode` | 5 | shared (duplicate) | duplicate of S |
| C | `test_budget_overrides_and_rejections_precede_engine` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_budget_rules_match_shared_python_module` | 1-2 | shared (duplicate) | duplicate of S |
| C | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_engine_default_secrets_are_masked_in_every_mode` | 5 | shared (duplicate) | duplicate of S |
| C | `test_agent_dev_layout_attaches_terminals_in_every_mode` | 6 | shared (duplicate) | duplicate of S |
| C | `test_ignored_budgets_stop_before_start_and_remove_owned_container` | 6 | shared (duplicate) | duplicate of S |
| C | `test_lifetime_notice_preserves_status` | 6 | shared (duplicate) | duplicate of S |
| C | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_wsl_drive_roots_refused_but_subdirectories_accepted` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_proxy_hardening_failure_never_starts_agent` | 5 | shared |  |
| C | `test_proxy_probe_timeout_and_interruption_clean_only_proxy` | 7 | shared |  |
| C | `test_insecure_existing_state_rejected` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_tty_allocated_for_terminal` | 6 | shared (duplicate) | duplicate of S |
| C | `test_socket_only_required_when_enabled` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_socket_engine_must_be_rootless` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_rootful_and_remote_rejected_local_unix_accepted` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_build_location_refresh_and_missing_image` | 5 | shared (rewrite) | decision U3, U8 |
| C | `test_runtime_build_receives_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of S |
| C | `test_build_and_image_inspection_errors` | 5 | shared (duplicate) | duplicate of S |
| C | `test_exit_status_and_owned_cleanup` | 7 | shared (duplicate) | duplicate of S |
| C | `test_successful_restart_check_is_informational_and_real_errors_remain` | 6 | shared (duplicate) | duplicate of S |
| C | `test_cleanup_failure_or_stall_preserves_application_status` | 7 | shared (duplicate) | duplicate of S |
| C | `test_ignored_signals_force_owned_removal` | 7 | shared (duplicate) | duplicate of S |
| C | `test_stalled_controls_and_repeated_signal_are_bounded` | 7 | shared (duplicate) | duplicate of S |
| C | `test_interrupted_creation_recovers_only_owned_identity` | 7 | shared (duplicate) | duplicate of S |
| C | `test_interrupted_creation_rejects_foreign_recovery_result` | 7 | shared (duplicate) | duplicate of S |
| C | `test_interrupted_creation_recovery_calls_are_bounded` | 7 | shared (duplicate) | duplicate of S |
| C | `test_collision_reconciliation_can_be_interrupted` | 7 | shared (duplicate) | duplicate of S |
| C | `test_failed_create_after_id_publication_is_cleaned` | 6 | shared (duplicate) | duplicate of S |
| C | `test_failed_signal_delivery_still_removes_owned_container` | 7 | shared (duplicate) | duplicate of S |
| C | `test_timeout_prerequisite_and_independent_help` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_healthy_build_and_session_outlive_shutdown_budget` | 7 | shared (duplicate) | duplicate of S |
| C | `test_existing_names_and_collision_retry` | 6 | shared (duplicate) | duplicate of S |
| C | `test_create_failure_preserved_without_cleanup_of_other_containers` | 7 | shared (duplicate) | duplicate of S |
| C | `test_term_forwarding` | 7 | shared (duplicate) | duplicate of S |
| C | `test_launch_verification_fails_before_image_operations` | 5 | shared (duplicate) | duplicate of S |
| C | `test_verification_preserves_exact_record_boundaries_and_status` | 6 | shared (rewrite) | decision U16, U17 |
| C | `test_delegated_response_rejects_carriage_returns_before_image_operations` | 5 | shared (duplicate) | duplicate of S |
| C | `test_response_validation_composes_with_launch_modes` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_delegated_cr_response_preserves_query_failure_and_disabled_access` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_pathless_or_relative_unix_launch_endpoint_rejected_before_query` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_help_with_pathless_launch_endpoint` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_shared_state_default_and_override` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_state_conflict_fails_without_engine` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_state_overlapping_the_workspace_fails_without_engine` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_private_creation_does_not_change_host_command_umask` | 6 | shared (duplicate) | duplicate of S |
| C | `test_state_alias_and_configuration_escape` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_private_existing_claude_and_wrong_owner` | 3-4 | shared |  |
| C | `test_inaccessible_state_and_ignored_permissions` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_socket_disabled_values_skip_delegation_checks` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_socket_precedence_and_remapping` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_podman5_unix_url_host_socket_is_bound_as_path` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_socket_fallback_and_invalid_sources` | 3-4 | shared (rewrite) | decision U16 |
| C | `test_invalid_delegation_results_gate_explicit_build` | 5 | shared (rewrite) | decision U16 |
| C | `test_composition_and_independence_in_both_state_modes` | 3-4 | shared (rewrite) | decision U7 |
| C | `test_disabled_delegation_preserves_host_launch_endpoint` | 3-4 | shared (rewrite) | decision U16, U17 |
| C | `test_ca_mount_and_security_policy` | 5 | shared (rewrite) | decision U7 |
| C | `test_symlink_invocation_and_native_permissions` | 3-4 | shared (duplicate) | duplicate of S |
| C | `test_collision_exhaustion_and_diagnostic_cleanup` | 7 | shared (duplicate) | duplicate of S |
| C | `test_int_and_hup_forwarding` | 7 | shared (duplicate) | duplicate of S |
| X | `test_help_without_engine_or_state` | 3-4 | shared |  |
| X | `test_help_without_podman_installed` | 7 | shared |  |
| X | `test_valid_launch_engine_without_delegation` | 3-4 | shared |  |
| X | `test_explicit_build_and_image_override` | 5 | shared (rewrite) | decision U3 |
| X | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared |  |
| X | `test_engine_failure_matrix_before_image_operations` | 5 | shared |  |
| X | `test_unsupported_contexts` | 3-4 | shared |  |
| X | `test_explicit_unix_launch_connection` | 3-4 | shared |  |
| X | `test_slash_only_endpoints_rejected_before_podman` | 3-4 | shared |  |
| X | `test_verification_normal_terminators_and_socket_spaces` | 3-4 | shared |  |
| X | `test_extra_launch_records_are_not_trimmed` | 3-4 | shared |  |
| X | `test_extra_delegation_records_are_not_trimmed` | 3-4 | shared |  |
| X | `test_failed_queries_with_valid_looking_raw_output` | 1-2 | shared |  |
| X | `test_yolo_case_insensitive_and_delegation_independent` | 3-4 | hook |  |
| X | `test_all_names_decimal_bounds_and_listing_error` | 6 | shared |  |
| X | `test_root_prefix_and_numeric_upper_bound` | 6 | shared |  |
| X | `test_collision_retries_and_exhaustion` | 6 | shared |  |
| X | `test_creation_and_collision_query_failures` | 6 | shared |  |
| X | `test_owned_name_is_not_a_collision` | 6 | shared |  |
| X | `test_interrupted_creation_is_recovered_by_label` | 7 | shared |  |
| X | `test_application_status_and_cleanup_failure` | 7 | shared |  |
| X | `test_signals_during_creation` | 7 | shared (rewrite) | decision U9 |
| X | `test_permanently_stalled_creation_signal_matrix` | 7 | shared (rewrite) | decision U9 |
| X | `test_interrupted_creation_invalid_identity_and_control_failures` | 7 | shared |  |
| X | `test_stopped_creation_client_is_cancelled` | 6 | shared |  |
| X | `test_unreapable_client_reports_without_waiting` | 7 | shared |  |
| X | `test_attached_signals_both_modes` | 7 | shared |  |
| X | `test_stubborn_application_and_stalled_cleanup_are_bounded` | 7 | shared (rewrite) | decision U9 |
| X | `test_terminal_matrix` | 6 | shared |  |
| X | `test_pipe_and_file_input_reach_eof` | 6 | shared |  |
| X | `test_image_and_build_status_matrix` | 6 | shared |  |
| X | `test_tmpfs_capacities_and_options` | 5 | shared (rewrite) | decision U7 |
| X | `test_state_overlapping_the_workspace_fails_without_engine` | 3-4 | shared (duplicate) | duplicate of S |
| X | `test_private_state_creation_and_mask` | 6 | shared |  |
| X | `test_existing_state_relative_symlink_and_spaces` | 3-4 | shared |  |
| X | `test_invalid_state_before_image_operations` | 5 | shared |  |
| X | `test_inaccessible_state` | 3-4 | shared |  |
| X | `test_wrong_owner_controlled_fixture` | 3-4 | shared |  |
| X | `test_non_enforcing_modes_controlled_fixture` | 1-2 | shared |  |
| X | `test_default_state_and_help_with_invalid_state` | 3-4 | shared |  |
| X | `test_socket_override_and_remapped_source` | 3-4 | shared |  |
| X | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared |  |
| X | `test_socket_fallbacks_and_symlink` | 3-4 | shared |  |
| X | `test_invalid_socket_paths` | 3-4 | shared |  |
| X | `test_inaccessible_socket` | 3-4 | shared |  |
| X | `test_service_failures_before_image_operations` | 5 | shared |  |
| X | `test_permissions_independent_and_exact_opt_in` | 3-4 | hook |  |
| X | `test_workspace_parent_symlink_and_mount_boundary` | 5 | shared |  |
| X | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared |  |
| X | `test_hardening_and_default_budgets_in_every_mode` | 5 | shared |  |
| X | `test_budget_overrides` | 1-2 | shared |  |
| X | `test_invalid_budgets_and_lifetime_rejected_before_engine` | 6 | shared |  |
| X | `test_budget_mismatch_and_inspection_failure_stop_before_start` | 6 | shared |  |
| X | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S |
| X | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared |  |
| X | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared |  |
| X | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared |  |
| X | `test_lifetime_argument_and_notice` | 6 | shared |  |
| X | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared (duplicate) | duplicate of S |
| X | `test_wsl_drive_roots` | 3-4 | shared |  |
| X | `test_unsafe_workspace_override_is_exact` | 3-4 | shared |  |
| X | `test_help_documents_hardening` | 5 | shared |  |
| X | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S |
| X | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S |
| X | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S |
| X | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S |
| X | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S |
| X | `test_toolchain_cannot_set_codex_variables` | 5 | shared (duplicate) | duplicate of C |
| X | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S |
| X | `test_missing_mode_stops_before_engine_state_and_other_checks` | 3-4 | shared (rewrite) | decision U1 |
| X | `test_mode_and_delegation_rejections_precede_engine` | 3-4 | shared |  |
| X | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared |  |
| X | `test_maintenance_gates_every_build` | 5 | shared |  |
| X | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared |  |
| X | `test_isolated_home_mounts_and_privacy` | 5 | shared |  |
| X | `test_host_ca_trust_modes` | 5 | shared |  |
| X | `test_offline_order_arguments_and_status` | 6 | shared |  |
| X | `test_provider_order_protected_overrides_and_api_key` | 5 | shared (rewrite) | decision U10 (protected overrides stay a hook test) |
| X | `test_api_key_follows_the_policy_authentication_method` | 1-2 | shared (rewrite) | decision U10 |
| X | `test_failed_qualification_stops_before_session_resources` | 1-2 | shared |  |
| X | `test_interrupted_restricted_helpers_are_bounded_and_clean_owned_proxy` | 7 | shared |  |
| X | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared |  |
| X | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared |  |
| X | `test_unrestricted_codex_keeps_its_own_sandbox` | 1-2 | hook |  |
| X | `test_qualification_entry_points` | 1-2 | shared |  |
| A | `test_help_without_podman_or_side_effects` | 1-2 | shared (duplicate) | duplicate of S |
| A | `test_argument_forwarding_and_defaults` | 6 | shared (duplicate) | duplicate of S |
| A | `test_four_independent_permission_combinations` | 1-2 | hook |  |
| A | `test_boolean_forms_and_invalid_values` | 1-2 | shared (duplicate) | duplicate of S |
| A | `test_shell_does_not_receive_yolo_or_cli_arguments` | 1-2 | shared (rewrite) | decision U14 |
| A | `test_workspace_worktree_and_symlink` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_read_only_identity_and_no_extra_host_mounts` | 5 | shared (duplicate) | duplicate of S |
| A | `test_insecure_existing_state_rejected` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_state_preflight_failures_before_images` | 5 | shared |  |
| A | `test_private_state_symlink_and_scoped_umask` | 3-4 | shared |  |
| A | `test_delegation_does_not_retarget_launch_connection` | 3-4 | shared |  |
| A | `test_explicit_temporary_mount_arguments` | 5 | shared |  |
| A | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared (duplicate) | duplicate of X |
| A | `test_tty_allocated_for_terminal` | 6 | shared (duplicate) | duplicate of S |
| A | `test_socket_only_required_when_enabled` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_socket_engine_must_be_rootless` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_rootful_and_remote_rejected_local_unix_accepted` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_exact_delegation_cli_and_shell` | 3-4 | shared |  |
| A | `test_complete_socket_response_required` | 3-4 | shared |  |
| A | `test_inaccessible_socket_rejected` | 3-4 | shared |  |
| A | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared (duplicate) | duplicate of X |
| A | `test_socket_selection_canonicalization_and_host_remapping` | 3-4 | shared |  |
| A | `test_relative_existing_and_missing_socket_rejected_before_delegation_query` | 3-4 | shared |  |
| A | `test_complete_launch_response_required` | 3-4 | shared |  |
| A | `test_launch_endpoint_rejected_before_query` | 3-4 | shared |  |
| A | `test_build_location_refresh_and_missing_image` | 5 | shared (rewrite) | decision U3, U8 |
| A | `test_every_build_requires_exact_maintenance` | 5 | shared |  |
| A | `test_build_and_image_inspection_errors` | 5 | shared (duplicate) | duplicate of S |
| A | `test_exit_status_and_owned_cleanup` | 7 | shared (duplicate) | duplicate of S |
| A | `test_existing_names_and_collision_retry` | 6 | shared (duplicate) | duplicate of S |
| A | `test_create_failure_preserved_without_cleanup_of_other_containers` | 7 | shared (duplicate) | duplicate of S |
| A | `test_diagnostic_cleanup_all_exit_paths` | 7 | shared |  |
| A | `test_diagnostic_cleanup_on_startup_signals` | 7 | shared |  |
| A | `test_private_cid_ownership_and_collision_errors` | 6 | shared |  |
| A | `test_owned_name_is_not_a_collision` | 6 | shared (duplicate) | duplicate of X |
| A | `test_interrupted_creation_is_recovered_by_label` | 7 | shared (duplicate) | duplicate of X |
| A | `test_creation_signal_ownership_races` | 7 | shared |  |
| A | `test_stalled_creation_cancellation_is_bounded` | 7 | shared |  |
| A | `test_attached_signal_matrix` | 7 | shared |  |
| A | `test_stubborn_sessions_and_control_failures_are_bounded` | 7 | shared (rewrite) | decision U9 |
| A | `test_application_status_survives_cleanup_failure` | 7 | shared |  |
| A | `test_timeout_prerequisite_without_help_side_effects` | 3-4 | shared |  |
| A | `test_key_forwarded_by_name_without_value_in_argv` | 5 | shared |  |
| A | `test_term_forwarding` | 7 | shared (duplicate) | duplicate of S |
| A | `test_hardening_and_default_budgets_in_every_mode` | 5 | shared (duplicate) | duplicate of X |
| A | `test_budget_overrides` | 1-2 | shared (duplicate) | duplicate of X |
| A | `test_invalid_budgets_and_lifetime_rejected_before_engine` | 6 | shared (duplicate) | duplicate of X |
| A | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of X |
| A | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared (duplicate) | duplicate of X |
| A | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared (duplicate) | duplicate of X |
| A | `test_budget_mismatch_and_inspection_failure_stop_before_start` | 6 | shared (duplicate) | duplicate of X |
| A | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared (duplicate) | duplicate of X |
| A | `test_lifetime_argument_and_notice` | 6 | shared (duplicate) | duplicate of X |
| A | `test_sensitive_workspaces_refused_before_engine` | 3-4 | shared (duplicate) | duplicate of S |
| A | `test_wsl_drive_roots` | 3-4 | shared (duplicate) | duplicate of X |
| A | `test_unsafe_workspace_override_is_exact` | 3-4 | shared (duplicate) | duplicate of X |
| A | `test_help_documents_hardening` | 5 | shared (duplicate) | duplicate of X |
| A | `test_missing_mode_stops_before_engine` | 3-4 | shared (rewrite) | decision U1 |
| A | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared (duplicate) | duplicate of X |
| A | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared (duplicate) | duplicate of X |
| A | `test_mode_state_and_delegation_rejections_precede_engine` | 3-4 | shared |  |
| A | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared (duplicate) | duplicate of X |
| A | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared (duplicate) | duplicate of X |
| A | `test_state_choices_and_configuration_directory` | 3-4 | shared (rewrite) | decision U4 |
| A | `test_host_ca_trust` | 5 | shared |  |
| A | `test_offline_order_arguments_and_forwarding` | 7 | shared |  |
| A | `test_provider_order_and_profile_credentials` | 5 | shared (rewrite) | decision U10 (agent settings stay a hook test) |
| A | `test_unrestricted_keeps_forwarding_without_bus` | 5 | shared (rewrite) | decision U10, U11 |
| A | `test_failed_qualification_and_interrupted_helpers_clean_up` | 7 | shared |  |
| A | `test_qualification_entry_points` | 1-2 | shared (duplicate) | duplicate of X |
| A | `test_restricted_credentials_match_the_agent_profile` | 5 | shared |  |
| A | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S |
| A | `test_toolchain_cannot_set_agent_variables` | 5 | shared (duplicate) | duplicate of C |
| A | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S |
| A | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S |
| A | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S |
| A | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S |
| A | `test_antigravity_settings_win_over_toolchain_variables` | 5 | hook |  |
| A | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S |
| O | `test_baseline_fixture` | 1-2 | fake engine |  |
| O | `test_help_and_arguments` | 1-2 | shared |  |
| O | `test_modes` | 1-2 | shared |  |
| O | `test_launch_validation` | 3-4 | shared |  |
| O | `test_exact_delegation_and_remapping` | 3-4 | shared |  |
| O | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared (duplicate) | duplicate of X |
| O | `test_socket_validation_and_precedence` | 3-4 | shared |  |
| O | `test_private_xdg_and_umask` | 5 | hook |  |
| O | `test_state_files_broken_links_and_resolution` | 3-4 | shared |  |
| O | `test_host_xdg_variables_do_not_relocate_state` | 5 | hook |  |
| O | `test_config_override_conflicts_with_isolated_state` | 3-4 | shared |  |
| O | `test_mount_paths_and_boundaries` | 5 | shared |  |
| O | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared (duplicate) | duplicate of X |
| O | `test_tmpfs_and_named_environment` | 5 | hook |  |
| O | `test_claude_state_is_never_mounted` | 5 | hook |  |
| O | `test_integrations_require_exact_opt_in` | 5 | hook |  |
| O | `test_missing_opted_in_integration_fails_early` | 5 | hook |  |
| O | `test_provider_profiles` | 5 | hook |  |
| O | `test_unsupported_provider_fails_early` | 5 | hook |  |
| O | `test_unselected_provider_forwards_nothing_and_notifies` | 5 | hook |  |
| O | `test_extra_environment_names` | 6 | shared (rewrite) | decision U5, U13 |
| O | `test_home_layout` | 5 | shared |  |
| O | `test_deprecated_shim` | 1-2 | obsolete |  |
| O | `test_labels_use_common_namespace` | 6 | obsolete |  |
| O | `test_image_and_ignored_version_variables` | 5 | shared (rewrite) | decision IMAGE refusal kept, U2 notices removed |
| O | `test_isolated_state_directory` | 3-4 | shared |  |
| O | `test_budgets` | 1-2 | shared |  |
| O | `test_budget_inspection_failures` | 6 | shared |  |
| O | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S |
| O | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared (duplicate) | duplicate of X |
| O | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared (duplicate) | duplicate of X |
| O | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of X |
| O | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared (duplicate) | duplicate of X |
| O | `test_lifetime` | 6 | shared |  |
| O | `test_sensitive_workspaces` | 3-4 | shared |  |
| O | `test_yolo_switch` | 1-2 | hook |  |
| O | `test_image_inspection_and_build` | 5 | shared |  |
| O | `test_stalled_creation_cancellation_is_bounded` | 7 | shared (duplicate) | duplicate of A |
| O | `test_attached_signal_matrix` | 7 | shared (duplicate) | duplicate of A |
| O | `test_stubborn_sessions_and_control_failures_are_bounded` | 7 | shared (rewrite) | decision U9 |
| O | `test_application_status_survives_cleanup_failure` | 7 | shared (duplicate) | duplicate of A |
| O | `test_owned_name_is_not_a_collision` | 6 | shared (duplicate) | duplicate of X |
| O | `test_names_failures_and_owned_records` | 6 | shared |  |
| O | `test_creation_signals` | 7 | shared |  |
| O | `test_tty_and_mixed_streams` | 6 | shared |  |
| O | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S |
| O | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S |
| O | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S |
| O | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S |
| O | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S |
| O | `test_restricted_sessions_declare_the_toolchain_mount` | 5 | shared (duplicate) | duplicate of S |
| O | `test_toolchain_cannot_override_protected_variables` | 5 | shared |  |
| O | `test_toolchain_cannot_set_agent_variables` | 5 | shared (duplicate) | duplicate of C |
| O | `test_missing_mode_stops_before_engine_state_and_other_checks` | 3-4 | shared (rewrite) | decision U1 |
| O | `test_mode_and_delegation_rejections_precede_engine` | 3-4 | shared (duplicate) | duplicate of X |
| O | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared (duplicate) | duplicate of X |
| O | `test_maintenance_gates_every_build` | 5 | shared (duplicate) | duplicate of X |
| O | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared (duplicate) | duplicate of X |
| O | `test_host_ca_trust_modes` | 5 | shared (duplicate) | duplicate of X |
| O | `test_offline_order_arguments_and_status` | 6 | shared (duplicate) | duplicate of X |
| O | `test_provider_order_credentials_and_protected_values` | 5 | shared (rewrite) | decision U10 (OpenCode flags stay a hook test) |
| O | `test_restricted_modes_reserve_network_variables` | 1-2 | shared |  |
| O | `test_failed_qualification_stops_before_session_resources` | 1-2 | shared (duplicate) | duplicate of X |
| O | `test_interrupted_restricted_helpers_are_bounded_and_clean_owned_proxy` | 7 | shared (duplicate) | duplicate of X |
| O | `test_qualification_entry_points` | 1-2 | shared (duplicate) | duplicate of X |
| O | `test_restricted_credentials_match_the_agent_profile` | 5 | shared (duplicate) | duplicate of A |
| O | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared (duplicate) | duplicate of X |
| O | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared (duplicate) | duplicate of X |
| O | `test_session_names_the_effective_configuration_directory` | 6 | shared |  |
| P | `test_fixture_rejects_unknown_and_preserves_records` | 3-4 | fake engine |  |
| P | `test_help_without_engine_or_state` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_help_without_podman_installed` | 7 | shared (duplicate) | duplicate of X |
| P | `test_valid_launch_engine_without_delegation` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_engine_failure_matrix_before_image_operations` | 5 | shared (duplicate) | duplicate of X |
| P | `test_unsupported_contexts` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_explicit_unix_launch_connection` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_slash_only_endpoints_rejected_before_podman` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_verification_normal_terminators_and_socket_spaces` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_extra_launch_records_are_not_trimmed` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_extra_delegation_records_are_not_trimmed` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_failed_queries_with_valid_looking_raw_output` | 1-2 | shared (duplicate) | duplicate of X |
| P | `test_all_names_decimal_bounds_and_listing_error` | 6 | shared (duplicate) | duplicate of X |
| P | `test_collision_retries_and_exhaustion` | 6 | shared (duplicate) | duplicate of X |
| P | `test_creation_and_collision_query_failures` | 6 | shared (duplicate) | duplicate of X |
| P | `test_owned_name_is_not_a_collision` | 6 | shared (duplicate) | duplicate of X |
| P | `test_interrupted_creation_is_recovered_by_label` | 7 | shared (duplicate) | duplicate of X |
| P | `test_application_status_and_cleanup_failure` | 7 | shared (duplicate) | duplicate of X |
| P | `test_signals_during_creation` | 7 | shared (rewrite) | decision U9 |
| P | `test_permanently_stalled_creation_signal_matrix` | 7 | shared (rewrite) | decision U9 |
| P | `test_interrupted_creation_invalid_identity_and_control_failures` | 7 | shared (duplicate) | duplicate of X |
| P | `test_stopped_creation_client_is_cancelled` | 6 | shared (duplicate) | duplicate of X |
| P | `test_unreapable_client_reports_without_waiting` | 7 | shared (duplicate) | duplicate of X |
| P | `test_attached_signals_both_modes` | 7 | shared (duplicate) | duplicate of X |
| P | `test_stubborn_application_and_stalled_cleanup_are_bounded` | 7 | shared (rewrite) | decision U9 |
| P | `test_terminal_matrix` | 6 | shared (duplicate) | duplicate of X |
| P | `test_pipe_and_file_input_reach_eof` | 6 | shared (duplicate) | duplicate of X |
| P | `test_image_and_build_status_matrix` | 6 | shared (duplicate) | duplicate of X |
| P | `test_private_state_creation_and_mask` | 6 | shared (duplicate) | duplicate of X |
| P | `test_invalid_state_before_image_operations` | 5 | shared (duplicate) | duplicate of X |
| P | `test_inaccessible_state` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_wrong_owner_controlled_fixture` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_non_enforcing_modes_controlled_fixture` | 1-2 | shared (duplicate) | duplicate of X |
| P | `test_socket_override_and_remapped_source` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_podman5_socket_url_is_reduced_to_its_path` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_socket_fallbacks_and_symlink` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_invalid_socket_paths` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_inaccessible_socket` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_service_failures_before_image_operations` | 5 | shared (duplicate) | duplicate of X |
| P | `test_modes_image_override_and_native_help` | 5 | shared |  |
| P | `test_help_missing_version_and_runtime` | 1-2 | hook |  |
| P | `test_exact_delegation_and_connection_forwarding` | 7 | shared |  |
| P | `test_physical_state_both_directories_and_readonly` | 3-4 | shared |  |
| P | `test_workspace_parent_identity_tmpfs_and_controls` | 5 | shared |  |
| P | `test_hash_inspection_build_inputs_and_failures` | 5 | shared |  |
| P | `test_dedicated_home_layout` | 5 | shared |  |
| P | `test_isolated_state_directory` | 3-4 | shared (duplicate) | duplicate of O |
| P | `test_prefix_fallback_identity_records_and_attempt_environment` | 6 | shared |  |
| P | `test_build_cannot_consume_session_input` | 5 | shared |  |
| P | `test_missing_successful_cid_reports_unresolved` | 6 | shared |  |
| P | `test_runtime_runner_prerequisites_and_smoke_image_guard` | 5 | fake engine |  |
| P | `test_retained_editors_gitconfig_and_secrets` | 5 | hook |  |
| P | `test_gitconfig_requires_exact_opt_in` | 5 | hook |  |
| P | `test_gitconfig_opt_in_without_regular_file` | 5 | hook |  |
| P | `test_gitconfig_deprecated_alias` | 5 | obsolete |  |
| P | `test_suite_leaves_no_scratch_directories` | 1-2 | fake engine |  |
| P | `test_common_names_and_deprecated_aliases` | 1-2 | obsolete |  |
| P | `test_yolo_has_no_effect` | 1-2 | hook |  |
| P | `test_budget_validation` | 1-2 | shared |  |
| P | `test_device_and_secret_mounts_in_every_unrestricted_mode` | 5 | shared (duplicate) | duplicate of X |
| P | `test_budgets_follow_delegated_controllers` | 3-4 | shared (duplicate) | duplicate of S |
| P | `test_unverifiable_controller_list_stops_before_state` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_unenforced_budget_present_or_enforced_budget_missing_stops` | 1-2 | shared (duplicate) | duplicate of X |
| P | `test_budget_inspection` | 6 | shared |  |
| P | `test_short_failure_across_a_second_boundary_has_no_lifetime_notice` | 6 | shared (duplicate) | duplicate of X |
| P | `test_lifetime_notice` | 6 | shared |  |
| P | `test_sensitive_workspaces` | 3-4 | shared (duplicate) | duplicate of O |
| P | `test_toolchain_command_dispatch` | 5 | shared (duplicate) | duplicate of S |
| P | `test_toolchain_cannot_set_agent_variables` | 5 | shared (duplicate) | duplicate of C |
| P | `test_toolchain_library_created_private_and_mounted_read_only` | 6 | shared (duplicate) | duplicate of S |
| P | `test_unsafe_toolchain_library_stops_before_engine_operations` | 5 | shared (duplicate) | duplicate of S |
| P | `test_toolchain_mount_can_be_disabled` | 5 | shared (duplicate) | duplicate of S |
| P | `test_default_toolchain_environment_is_appended` | 5 | shared (duplicate) | duplicate of S |
| P | `test_restricted_sessions_declare_the_toolchain_mount_and_keep_pi_settings` | 5 | hook |  |
| P | `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | 1-2 | shared (duplicate) | duplicate of X |
| P | `test_client_stderr_passes_through_the_diagnostics_filter` | 6 | shared (duplicate) | duplicate of X |
| P | `test_missing_mode_and_removed_network_stop_before_engine` | 3-4 | obsolete |  |
| P | `test_mode_and_delegation_rejections_precede_engine` | 3-4 | shared (duplicate) | duplicate of X |
| P | `test_help_documents_modes_migration_and_provider_limits` | 5 | shared (duplicate) | duplicate of X |
| P | `test_maintenance_gates_every_build` | 5 | shared (duplicate) | duplicate of X |
| P | `test_builds_receive_the_host_ca_only_when_trusted` | 5 | shared (duplicate) | duplicate of X |
| P | `test_invalid_ca_bundle_stops_build_only_before_image_operations` | 5 | shared |  |
| P | `test_build_only_refresh` | 5 | shared |  |
| P | `test_proxy_image_acquisition_requires_maintenance_and_digest` | 5 | shared (duplicate) | duplicate of X |
| P | `test_config_override_session_value_and_host_ca` | 5 | shared |  |
| P | `test_offline_order_arguments_and_forwarding` | 7 | shared (duplicate) | duplicate of A |
| P | `test_provider_order_and_profile_credentials` | 5 | shared (rewrite) | decision U10 (agent settings stay a hook test) |
| P | `test_unrestricted_keeps_forwarding` | 5 | shared (rewrite) | decision U10, U11 |
| P | `test_failed_qualification_and_interrupted_helpers_clean_up` | 7 | shared (duplicate) | duplicate of A |
| P | `test_qualification_entry_points` | 1-2 | shared (duplicate) | duplicate of X |
| P | `test_restricted_credentials_match_the_agent_profile` | 5 | shared (duplicate) | duplicate of A |

## Other shared test files

These shared files change with the core; they are not wrapper tests and are not counted above.

| File | Change |
| --- | --- |
| `tests/test_alignment.py` | checks `agent/launcher.sh` and the thin entry script instead of profile values inside the wrapper; compares `agent/launcher.sh` with `agent/profile.json` and `AGENT_CREDENTIALS` with `agent/policies/default.json` |
| `tests/test_agent_profile.py` | `native.exec`, `native.exec_tmp`; `install.runtime_build` removed |
| `tests/test_setup.py` | setup builds through the wrapper only (`runtime_build` removed); setup and smoke drop `ENV_VARS` and `READONLY_STATE` |
| `tests/test_qualification.py` | a missing mode resolves to the profile default |
