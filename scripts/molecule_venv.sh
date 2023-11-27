#!/bin/bash
set -euxo pipefail

LOCAL_MOLECULE_ENV=$(mktemp -d)/molecule
if which python3.9 2>/dev/null; then
    python3.9 -m venv $LOCAL_MOLECULE_ENV
else
    echo WARNING: python3.9 binary is not in path. Tests will run with system python: $(python3 --version) at $(which python3)
    python3 -m venv $LOCAL_MOLECULE_ENV
fi

# some python modules need to be compiled
if ! command -v python3-config 2>/dev/null; then
    if -e /etc/redhat-release; then
        sudo dnf -y install python3-devel
    else
        echo "Please, install python3 development package otherwise installation of modules could fail"
    fi
fi

source $LOCAL_MOLECULE_ENV/bin/activate

pip install -r molecule-requirements.txt
ansible-galaxy collection install -r requirements.yml
./scripts/test_roles.py
deactivate
