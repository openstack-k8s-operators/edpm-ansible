#!/usr/bin/env bash

set -euxo pipefail

TEMP_VENV_ENV="$(mktemp -d)"
DOCS_DIR="./docs"

python -m venv ${TEMP_VENV_ENV} && source ${TEMP_VENV_ENV}/bin/activate

pip install -c ${UPPER_CONSTRAINTS_FILE:-https://releases.openstack.org/constraints/upper/master} -r ${DOCS_DIR}/docs-requirements.txt
ansible-galaxy install -r requirements.yml
ansible-galaxy collection install . --force

# Remove any leftovers from previous builds
rm -rf ${DOCS_DIR}/source/collections/*

# antsibull requires that the directory is only writeable by
# its owner. so ensure its 755
chmod 755 ${DOCS_DIR}/source

# Use modified antsibull-docs script
${DOCS_DIR}/source/antsibull-docs \
    collection \
    --use-current \
    --dest-dir ${DOCS_DIR}/source \
    osp.edpm

# Clean up antsibull boilerplate directives and disclaimers
sed -i 's/:orphan://' ${DOCS_DIR}/source/collections/osp/edpm/*
sed -i '/^.. Collection note$/,/^.*To use it in a playbook.*$/d' ${DOCS_DIR}/source/collections/osp/edpm/*

# Run linter on docs, skipping antsibull-docs output as it isn't up to spec
doc8 --config ${DOCS_DIR}/doc8.ini ${DOCS_DIR}/source

sphinx-build -a -E -W -d ${DOCS_DIR}/build/doctrees --keep-going -b html ${DOCS_DIR}/source ${DOCS_DIR}/build/html -T

## ASCIIDocs
# Dependencies
if ! type bundle; then \
    echo "Bundler not found. On Linux run 'sudo dnf install /usr/bin/bundle' to install it."; \
    exit 1; \
fi

bundle config set path .ruby/.bundle
bundle install --gemfile=${DOCS_DIR}/Gemfile --binstubs=.ruby

# Build
${DOCS_DIR}/.ruby/asciidoctor -a source-highlighter=highlightjs \
            -a highlightjs-languages="yaml,bash" \
            -a highlightjs-theme="monokai" \
            --failure-level WARN \
            -a build=build \
            -b xhtml5 \
            -d book \
            -o ${DOCS_DIR}/build/html/index-asciidoc.html \
            ${DOCS_DIR}/source/main.adoc

deactivate
rm -fr ${TEMP_VENV_ENV}
