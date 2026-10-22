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

"""YAML loader for nmstate templates that never mangles PCI-address-like
scalars into numbers.

Ansible's built-in `from_yaml` filter behaves like `yaml.safe_load`, which
implements YAML 1.1's legacy base-60 ("H:MM:SS") int/float auto-conversion:
an unquoted scalar made of all-digit groups joined by colons (optionally with
a decimal fraction) is resolved as a number. A PCI address such as
"0000:19:00.1" matches that grammar exactly and silently becomes the float
1140.1 - which then breaks nmstate's SR-IOV `dpdk.devargs` / bare PCI-address
fields (and anything else shaped like a BDF) unless the template author
remembers to quote it.

edpm_safe_from_yaml is a drop-in replacement for `from_yaml` in the nmstate
render pipeline (edpm_network_config_template,
edpm_network_config_nmstate_sriov_pf_template, ...) that keeps normal
int/float/hex/octal resolution for every other value, but always treats a
colon-containing scalar as a string instead.
"""

import yaml

# String fields (dpdk.devargs, sr-iov vfs pci-address, ...) are the ones this
# guards against, but the loader-level fix applies to every scalar in the
# document - no need to enumerate specific nmstate keys here.


def _string_or_original(base_constructor):
    """Wrap a PyYAML scalar constructor: fall back to the raw string for any
    colon-containing scalar instead of resolving it as int/float.

    Neither the int nor the float grammar ever matches a colon-containing
    scalar except through the legacy base-60 alternative, so seeing ':' here
    means that's what fired - return the original text instead of trusting
    the resolved numeric tag.
    """

    def _construct(loader, node):
        raw = loader.construct_scalar(node)
        if ":" in raw:
            return raw
        return base_constructor(loader, node)

    return _construct


class _EdpmSafeLoader(yaml.SafeLoader):
    """SafeLoader that never turns a colon-containing scalar (e.g. a PCI
    address like "0000:19:00.1") into a number. See _string_or_original.
    """


_EdpmSafeLoader.add_constructor(
    "tag:yaml.org,2002:int",
    _string_or_original(yaml.SafeLoader.construct_yaml_int),
)
_EdpmSafeLoader.add_constructor(
    "tag:yaml.org,2002:float",
    _string_or_original(yaml.SafeLoader.construct_yaml_float),
)


class FilterModule:
    def filters(self):
        return {"edpm_safe_from_yaml": self.edpm_safe_from_yaml}

    def edpm_safe_from_yaml(self, data):
        """Parse a YAML string the same way Ansible's `from_yaml` does,
        except colon-containing scalars are never misread as numbers.

        :param data: YAML document string (e.g. a nmstate template).
        :returns: Parsed structure (dict/list/scalar), or None for empty input.
        """
        if data is None:
            return None
        return yaml.load(data, Loader=_EdpmSafeLoader)
