#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0

import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest

import yaml

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "roles",
        "edpm_network_config",
        "files",
        "edpm_driver_bind.py",
    )
)

FAKE_DRIVERCTL = """#!/usr/bin/env python3
import os
import sys

if len(sys.argv) != 4 or sys.argv[1] != "set-override":
    sys.exit(1)

pci_devices = os.environ["EDPM_TEST_PCI_DEVICES"]
pci_address, driver = sys.argv[2], sys.argv[3]
driver_link = os.path.join(pci_devices, pci_address, "driver")
os.makedirs(os.path.dirname(driver_link), exist_ok=True)
if os.path.islink(driver_link) or os.path.exists(driver_link):
    os.remove(driver_link)
os.symlink(os.path.join("/fake/drivers", driver), driver_link)
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("edpm_driver_bind", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEdpmDriverBind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sys_class_net = os.path.join(self.tmp, "class", "net")
        self.pci_devices = os.path.join(self.tmp, "bus", "pci", "devices")
        os.makedirs(self.sys_class_net)
        os.makedirs(self.pci_devices)

        self.driverctl_path = os.path.join(self.tmp, "fake-driverctl")
        with open(self.driverctl_path, "w", encoding="utf-8") as fh:
            fh.write(FAKE_DRIVERCTL)
        os.chmod(self.driverctl_path, os.stat(self.driverctl_path).st_mode | stat.S_IEXEC)

        os.environ["EDPM_TEST_SYS_CLASS_NET"] = self.sys_class_net
        os.environ["EDPM_TEST_PCI_DEVICES"] = self.pci_devices
        os.environ["EDPM_TEST_DRIVERCTL_BIN"] = self.driverctl_path
        self.mod = _load_module()

    def tearDown(self):
        for key in (
            "EDPM_TEST_SYS_CLASS_NET",
            "EDPM_TEST_PCI_DEVICES",
            "EDPM_TEST_DRIVERCTL_BIN",
        ):
            os.environ.pop(key, None)

    def _mk_physical_netdev(self, name, pci_bdf, driver=None):
        net_dir = os.path.join(self.sys_class_net, name)
        os.makedirs(net_dir)
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        os.symlink(pci_path, os.path.join(net_dir, "device"))
        if driver:
            self._set_pci_driver(pci_bdf, driver)

    def _set_pci_driver(self, pci_bdf, driver):
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        driver_link = os.path.join(pci_path, "driver")
        if os.path.islink(driver_link):
            os.remove(driver_link)
        os.symlink(os.path.join("/fake/drivers", driver), driver_link)

    def _write_device_map(self, devices):
        path = os.path.join(self.tmp, "device_map.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump({"devices": devices}, fh)
        return path

    def _write_template(self, interfaces):
        path = os.path.join(self.tmp, "driver_bind.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump({"interfaces": interfaces}, fh)
        return path

    # -- validation ---------------------------------------------------

    def test_validation_fails_on_sysfs_mismatch(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0")
        errors = self.mod.validate_interfaces(
            [{"name": "eno1", "pci_address": "0000:99:00.0", "driver": "vfio-pci"}],
            self.sys_class_net,
            {},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("eno1", errors[0])
        self.assertIn("sysfs reports", errors[0])

    def test_validation_fails_on_device_map_mismatch(self):
        # "eno1" has already disappeared from sysfs (e.g. unbound already).
        device_map = {"devices": {"eno1": {"pci": "0000:01:00.0"}}}
        errors = self.mod.validate_interfaces(
            [{"name": "eno1", "pci_address": "0000:99:00.0", "driver": "vfio-pci"}],
            self.sys_class_net,
            device_map,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("device_map.yaml records", errors[0])

    def test_validation_passes_when_absent_from_both(self):
        errors = self.mod.validate_interfaces(
            [{"name": "eno1", "pci_address": "0000:99:00.0", "driver": "vfio-pci"}],
            self.sys_class_net,
            {},
        )
        self.assertEqual(errors, [])

    def test_validation_passes_when_device_map_matches(self):
        device_map = {"devices": {"eno1": {"pci": "0000:99:00.0"}}}
        errors = self.mod.validate_interfaces(
            [{"name": "eno1", "pci_address": "0000:99:00.0", "driver": "vfio-pci"}],
            self.sys_class_net,
            device_map,
        )
        self.assertEqual(errors, [])

    def test_validation_reports_missing_schema_keys(self):
        errors = self.mod.validate_interfaces(
            [{"name": "eno1", "driver": "vfio-pci"}], self.sys_class_net, {}
        )
        self.assertTrue(any("pci_address" in e for e in errors))

    # -- binding --------------------------------------------------------

    def test_bind_noop_when_driver_already_set(self):
        self._set_pci_driver("0000:01:00.0", "vfio-pci")
        changed = self.mod.bind_driver(
            self.pci_devices, "0000:01:00.0", "vfio-pci", self.driverctl_path
        )
        self.assertFalse(changed)

    def test_bind_invokes_driverctl_when_driver_differs(self):
        self._set_pci_driver("0000:01:00.0", "ice")
        changed = self.mod.bind_driver(
            self.pci_devices, "0000:01:00.0", "vfio-pci", self.driverctl_path
        )
        self.assertTrue(changed)
        self.assertEqual(
            self.mod._driver_for_pci(self.pci_devices, "0000:01:00.0"), "vfio-pci"
        )

    # -- CLI end-to-end ---------------------------------------------------

    def test_cli_end_to_end_success(self):
        self._set_pci_driver("0000:8a:00.0", "ice")
        template = self._write_template(
            [{"name": "eno12399np0", "pci_address": "0000:8a:00.0", "driver": "vfio-pci"}]
        )
        map_path = self._write_device_map({})

        result = subprocess.run(
            [sys.executable, SCRIPT_PATH, "-f", template, "-m", map_path],
            env=dict(os.environ),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("edpm_driver_bind_changed=yes", result.stdout)
        self.assertEqual(
            self.mod._driver_for_pci(self.pci_devices, "0000:8a:00.0"), "vfio-pci"
        )

    def test_cli_end_to_end_validation_failure(self):
        self._mk_physical_netdev("eno12399np0", "0000:01:00.0")
        template = self._write_template(
            [{"name": "eno12399np0", "pci_address": "0000:8a:00.0", "driver": "vfio-pci"}]
        )

        result = subprocess.run(
            [sys.executable, SCRIPT_PATH, "-f", template],
            env=dict(os.environ),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("validation failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
