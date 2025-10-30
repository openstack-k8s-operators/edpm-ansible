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

import fnmatch
import glob
import hashlib
import json
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
short_description: Generate config hashes for container startup configs
notes: []
description:
  - Generate config hashes for container startup configs
requirements:
  - None
options:
  check_mode:
    description:
      - Ansible check mode is enabled
    type: bool
    default: False
  config_vol_prefix:
    description:
      - Config volume prefix
    type: str
    default: '/var/lib/openstack'
"""

EXAMPLES = """
- name: Update config hashes for container startup configs
  container_config_hash:
"""

CONTAINER_STARTUP_CONFIG = '/var/lib/edpm-config/container-startup-config'
BUF_SIZE = 65536


class ContainerConfigHashManager:
    """Notes about this module.

    It will generate container config hash that will be consumed by
    the edpm-container-manage role that is using podman_container module.
    """

    def __init__(self, module, results):

        super(ContainerConfigHashManager, self).__init__()
        self.module = module
        self.results = results

        # parse args
        args = self.module.params

        # Set parameters
        self.config_vol_prefix = args['config_vol_prefix']

        # Update container-startup-config with new config hashes
        self._update_hashes()

        self.module.exit_json(**self.results)

    def _remove_file(self, path):
        """Remove a file.

        :param path: string
        """
        if os.path.exists(path):
            os.remove(path)

    def _find(self, path, pattern='*.json'):
        """Returns a list of files in a directory.

        :param path: string
        :param pattern: string
        :returns: list
        """
        configs = []
        if os.path.exists(path):
            for root, dirnames, filenames in os.walk(path):
                for filename in fnmatch.filter(filenames, pattern):
                    configs.append(os.path.join(root, filename))
        else:
            self.module.warn('{} does not exists'.format(path))
        return configs

    def _slurp(self, path):
        """Slurps a file and return its content.

        :param path: string
        :returns: string
        """
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        else:
            self.module.warn('{} was not found.'.format(path))
            return ''

    def _update_container_config(self, path, config):
        """Update a container config.

        :param path: string
        :param config: string
        """
        with open(path, 'wb') as f:
            f.write(json.dumps(config, indent=2).encode('utf-8'))
        os.chmod(path, 0o600)
        self.results['changed'] = True

    def _read_file(self, file):
        """Read a given file and return its content
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

    def _calculate_checksum(self, config_volume, exclusions=[]):
        """Calculate an sha256 hash from a list of files from the given folder
           and if needed exclude files from that list.

        :param config_volume: string
        :param exclusions: list
        :returns: string
        """

        total_hash = hashlib.new('sha256')
        for file in glob.glob(config_volume + '/**/*', recursive=True):
            file_relpath = '/' + os.path.relpath(file, config_volume)
            if os.path.isfile(file) and file_relpath not in exclusions:
                total_hash.update(self._read_file(file))

        return total_hash.hexdigest()

    def _get_config_base(self, prefix, volume):
        """Returns a config base path for a specific volume.

        :param prefix: string
        :param volume: string
        :returns: string
        """
        # crawl the volume's path upwards until we find the
        # volume's base, where the hashed config file resides
        path = volume
        base = prefix.rstrip(os.path.sep)
        base_generated = os.path.join(base, 'ansible-generated')
        while path.startswith(prefix):
            dirname = os.path.dirname(path)
            if dirname == base or dirname == base_generated:
                return path
            else:
                path = dirname
        self.module.fail_json(
            msg='Could not find config base for: {} '
                'with prefix: {}'.format(volume, prefix))

    def _match_config_volumes(self, config):
        """Return a list of volumes that match a config.

        :param config: dict
        :returns: list
        """
        # Match the mounted config volumes - we can't just use the
        # key as e.g "novacomute" consumes config-data/nova
        prefix = self.config_vol_prefix
        try:
            volumes = config.get('volumes', [])
        except AttributeError:
            self.module.fail_json(
                msg='Error fetching volumes. Prefix: '
                    '{} - Config: {}'.format(prefix, config))
        return sorted([self._get_config_base(prefix, v.split(":")[0])
                       for v in volumes if v.startswith(prefix)])

    def _update_hashes(self):
        """Update container startup config with new config hashes if needed.
        """
        configs = self._find(CONTAINER_STARTUP_CONFIG)
        for config in configs:
            old_config_hash = ''
            cname = os.path.splitext(os.path.basename(config))[0]
            if cname.startswith('hashed-'):
                # Take the opportunity to cleanup old hashed files which
                # don't exist anymore.
                self._remove_file(config)
                continue
            startup_config_json = json.loads(self._slurp(config))
            config_volumes = self._match_config_volumes(startup_config_json)
            if config_volumes:
                old_config_hash = startup_config_json['environment'].get(
                    'EDPM_CONFIG_HASH', '')
                exclude_from_hash = startup_config_json.get(
                    'edpm_exclude_files_from_hash', [])
                new_hashes = [
                    self._calculate_checksum(vol_path, exclude_from_hash) for vol_path in config_volumes
                ]
                new_hash = '-'.join(new_hashes)
                if new_hash != old_config_hash:
                    startup_config_json['environment']['EDPM_CONFIG_HASH'] = (
                        new_hash)
                    self._update_container_config(
                        config, startup_config_json)
                else:
                    # config doesn't need an update
                    continue


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
