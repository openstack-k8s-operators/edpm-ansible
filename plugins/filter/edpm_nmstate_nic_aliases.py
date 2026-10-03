#!/usr/bin/python
# Copyright 2026 Red Hat, Inc.
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

# Collection filter plugin (plugins/filter/) — same layout as upstream edpm-ansible:
# https://github.com/openstack-k8s-operators/edpm-ansible/tree/main/plugins/filter

"""Substitute NIC aliases only under nmstate keys that reference interface names."""

import re

# nmstate's "refer to a VF by PF name + VF index" pseudo interface name; see
# https://nmstate.io/features/iface_vf_id.html. The <pf_name> segment may itself
# be an EDPM alias (e.g. "sriov:nic3:0") and needs the same substitution as a
# plain interface name.
_SRIOV_VF_REF_RE = re.compile(r"^sriov:(?P<pf_name>.+):(?P<vf_id>\d+)$")


def _resolve_name(name: str, mapping: dict) -> str:
    match = _SRIOV_VF_REF_RE.match(name)
    if match:
        pf_name = match.group("pf_name")
        return "sriov:%s:%s" % (mapping.get(pf_name, pf_name), match.group("vf_id"))
    return mapping.get(name, name)


def _normalize_key(key: str) -> str:
    if not isinstance(key, str):
        return ""
    return key.lower().replace("_", "-")


# Keys whose values (string or list of strings) may be Linux interface names or
# EDPM aliases (nic1, ...) to be resolved. Derived from nmstate YAML usage
# (interfaces, routes, route-rules, bonds, bridges, vlan/macvlan/vxlan, etc.);
# see https://www.nmstate.io/devel/yaml_api.html — extend if new schema keys appear.
_NIC_NAME_KEYS = frozenset(
    {
        # Interface identity & attachment
        "name",
        "device",
        "interface",
        "iface",
        "interface-name",
        "parent",
        "controller",
        "base-iface",
        "copy-mac-from",
        # Bond / bridge / OVS / team ports (also nested under bridge.port, bond.port, …)
        "peer",
        "patch",
        "port",
        "ports",
        # Routes & rules (nmstate routes.config / route-rules.config)
        "next-hop-interface",
        "next-hop-iface",
        "vrf-name",
        "iif",
    }
)


def _is_nic_name_key(key: str) -> bool:
    return _normalize_key(key) in _NIC_NAME_KEYS


# Keys whose values are PCI addresses / DPDK devargs and must stay strings.
# These are BDF-shaped ("0000:19:00.1"), always a single scalar (nmstate's
# dpdk.devargs is one BDF per port; our own driver_bind pci_address is one
# per interface entry - never a list), and, if ever loaded by a YAML parser
# that still applies the legacy base-60 int/float grammar (colon-separated,
# all-digit groups), would silently become a number (see edpm_safe_yaml.py,
# used when rendering these templates, and edpm_driver_bind.py's loader).
# This is belt-and-suspenders for values that reach this filter as
# already-non-string (e.g. built up programmatically) rather than parsed
# from raw YAML text.
_PCI_LIKE_KEYS = frozenset({"pci-address", "devargs"})


def _is_pci_like_key(key: str) -> bool:
    return _normalize_key(key) in _PCI_LIKE_KEYS


def _stringify_pci_like(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return value


def _subst_value(key: str, value, mapping: dict):
    if _is_pci_like_key(key):
        return _stringify_pci_like(value)
    if not _is_nic_name_key(key):
        if isinstance(value, dict):
            return _walk_dict(value, mapping)
        if isinstance(value, list):
            return [_walk_any(item, mapping) for item in value]
        return value
    if isinstance(value, str):
        return _resolve_name(value, mapping)
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                out.append(_resolve_name(item, mapping))
            elif isinstance(item, dict):
                out.append(_walk_dict(item, mapping))
            elif isinstance(item, list):
                out.append(_subst_value(key, item, mapping))
            else:
                out.append(item)
        return out
    if isinstance(value, dict):
        return _walk_dict(value, mapping)
    return value


def _walk_any(node, mapping: dict):
    if isinstance(node, dict):
        return _walk_dict(node, mapping)
    if isinstance(node, list):
        return [_walk_any(item, mapping) for item in node]
    return node


def _walk_dict(node: dict, mapping: dict) -> dict:
    out = {}
    for k, v in node.items():
        out[k] = _subst_value(k, v, mapping)
    return out


class FilterModule:
    def filters(self):
        return {"edpm_substitute_nic_aliases": self.edpm_substitute_nic_aliases}

    def edpm_substitute_nic_aliases(self, data, mapping):
        """Replace alias strings only under known nmstate interface-reference keys.

        Keys are listed in _NIC_NAME_KEYS (nmstate YAML API); unknown keys are only
        recursed, not string-substituted.

        :param data: Parsed nmstate/network_state (dict or list), typically from_yaml.
        :param mapping: dict mapping alias -> interface name (e.g. nic1 -> eth0).
        :returns: New structure with substitutions applied. Always walked (even
            with an empty mapping) since PCI-like fields (see _PCI_LIKE_KEYS)
            are normalized to strings regardless of alias substitution.
        """
        mapping = mapping or {}
        if isinstance(data, dict):
            return _walk_dict(data, mapping)
        if isinstance(data, list):
            return [_walk_any(item, mapping) for item in data]
        return data
