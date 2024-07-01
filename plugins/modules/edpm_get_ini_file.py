#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright 2024 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import configparser

import yaml

from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: edpm_get_ini_file
author:
    - Jiri Podivin <jpodivin@redhat.com>
version_added: '0.0.1'
short_description: Retrieve contents of section, key or entire given ini file
notes: []
description: |
    Retrieve contents of given ini file. Either a single value,
    section or an entire file as a dictionary.
options:
    path:
        description: |
            Path to ini file.
        type: str
        required: true
    section:
        description: |
            Name of the section containing the key.
        type: str
    key:
        description: |
            Name of the field you want to retrieve.
        type: str

"""

EXAMPLES = """
- name: Create network configs with defaults
  edpm_get_ini_file:
    path: /path/to/ini
    section: main
    key: some_key
"""

RETURN = """
value:
    description: |
        Contents of given ini file.
    returned: success
    type: str
    sample: localhost.local
"""


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )
    # Parse args
    args = module.params

    # Argument sanity check
    if args["key"] and not args["section"]:
        module.fail_json(f"Key {args['key']} was specified without corresponding section.")
    cfg = configparser.ConfigParser(strict=False)

    # Open file
    file = cfg.read(args["path"])

    # Get file contents
    try:
        # Late check on ret val from ConfigParser
        if not file:
            module.fail_json(f"File at {args['path']} couldn't be parsed.")
        if args["section"]:
            value = dict(cfg[args["section"]])
            if args["key"]:
                value = value[args["key"]]
        else:
            value = {key: dict(val) for key, val in cfg.items()}
        results['value'] = value
    except KeyError:
        module.fail_json(
            f"File {args['path']} doesn't contain key {args['key']} in section {args['section']}")

    module.exit_json(**results)


if __name__ == '__main__':
    main()
