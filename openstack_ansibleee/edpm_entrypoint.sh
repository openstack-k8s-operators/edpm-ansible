#!/usr/bin/env bash

# Adding edpm ansible-runner specific scripts here
# Set defaults before expanding the settings template.
: "${RUNNER_IDLE_TIMEOUT:=600}"
: "${RUNNER_JOB_TIMEOUT:=3600}"
: "${RUNNER_PEXPECT_TIMEOUT:=10}"
: "${RUNNER_PEXPECT_USE_POLL:=True}"
: "${RUNNER_SUPPRESS_OUTPUT_FILE:=False}"
: "${RUNNER_SUPPRESS_ANSIBLE_OUTPUT:=False}"
: "${RUNNER_FACT_CACHE:=fact_cache}"
: "${RUNNER_FACT_CACHE_TYPE:=jsonfile}"

export \
    RUNNER_IDLE_TIMEOUT \
    RUNNER_JOB_TIMEOUT \
    RUNNER_PEXPECT_TIMEOUT \
    RUNNER_PEXPECT_USE_POLL \
    RUNNER_SUPPRESS_OUTPUT_FILE \
    RUNNER_SUPPRESS_ANSIBLE_OUTPUT \
    RUNNER_FACT_CACHE \
    RUNNER_FACT_CACHE_TYPE

# Expand the variables
envsubst < /runner/env/settings > /runner/env/settings.tmp && mv /runner/env/settings.tmp /runner/env/settings

if [ -n "$RUNNER_INVENTORY" ]; then
    echo "---" > /runner/inventory/inventory.yaml
    echo "$RUNNER_INVENTORY" >> /runner/inventory/inventory.yaml
fi

if [ -n "$RUNNER_PLAYBOOK" ]; then
    echo "---" > /runner/project/playbook.yaml
    echo "$RUNNER_PLAYBOOK" >> /runner/project/playbook.yaml
fi

if [ -n "$RUNNER_CMDLINE" ]; then
    echo "$RUNNER_CMDLINE" >> /runner/env/cmdline
fi

if [ -n "$RUNNER_EXTRA_VARS" ]; then
    echo "---" > /runner/env/extravars
    echo "$RUNNER_EXTRA_VARS" >> /runner/env/extravars
fi

# Contents from ansible-runner entrypoint
