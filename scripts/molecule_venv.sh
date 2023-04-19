#!/bin/bash
LOCAL_MOLECULE_ENV=$(mktemp -d)/molecule
python -m venv $LOCAL_MOLECULE_ENV
source $LOCAL_MOLECULE_ENV/bin/activate
pip install -r molecule-requirements.txt
pip install molecule
./scripts/test_roles.py
deactivate
