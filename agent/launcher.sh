# Agent part of the reference: profile data for the shared launcher core
# (launcher/core.sh). It mirrors agent/profile.json; tests/test_alignment.py
# compares the two. The reference shell has no hooks.
AGENT_NAME=sandbox-container
AGENT_DISPLAY_NAME=Sandbox
AGENT_WRAPPER=sandbox-container.sh
AGENT_ENV_PREFIX=SANDBOX_CONTAINER
AGENT_LABEL_NAMESPACE=io.sandbox-container
AGENT_IMAGE=localhost/sandbox-container
AGENT_PROXY_IMAGE=localhost/sandbox-container-egress
AGENT_HOME=/sandbox-home
AGENT_COMMAND=bash
AGENT_EXEC=/usr/local/bin/bash
AGENT_CONFIG_DIR_ENV=SANDBOX_CONTAINER_CONFIG_DIR
AGENT_CONFIG_HOME=.config/sandbox-container
AGENT_SHARED_DIRS=(.config/openspec)
AGENT_PRIVATE_SHARED_DIRS=0
AGENT_APPROVAL_BYPASS_ENV=
AGENT_EXEC_TMP=0
AGENT_CREDENTIALS=()
AGENT_POLICY_HOSTS=()
# The shell keeps its history with its configuration, out of reach of toolchains.
AGENT_SESSION_ENV=(HISTFILE=/sandbox-home/.config/sandbox-container/bash_history)
AGENT_RESTRICTED_ENV=()
AGENT_PROVIDER_ENV=()
AGENT_UNSET_ENV=()
AGENT_RESERVED_ENV=()
