#!/usr/bin/env bash

set -euxo pipefail

TEMP_VENV_ENV="$(mktemp -d)"
DOCS_DIR="./docs"

python -m venv ${TEMP_VENV_ENV} && source ${TEMP_VENV_ENV}/bin/activate

pip install -r ${DOCS_DIR}/docs-requirements.txt
ansible-galaxy install -r requirements.yml

doc8 --config ${DOCS_DIR}/doc8.ini ${DOCS_DIR}/source
sphinx-build -a -E -W -d ${DOCS_DIR}/build/doctrees --keep-going -b html ${DOCS_DIR}/source ${DOCS_DIR}/build/html -T

deactivate
rm -fr ${TEMP_VENV_ENV}
