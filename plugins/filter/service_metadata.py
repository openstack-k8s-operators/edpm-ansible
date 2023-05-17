#!/usr/bin/python
#
# Copyright 2020 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def parse_service_metadata(service_metadata, host_fqdn):
    """Extract managed services from a dictionary of metadata

    This filter is useful for parsing server metadata that is loaded on to
    instances and describes the services that instance will host. The metadata
    is written to disk as JSON on the instance, but this filter expects a
    dictionary. You can invoke the filter with the following:

    {{ server_metadata | from_json | parse_service_metadata(host_fqdn) }}

    This filter is useful for dynamically creating service principals in
    FreeIPA for services running on a specific host, which we can later use to
    generate TLS certificates. For example:

    - name: parse metadata for services
      include: register_services.yaml
      loop: {{ metadata | from_json | parse_service_metadata(host_fqdn) }}

    register_services.yaml

    ---
    - name: add sub-host in FreeIPA
      ipa_host:
        fqdn: {{ item.0 }}
        state: present

    - name: add service to FreeIPA
      ipa_service:
        name: "{{ item.1 }}/{{ sub_host }} "
        state: present

    :param service_metadata: is a dictionary where keys are strings that
                             describe the service. The value can be either a
                             list of networks (compact notation) or a string
                             that represents the service and principal (managed
                             notation).
    :param host_fqdn: is a string that represents the fully-qualified hostname
                      of the host we're processing metadata for (e.g.,
                      'controller-0.example.test')
    :returns: a list of tuples where the first element of the tuple is the
              fully-qualified domain name of the service (e.g.,
              'controller-0.external.example.test') and the second element is
              the service (e.g., 'haproxy').
    """
    hostname = host_fqdn.split('.')[0]
    domain = host_fqdn.split('.', 1)[1]
    managed_services = set()
    for service_key in service_metadata.keys():
        if service_key.startswith('managed_service_'):
            principal = service_metadata[service_key]
            service_name, service_hostname = principal.split('/', 2)
            managed_services.add((service_hostname, service_name))
        elif service_key.startswith('compact_service_'):
            interfaces = service_metadata[service_key]
            service_name = service_key.split('_', 2)[-1]
            for interface in interfaces:
                service_hostname = '.'.join([hostname, interface, domain])
                managed_services.add((service_hostname, service_name))

    return list(managed_services)


class FilterModule(object):
    def filters(self):
        return {'parse_service_metadata': parse_service_metadata}
