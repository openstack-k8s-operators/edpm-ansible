#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import fcntl
import os
import tempfile
import traceback
from datetime import datetime

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = '''
---
module: edpm_service_state
short_description: Manage EDPM service state file with atomic updates
description:
  - Manages the EDPM service state file with proper file locking
  - Supports atomic read-modify-write operations
  - Handles service registration and removal
author:
  - "EDPM team"
options:
  state_file:
    description:
      - Path to the state file
    type: path
    required: true
  service_name:
    description:
      - Name of the service to manage
    type: str
    required: true
  containers:
    description:
      - List of container names for the service
      - Required when state is present
    type: list
    elements: str
  append:
    description:
      - If true, append containers to existing list
      - If false, replace the container list
    type: bool
    default: false
  state:
    description:
      - Whether the service should be present or absent in the state file
    type: str
    choices: ['present', 'absent']
    default: present
'''

EXAMPLES = '''
- name: Register service with containers
  osp.edpm.edpm_service_state:
    state_file: /var/lib/edpm-config/deployed_services.yaml
    service_name: nova
    containers:
      - nova_compute
      - nova_compute_init
    state: present

- name: Append containers to existing service
  osp.edpm.edpm_service_state:
    state_file: /var/lib/edpm-config/deployed_services.yaml
    service_name: nova
    containers:
      - multipathd
      - iscsid
    append: true
    state: present

- name: Remove service from state file
  osp.edpm.edpm_service_state:
    state_file: /var/lib/edpm-config/deployed_services.yaml
    service_name: old_service
    state: absent
'''

RETURN = '''
changed:
  description: Whether the state file was modified
  type: bool
  returned: always
service:
  description: Service data after the operation
  type: dict
  returned: when state is present
message:
  description: Operation result message
  type: str
  returned: always
'''

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ServiceStateManager:
    def __init__(self, module):
        self.module = module
        self.state_file = module.params['state_file']
        self.service_name = module.params['service_name']
        self.containers = module.params.get('containers', [])
        self.append = module.params['append']
        self.state = module.params['state']
        self.changed = False

    def acquire_lock(self, lock_fd):
        """Acquire exclusive lock on file descriptor"""
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        except IOError as e:
            self.module.fail_json(msg=f"Failed to acquire lock: {str(e)}")

    def read_state(self):
        """Read current state file"""
        if os.path.exists(self.state_file) and os.path.getsize(self.state_file) > 0:
            try:
                with open(self.state_file, 'r') as f:
                    data = yaml.safe_load(f)
                    return data if data else {'services': {}}
            except Exception as e:
                self.module.fail_json(msg=f"Failed to read state file: {str(e)}")
        return {'services': {}}

    def write_state(self, state_data):
        """Write state file atomically"""
        try:
            # Create temp file in same directory for atomic move
            state_dir = os.path.dirname(self.state_file) or '.'
            fd, temp_path = tempfile.mkstemp(dir=state_dir, prefix='.state_', suffix='.tmp')

            try:
                with os.fdopen(fd, 'w') as f:
                    yaml.dump(state_data, f, default_flow_style=False, indent=2)

                # Set permissions
                os.chmod(temp_path, 0o644)

                # Atomic move
                os.rename(temp_path, self.state_file)

            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

        except Exception as e:
            self.module.fail_json(msg=f"Failed to write state file: {str(e)}")

    def update_service(self, state_data):
        """Update service in state data"""
        services = state_data.setdefault('services', {})

        if self.state == 'present':
            # Get existing containers
            existing = services.get(self.service_name, {}).get('containers', [])

            # Determine new container list
            if self.append and existing:
                # Merge and deduplicate
                new_containers = list(set(existing + self.containers))
            else:
                new_containers = self.containers

            # Check if changed
            service_exists = self.service_name in services
            if not service_exists or services[self.service_name].get('containers') != new_containers:
                self.changed = True

            # Update service
            services[self.service_name] = {
                'containers': new_containers,
                'last_updated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            return services[self.service_name]

        else:  # state == 'absent'
            if self.service_name in services:
                del services[self.service_name]
                self.changed = True
                return None
            return None

    def run(self):
        """Main execution with file locking"""
        # Ensure parent directory exists
        state_dir = os.path.dirname(self.state_file)
        if state_dir and not os.path.exists(state_dir):
            try:
                os.makedirs(state_dir, mode=0o755)
            except Exception as e:
                self.module.fail_json(msg=f"Failed to create state directory: {str(e)}")

        lock_file = f"{self.state_file}.lock"

        try:
            # Open lock file
            with open(lock_file, 'w') as lock_fd:
                # Acquire exclusive lock
                self.acquire_lock(lock_fd)

                # Read current state
                state_data = self.read_state()

                # Update service
                service_data = self.update_service(state_data)

                # Write if changed
                if self.changed:
                    self.write_state(state_data)

                # Prepare result
                result = {
                    'changed': self.changed,
                    'message': f"Service {self.service_name} {'updated' if self.state == 'present' else 'removed'}"
                }

                if service_data:
                    result['service'] = service_data

                return result

        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to manage service state: {str(e)}",
                exception=traceback.format_exc()
            )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state_file=dict(type='path', required=True),
            service_name=dict(type='str', required=True),
            containers=dict(type='list', elements='str'),
            append=dict(type='bool', default=False),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
        ),
        required_if=[
            ('state', 'present', ['containers']),
        ],
        supports_check_mode=True
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML is required for this module")

    manager = ServiceStateManager(module)

    if module.check_mode:
        module.exit_json(changed=False, msg="Check mode - no changes made")

    result = manager.run()
    module.exit_json(**result)


if __name__ == '__main__':
    main()
