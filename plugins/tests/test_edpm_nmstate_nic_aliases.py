#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0

import importlib.util
import os
import unittest

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "filter",
        "edpm_nmstate_nic_aliases.py",
    )
)


def _load_module():
    spec = importlib.util.spec_from_file_location("edpm_nmstate_nic_aliases", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEdpmNmstateNicAliases(unittest.TestCase):
    def setUp(self):
        self.mod = _load_module()
        self.mapping = {"nic1": "eno1np0", "nic3": "eno3np2"}
        self.filter_fn = self.mod.FilterModule().filters()["edpm_substitute_nic_aliases"]

    def test_substitutes_plain_interface_name(self):
        data = {"interfaces": [{"name": "nic1"}]}
        result = self.filter_fn(data, self.mapping)
        self.assertEqual(result["interfaces"][0]["name"], "eno1np0")

    def test_substitutes_sriov_pf_vf_reference(self):
        # nmstate's "sriov:<pf_name>:<vf_id>" pseudo interface name (used e.g. as a
        # bond port referring to a specific VF of an SR-IOV PF) must have its
        # <pf_name> segment resolved the same as a plain interface name.
        data = {
            "interfaces": [
                {
                    "name": "bond-sriov0",
                    "link-aggregation": {"port": ["sriov:nic3:0", "sriov:nic1:1"]},
                }
            ]
        }
        result = self.filter_fn(data, self.mapping)
        ports = result["interfaces"][0]["link-aggregation"]["port"]
        self.assertEqual(ports, ["sriov:eno3np2:0", "sriov:eno1np0:1"])

    def test_sriov_reference_with_unmapped_pf_name_is_left_unchanged(self):
        data = {"interfaces": [{"name": "b", "port": ["sriov:eno9np0:2"]}]}
        result = self.filter_fn(data, self.mapping)
        self.assertEqual(result["interfaces"][0]["port"], ["sriov:eno9np0:2"])

    def test_non_nic_keys_are_not_substituted(self):
        data = {"interfaces": [{"name": "nic1", "description": "nic1"}]}
        result = self.filter_fn(data, self.mapping)
        self.assertEqual(result["interfaces"][0]["description"], "nic1")

    def test_empty_mapping_returns_data_unchanged(self):
        data = {"interfaces": [{"name": "nic1", "port": ["sriov:nic1:0"]}]}
        result = self.filter_fn(data, {})
        self.assertEqual(result, data)


if __name__ == "__main__":
    unittest.main()
