#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0

import importlib.util
import os
import unittest

import yaml

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "filter",
        "edpm_safe_yaml.py",
    )
)


def _load_module():
    spec = importlib.util.spec_from_file_location("edpm_safe_yaml", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEdpmSafeYaml(unittest.TestCase):
    def setUp(self):
        self.mod = _load_module()
        self.filter_fn = self.mod.FilterModule().filters()["edpm_safe_from_yaml"]

    def test_baseline_pyyaml_mangles_pci_looking_scalar(self):
        # Sanity check that the bug this filter guards against is real, so this
        # test fails loudly if a future PyYAML version stops doing this instead
        # of silently making edpm_safe_from_yaml a no-op fix for nothing.
        self.assertEqual(yaml.safe_load("x: 0000:19:00.1")["x"], 1140.1)

    def test_pci_address_like_scalar_stays_a_string(self):
        doc = "interfaces:\n  - name: nic2\n    pci_address: 0000:19:00.1\n"
        result = self.filter_fn(doc)
        self.assertEqual(result["interfaces"][0]["pci_address"], "0000:19:00.1")

    def test_devargs_like_scalar_stays_a_string(self):
        doc = "interfaces:\n  - name: dpdk0\n    dpdk:\n      devargs: 0000:5e:00.1\n"
        result = self.filter_fn(doc)
        self.assertEqual(result["interfaces"][0]["dpdk"]["devargs"], "0000:5e:00.1")

    def test_normal_integers_still_resolve_as_int(self):
        doc = "interfaces:\n  - name: nic3\n    ethernet:\n      sr-iov:\n        total-vfs: 4\n"
        result = self.filter_fn(doc)
        self.assertEqual(
            result["interfaces"][0]["ethernet"]["sr-iov"]["total-vfs"], 4
        )

    def test_normal_floats_still_resolve_as_float(self):
        doc = "x: 3.14\n"
        result = self.filter_fn(doc)
        self.assertEqual(result["x"], 3.14)

    def test_hex_values_still_resolve_as_int(self):
        doc = "pmd-cpu-mask: 0xC\n"
        result = self.filter_fn(doc)
        self.assertEqual(result["pmd-cpu-mask"], 12)

    def test_quoted_pci_address_still_a_string(self):
        doc = 'pci_address: "0000:19:00.1"\n'
        result = self.filter_fn(doc)
        self.assertEqual(result["pci_address"], "0000:19:00.1")

    def test_none_input_returns_none(self):
        self.assertIsNone(self.filter_fn(None))

    def test_matches_plain_interface_name_semantics(self):
        # Non-PCI-shaped values (no all-digit colon groups) should parse the
        # same as with the standard loader.
        doc = "name: eno1np0\n"
        result = self.filter_fn(doc)
        self.assertEqual(result, {"name": "eno1np0"})


if __name__ == "__main__":
    unittest.main()
