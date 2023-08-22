#!/bin/bash
set -euxo pipefail

LOCAL_MOLECULE_ENV=$(mktemp -d)/molecule
if which python3.9 2>/dev/null; then
    python3.9 -m venv $LOCAL_MOLECULE_ENV
else
    echo WARNING: python3.9 binary is not in path. Tests will run with system python: $(python --version) at $(which python)
    python -m venv $LOCAL_MOLECULE_ENV
fi

source $LOCAL_MOLECULE_ENV/bin/activate
pip install -r molecule-requirements.txt
ansible-galaxy collection install -r requirements.yml
./scripts/test_roles.py
deactivate
