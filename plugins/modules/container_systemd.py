#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2023 Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import glob
import json
import os
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
module: container_systemd
author:
  - "EDPM team"
version_added: '2.9'
short_description: Create systemd files and manage services to run containers
notes: []
description:
  - Manage the systemd unit files for containers with a restart policy and
    then make sure the services are started so the containers are running.
    It takes the container config data in entry to figure out how the unit
    files will be configured. It returns a list of services that were
    restarted.
requirements:
  - None
options:
  container_config:
    description:
      - List of container configurations
    type: list
    elements: dict
  systemd_healthchecks:
    default: true
    description:
      - Whether or not we cleanup the old healthchecks with SystemD.
    type: boolean
  debug:
    default: false
    description:
      - Whether or not debug is enabled.
    type: boolean
"""
EXAMPLES = """
- name: Manage container systemd services
  container_systemd:
    container_config:
      - keystone:
          image: quay.io/edpm/keystone
          restart: always
      - mysql:
          image: quay.io/edpm/mysql
          stop_grace_period: 25
          restart: always
"""
RETURN = """
restarted:
    description: List of services that were restarted
    returned: always
    type: list
    sample:
      - edpm_keystone.service
      - edpm_mysql.service
"""
