#!/usr/bin/env bash

# Adding edpm ansible-runner specific scripts here
# Expand the variables
eval "echo \"$(cat /runner/env/settings)\"" > /runner/env/settings

# Create symlinks to mounted inventories in the general inventory dir
# This will treat all files in designated paths as if they were inventories
if [ -n "$RUNNER_INVENTORY_PATHS" ]; then
    for inv_path in $RUNNER_INVENTORY_PATHS; do
        ln -s $inv_path/** /runner/inventory/
    done
fi

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
