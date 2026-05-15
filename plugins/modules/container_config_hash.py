#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat, Inc.
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
import hashlib
import os
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: container_config_hash
author:
  - "Emilien Macchi (@EmilienM)"
  - "Roberto Alfieri (@rebtoor)"
version_added: '2.9'
short_description: Compute config hash from container volume mounts
notes: []
description:
  - Compute a SHA-256 hash from files in config volume mount paths.
    Returns the hash without modifying any file.
requirements:
  - None
options:
  volumes:
    description:
      - List of volume mount strings (host:container:opts format).
        Only volumes with host paths under config_vol_prefix are hashed.
    type: list
    default: []
  config_vol_prefix:
    description:
      - Host path prefix used to filter which volumes contain config data.
    type: str
    default: '/var/lib/openstack'
"""

EXAMPLES = """
- name: Compute config hash for a service
  container_config_hash:
    volumes:
      - "/var/lib/openstack/certs/ovn/default/ca.crt:/etc/pki/tls/certs/ca.crt:ro,z"
      - "/var/lib/openstack/healthchecks/ovn_controller:/openstack:ro,z"
  register: result

# result.hash contains the computed SHA-256 hash string
"""

BUF_SIZE = 65536
SHARED_CONFIG_NAMESPACES = ('certs', 'cacerts', 'configs')


class ContainerConfigHashManager:
    """Compute config hashes for container volume mounts.

    Takes a list of volume mount strings, filters for config volumes
    under config_vol_prefix, and returns a SHA-256 hash of their contents.
    """

    def __init__(self, module, results):

        super(ContainerConfigHashManager, self).__init__()
        self.module = module
        self.results = results

        # parse args
        args = self.module.params

        # Set parameters
        self.config_vol_prefix = args['config_vol_prefix']

        self._hash_config_volumes(args.get('volumes', []))

        self.module.exit_json(**self.results)

    def _hash_config_volumes(self, volumes):
        """Compute config hash from volume list without writing to any file.

        Filters volumes by config_vol_prefix, resolves each to its config
        base directory via _get_config_base, deduplicates, then computes
        SHA-256 of all files in each directory.

        :param volumes: list of volume mount strings (host:container:opts)
        """
        prefix = self.config_vol_prefix
        config_bases = set()
        for v in volumes:
            host_path = v.split(":")[0]
            if host_path.startswith(prefix):
                config_bases.add(self._get_config_base(prefix, host_path))
        if not config_bases:
            self.results['hash'] = ''
            return
        hashes = [
            self._calculate_checksum(vol_path)
            for vol_path in sorted(config_bases)
        ]
        self.results['hash'] = '-'.join(hashes)

    def _read_file(self, file):
        """Read a given file and return its content.

        :param file: string
        :returns: bytes
        """
        r = b''
        with open(file, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                r += data
                if not data:
                    break
        return r

    def _calculate_checksum(self, config_volume):
        """Calculate a SHA-256 hash from all files in the given directory.

        :param config_volume: string
        :returns: string
        """
        total_hash = hashlib.new('sha256')
        for file in glob.glob(config_volume + '/**/*', recursive=True):
            if os.path.isfile(file):
                total_hash.update(self._read_file(file))
        return total_hash.hexdigest()

    def _get_config_base(self, prefix, volume):
        """Returns a config base path for a specific volume.

        :param prefix: string
        :param volume: string
        :returns: string
        """
        path = volume
        base = prefix.rstrip(os.path.sep)
        shared_bases = tuple(
            os.path.join(base, namespace)
            for namespace in SHARED_CONFIG_NAMESPACES
        )
        while path.startswith(prefix):
            dirname = os.path.dirname(path)
            if dirname == base or dirname in shared_bases:
                return path
            else:
                path = dirname
        self.module.fail_json(
            msg='Could not find config base for: {} '
                'with prefix: {}'.format(volume, prefix))


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )
    ContainerConfigHashManager(module, results)


if __name__ == '__main__':
    main()
