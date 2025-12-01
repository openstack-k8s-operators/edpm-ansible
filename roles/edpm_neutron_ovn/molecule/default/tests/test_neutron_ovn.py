# Copyright 2023 Red Hat, Inc.
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


import os
import unittest
import uuid

import testinfra


HAPROXY_CONFIG_DIR = "/var/lib/neutron/ovn-agent-proxy"
EDPM_OVN_AGENT_SERVICE = "edpm_ovn_agent.service"
OVN_AGENT_CONTAINER = "ovn_agent"
HAPROXY_CONFIG = """
global
    log         /dev/log local0 debug
    log-tag     haproxy-ovn-agent-%(network_id)s
    user        neutron
    group       neutron
    maxconn     1024
    pidfile     /var/lib/neutron/external/pids/%(network_id)s.pid.haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor
    retries                 3
    timeout http-request    30s
    timeout connect         30s
    timeout client          32s
    timeout server          32s
    timeout http-keep-alive 30s

listen listener
    bind 169.254.169.254:80
    server metadata /var/lib/neutron/metadata_proxy

    http-request add-header X-OVN-Network-ID %(network_id)s
"""


def _get_haproxy_config(network_id):
    return HAPROXY_CONFIG % {
        'network_id': network_id}


class TestNeutronOvn(unittest.TestCase):

    def setUp(self):
        self.host = testinfra.get_host(
            "ansible://instance?ansible_inventory=%s" %
            os.environ['MOLECULE_INVENTORY_FILE'])

    def tearDown(self):
        self.host.run("/usr/bin/systemctl start %s" %
                      EDPM_OVN_AGENT_SERVICE)

    def _workaround_sys_mount_permission_problem(self, container_name=None):
        """This is helper function to workaround problem with mount of /sys

        When command like "ip netns exec ..." is going to be run in the
        rootless container it may fail with error like:

            mount of /sys failed: Operation not permitted

        more details about this and about workaround used here is available
        in the issue: https://github.com/containers/podman/issues/11887
        """
        container_cmd = ""
        if container_name:
            container_cmd = "/usr/bin/podman exec %s " % container_name
        self.host.run(container_cmd + "mkdir /sys2")
        self.host.run(
            container_cmd + "mount -t sysfs --make-private /sys2")

    def _find_haproxy_process(self, network_id):
        processes = self.host.process.filter(comm="haproxy")
        for p in processes:
            if network_id in p.args:
                return p

    def test_neutron_ovn_conf_was_copied_into_container(self):
        assert self.host.file(
            "/var/lib/config-data/ansible-generated/"
            "neutron-ovn-agent/10-neutron-ovn.conf"
        ).exists

    def test_sidecar_container_wrapper_script_was_created(self):
        assert self.host.file(
            "/var/lib/neutron/ovn_agent_haproxy_wrapper").exists

    def test_ovn_agent_container_is_running(self):
        assert self.host.podman(OVN_AGENT_CONTAINER).is_running

    def test_default_root_helper_works(self):
        ansible_vars = self.host.ansible(
            "include_vars",
            os.path.join(
                os.environ["MOLECULE_PROJECT_DIRECTORY"],
                "defaults/main.yml"))["ansible_facts"]
        root_helper = ansible_vars[
            "edpm_neutron_ovn_agent_agent_root_helper"
        ]
        self.host.run_test(
            "/usr/bin/podman exec %s %s sleep 0" %
            (OVN_AGENT_CONTAINER, root_helper))

    def test_sidecar_container(self):
        network_id = str(uuid.uuid4())
        namespace_name = "ovn-%s" % network_id
        haproxy_config_file = "%s/%s.conf" % (HAPROXY_CONFIG_DIR, network_id)
        haproxy_container_name = "neutron-haproxy-%s" % namespace_name
        # Create example haproxy config file
        self.host.run_test(
            "echo '%s' > %s" % (_get_haproxy_config(network_id),
                                haproxy_config_file))
        self._workaround_sys_mount_permission_problem()
        self._workaround_sys_mount_permission_problem(
            OVN_AGENT_CONTAINER)
        self.host.run_test("/sbin/ip netns add %s" % namespace_name)
        self.host.run_test(
            "/usr/bin/podman exec %s /sbin/ip netns exec %s haproxy -f %s" % (
                OVN_AGENT_CONTAINER, namespace_name,
                haproxy_config_file))
        assert self.host.podman(haproxy_container_name).is_running

        # Now stop agent container and make sure that sidecar container
        # with haproxy is still running
        self.host.run("/usr/bin/systemctl stop %s" %
                      EDPM_OVN_AGENT_SERVICE)
        assert not self.host.podman(OVN_AGENT_CONTAINER).is_running
        assert self.host.podman(haproxy_container_name).is_running

        # Test haproxy-kill script too
        self.host.run("/usr/bin/systemctl start %s" %
                      EDPM_OVN_AGENT_SERVICE)
        assert self.host.podman(OVN_AGENT_CONTAINER).is_running
        self._workaround_sys_mount_permission_problem(
            OVN_AGENT_CONTAINER)
        haproxy_process = self._find_haproxy_process(network_id)
        assert haproxy_process
        self.host.run(
            "/usr/bin/podman exec %s /sbin/ip netns exec %s "
            "/etc/neutron/kill_scripts/haproxy-kill 9 %s" % (
                OVN_AGENT_CONTAINER, namespace_name,
                haproxy_process.pid))
        assert self.host.podman(OVN_AGENT_CONTAINER).is_running
        # NOTE(slaweq): due to the bug
        # https://github.com/pytest-dev/pytest-testinfra/issues/694
        # simple host.podman.get_containers() can't be used and that's
        # why podman command needs to be executed manually
        all_containers = self.host.run(
            "/usr/bin/podman ps --all --format '{{ '{{' }}.Names{{ '}}' }}'"
        ).stdout
        assert haproxy_container_name not in all_containers
