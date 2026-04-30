#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import unittest


sys.path.append('plugins/modules')

from container_config_hash import ContainerConfigHashManager  # noqa: E402  # pyright: ignore[reportMissingImports]


class FakeModule(object):
    def fail_json(self, **kwargs):
        raise AssertionError(kwargs['msg'])


def _manager():
    manager = ContainerConfigHashManager.__new__(ContainerConfigHashManager)
    manager.module = FakeModule()
    manager.results = {}
    return manager


class ContainerConfigHashManagerTestCase(unittest.TestCase):
    def test_get_config_base_directly_under_prefix(self):
        manager = _manager()

        self.assertEqual(
            '/var/lib/openstack/ovn',
            manager._get_config_base(
                '/var/lib/openstack',
                '/var/lib/openstack/ovn/etc/ovn/ovn.conf'
            )
        )

    def test_match_config_volumes_deduplicates_resolved_roots(self):
        manager = _manager()
        manager.config_vol_prefix = '/var/lib/openstack'

        self.assertEqual(
            [
                '/var/lib/openstack/ovn',
            ],
            manager._match_config_volumes({
                'volumes': [
                    '/var/lib/openstack/ovn/etc/ovn/ovn.conf:/etc/ovn/ovn.conf:ro',
                    '/var/lib/openstack/ovn/etc/sysconfig:/etc/sysconfig:ro',
                ]
            })
        )
