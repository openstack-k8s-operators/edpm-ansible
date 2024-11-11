#!/bin/bash -e
set -eux pipefail

microdnf -y makecache
microdnf install -y \
    gcc \
    libssh-devel \
    iputils \
    bind-utils \
    ncurses \
    openssh-clients \
    "python${PYV}" \
    "python${PYV}-cffi" \
    "python${PYV}-pip" \
    "python${PYV}-pyyaml" \
    "python${PYV}-wheel" \
    util-linux-user \
    which \
    rsync \
    zsh

microdnf -y clean all

"/usr/bin/python${PYV}" -m pip install --no-cache -r $REMOTE_SOURCE_DIR/openstack_ansibleee/requirements.txt
