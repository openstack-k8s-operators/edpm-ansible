#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat, Inc.
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
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os
import time
import uuid
import yaml

import six
from six.moves import http_client
from six.moves.configparser import SafeConfigParser

from gssapi.exceptions import GSSError
from ipalib import api
from ipalib import errors

try:
    from ipapython.ipautil import kinit_keytab
except ImportError:
    # The import moved in freeIPA 4.5.0
    from ipalib.install.kinit import kinit_keytab

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: cleanup_ipa_services

short_description: Cleanup IPA Services and Hosts

version_added: "2.8"

description:
    - When hosts are deleted, delete the hosts, subhosts and services
      associated with the hosts in the FreeIPA server.
    - If the services are managed exclusively by the hosts, then
      delete the subhost for that service and the service itself.
    - If the service is managed by other hosts (not being deleted),
      then simply remove the host(s) being deleted from the managed_by
      attribute.

options:
    keytab:
        description:
            - Keytab to use when authenticating to FreeIPA
        type: str
    hosts:
        description:
            - Hosts to be deleted (list of FQDNs)
        type: list
author:
    - Ade Lee (@vakwetu)
'''

EXAMPLES = '''
- name: Cleanup IPA hosts and services
  cleanup_ipa_services:
      keytab: /etc/krb5.keytab
      hosts:
        - test-server-0.exmaple.com
        - test-server-1.example.com
        - test-server-2.example.com
'''


class IPAClient(object):

    def __init__(self, keytab):
        self.ntries = 5
        self.retry_delay = 2
        self.keytab = keytab

        if self._ipa_client_configured() and not api.isdone('finalize'):
            self.ccache = "MEMORY:" + str(uuid.uuid4())
            os.environ['KRB5CCNAME'] = self.ccache
            (hostname, realm) = self.get_host_and_realm()
            kinit_keytab(str('nova/%s@%s' % (hostname, realm)),
                         self.keytab, self.ccache)
            api.bootstrap(context='cleanup')
            api.finalize()
        else:
            self.ccache = os.environ['KRB5CCNAME']
        self.batch_args = list()

    def split_principal(self, principal):
        """Split a principal into its components. Copied from IPA 4.0.0"""
        service = hostname = realm = None

        # Break down the principal into its component parts, which may or
        # may not include the realm.
        sp = principal.split('/')
        if len(sp) != 2:
            raise errors.MalformedServicePrincipal(reason='missing service')

        service = sp[0]
        if len(service) == 0:
            raise errors.MalformedServicePrincipal(reason='blank service')
        sr = sp[1].split('@')
        if len(sr) > 2:
            raise errors.MalformedServicePrincipal(
                reason='unable to determine realm')

        hostname = sr[0].lower()
        if len(sr) == 2:
            realm = sr[1].upper()
            # At some point we'll support multiple realms
            if realm != api.env.realm:
                raise errors.RealmMismatch()
        else:
            realm = api.env.realm

        # Note that realm may be None.
        return (service, hostname, realm)

    def split_hostname(self, hostname):
        """Split a hostname into its host and domain parts"""
        parts = hostname.split('.')
        domain = six.text_type('.'.join(parts[1:]) + '.')
        return (parts[0], domain)

    def get_host_and_realm(self):
        """Return the hostname and IPA realm name."""
        config = SafeConfigParser()
        config.read('/etc/ipa/default.conf')
        hostname = config.get('global', 'host')
        realm = config.get('global', 'realm')
        return (hostname, realm)

    def __get_connection(self):
        """Make a connection to IPA or raise an error."""
        tries = 0

        while (tries <= self.ntries):
            logging.debug("Attempt %d of %d", tries, self.ntries)
            if api.Backend.rpcclient.isconnected():
                api.Backend.rpcclient.disconnect()
            try:
                api.Backend.rpcclient.connect()
                # ping to force an actual connection in case there is only one
                # IPA master
                api.Command[u'ping']()
            except (errors.CCacheError,
                    errors.TicketExpired,
                    errors.KerberosError) as e:
                tries += 1

                # pylint: disable=no-member
                logging.debug("kinit new ccache in get_connection: %s", e)
                try:
                    kinit_keytab(str('nova/%s@%s' %
                                 (api.env.host, api.env.realm)),
                                 self.keytab,
                                 self.ccache)
                except GSSError as e:
                    logging.debug("kinit failed: %s", e)
            except errors.NetworkError:
                tries += 1
            except http_client.ResponseNotReady:
                # NOTE(xek): This means that the server closed the socket,
                # so keep-alive ended and we can't use that connection.
                api.Backend.rpcclient.disconnect()
                tries += 1
            else:
                # successful connection
                return
            logging.debug("Waiting %s seconds before next retry.",
                          self.retry_delay)
            time.sleep(self.retry_delay)

        logging.error(" Failed to connect to IPA after %d attempts",
                      self.ntries)
        raise Exception("Failed to connect to IPA")

    def start_batch_operation(self):
        """Start a batch operation.

           IPA method calls will be collected in a batch job
           and submitted to IPA once all the operations have collected
           by a call to _flush_batch_operation().
        """
        logging.debug("start batch operation")
        self.batch_args = list()

    def _add_batch_operation(self, command, *args, **kw):
        """Add an IPA call to the batch operation"""
        self.batch_args.append({
            "method": six.text_type(command),
            "params": [args, kw],
        })

    def flush_batch_operation(self):
        """Make an IPA batch call."""
        logging.debug("flush_batch_operation")
        if not self.batch_args:
            return None

        kw = {}
        logging.debug(" %s", self.batch_args)

        return self._call_ipa('batch', *self.batch_args, **kw)

    def _call_ipa(self, command, *args, **kw):
        """Make an IPA call."""
        if not api.Backend.rpcclient.isconnected():
            self.__get_connection()
        if 'version' not in kw:
            kw['version'] = u'2.146'  # IPA v4.2.0 for compatibility

        while True:
            try:
                result = api.Command[command](*args, **kw)
                logging.debug(result)
                return result
            except (errors.CCacheError,
                    errors.TicketExpired,
                    errors.KerberosError):
                logging.debug("Refresh authentication")
                self.__get_connection()
            except errors.NetworkError:
                raise
            except http_client.ResponseNotReady:
                # NOTE(xek): This means that the server closed the socket,
                # so keep-alive ended and we can't use that connection.
                api.Backend.rpcclient.disconnect()
                raise

    def _ipa_client_configured(self):
        """Determine if the machine is an enrolled IPA client.

           Return boolean indicating whether this machine is enrolled
           in IPA. This is a rather weak detection method but better
           than nothing.
        """

        return os.path.exists('/etc/ipa/default.conf')

    def delete_host(self, hostname, batch=True):
        """Delete a host from IPA.

        Servers can have multiple network interfaces, and therefore can
        have multiple aliases.  Moreover, they can part of a service using
        a virtual host (VIP).  These aliases are denoted 'subhosts',
        """
        logging.debug("Deleting subhost: %s", hostname)
        host_params = [hostname]

        (hn, domain) = self.split_hostname(hostname)

        dns_params = [domain, hn]

        # If there is no DNS entry, this operation fails
        host_kw = {'updatedns': False, }

        dns_kw = {'del_all': True, }

        if batch:
            self._add_batch_operation('host_del', *host_params, **host_kw)
            self._add_batch_operation('dnsrecord_del', *dns_params,
                                      **dns_kw)
        else:
            self._call_ipa('host_del', *host_params, **host_kw)
            try:
                self._call_ipa('dnsrecord_del',
                               *dns_params, **dns_kw)
            except (errors.NotFound, errors.ACIError):
                # Ignore DNS deletion errors
                pass

    def host_get_services(self, service_host):
        """Return list of services this host manages"""
        logging.debug("Checking host %s services", service_host)
        params = []
        service_args = {'man_by_host': six.text_type(service_host)}
        result = self._call_ipa('service_find',
                                *params, **service_args)
        return [service['krbprincipalname'][0] for service in result['result']]

    def service_managed_by_other_hosts(self, service_principal,
                                       hosts_to_be_deleted):
        """Return True if hosts other than parent manages this service"""

        logging.debug("Checking if principal %s has hosts", service_principal)
        params = [service_principal]
        service_args = {}
        try:
            result = self._call_ipa('service_show',
                                    *params, **service_args)
        except errors.NotFound:
            raise KeyError
        serviceresult = result['result']

        try:
            (service, hostname, realm) = self.split_principal(
                service_principal
            )
        except errors.MalformedServicePrincipal as e:
            logging.error("Unable to split principal %s: %s",
                          service_principal, e)
            raise

        for candidate in serviceresult.get('managedby_host', []):
            if candidate != hostname:
                if candidate not in hosts_to_be_deleted:
                    return True
        return False

    def find_host(self, hostname):
        """Return True if this host exists"""
        logging.debug("Checking if host %s exists", hostname)
        params = []
        service_args = {'fqdn': six.text_type(hostname)}
        result = self._call_ipa('host_find',
                                *params, **service_args)
        return result['count'] > 0


def cleanup_ipa_services(keytab, hosts):
    ipa = IPAClient(keytab)

    hosts_to_delete = set()
    for host in hosts:
        if six.PY3:
            hostname = host
        else:
            hostname = host.decode('UTF-8')
        if ipa.find_host(hostname):
            hosts_to_delete.add(hostname)

    # get a list of all the services associated with a given hosts
    principals = set()
    for host in hosts_to_delete:
        principals.update(ipa.host_get_services(host))

    # Check the managed_by attribute of each service identified with
    # the given host.  If it is managed by a host other than the
    # parent or the hosts to be deleted, then it is likely a VIP and it
    # is not ready to be removed.
    subhosts_to_delete = set()
    for principal in principals:
        (service, subhost, domain) = ipa.split_principal(principal)
        if ipa.service_managed_by_other_hosts(principal, hosts_to_delete):
            # this service still has other hosts
            continue
        subhosts_to_delete.add(subhost)

    # delete the subhosts.  Referential integrity should take care of the
    # services associated with these hosts.
    ipa.start_batch_operation()
    for host in hosts_to_delete:
        ipa.delete_host(host)
    for subhost in subhosts_to_delete:
        ipa.delete_host(subhost)
    ipa.flush_batch_operation()


def run_module():
    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True,
        **openstack_module_kwargs()
    )

    try:
        keytab = module.params.get('keytab')
        hosts = module.params.get('hosts')

        cleanup_ipa_services(keytab, hosts)

        module.exit_json(changed=True)
    except Exception as err:
        module.fail_json(msg=str(err))


def main():
    run_module()


if __name__ == '__main__':
    main()
