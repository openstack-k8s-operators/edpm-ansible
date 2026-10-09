#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "roles",
        "edpm_network_config",
        "files",
        "edpm_nmstate_device_map.py",
    )
)


def _load_module():
    spec = importlib.util.spec_from_file_location("edpm_nmstate_device_map", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestNmstateDeviceMap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sys_class_net = os.path.join(self.tmp, "class", "net")
        self.pci_devices = os.path.join(self.tmp, "bus", "pci", "devices")
        self.pci_drivers = os.path.join(self.tmp, "bus", "pci", "drivers")
        os.makedirs(self.sys_class_net)
        os.makedirs(self.pci_devices)
        os.makedirs(self.pci_drivers)
        os.environ["EDPM_TEST_SYS_CLASS_NET"] = self.sys_class_net
        os.environ["EDPM_TEST_PCI_DEVICES"] = self.pci_devices
        self.mod = _load_module()

    def tearDown(self):
        os.environ.pop("EDPM_TEST_SYS_CLASS_NET", None)
        os.environ.pop("EDPM_TEST_PCI_DEVICES", None)

    def _set_pci_driver(self, pci_bdf, driver):
        """Bind a PCI address to a driver directly (no netdev), e.g. vfio-pci."""
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        driver_link = os.path.join(pci_path, "driver")
        if os.path.islink(driver_link):
            os.remove(driver_link)
        os.symlink(os.path.join("/fake/drivers", driver), driver_link)

    def _mk_physical_netdev(self, name, pci_bdf, driver=None):
        """A real NIC: netdev/device -> PCI device dir, optionally with a driver symlink."""
        net_dir = os.path.join(self.sys_class_net, name)
        os.makedirs(net_dir)
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        os.symlink(pci_path, os.path.join(net_dir, "device"))
        if driver:
            drv_path = os.path.join(self.pci_drivers, driver)
            os.makedirs(drv_path, exist_ok=True)
            os.symlink(drv_path, os.path.join(pci_path, "driver"))

    def _mk_virtual_netdev(self, name):
        """A virtual netdev (bond/bridge/dummy/vlan/loopback): no "device" entry at all."""
        os.makedirs(os.path.join(self.sys_class_net, name))

    def test_includes_physical_ethernet_device(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0", driver="ice")
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIn("eno1", device_map["devices"])
        self.assertEqual(device_map["devices"]["eno1"]["pci"], "0000:01:00.0")
        self.assertEqual(device_map["devices"]["eno1"]["driver"], "ice")
        self.assertIn("updated", device_map)

    def test_includes_sriov_vf_as_physical(self):
        # VFs are also backed by a real PCI device/driver (e.g. iavf).
        self._mk_physical_netdev("eno1v0", "0000:01:00.1", driver="iavf")
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIn("eno1v0", device_map["devices"])
        self.assertEqual(device_map["devices"]["eno1v0"]["driver"], "iavf")

    def test_excludes_virtual_devices(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0", driver="ice")
        for name in ("bond0", "br-ex", "dummy0", "lo", "eno1.100", "veth0"):
            self._mk_virtual_netdev(name)

        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertEqual(list(device_map["devices"]), ["eno1"])

    def test_device_without_driver_has_none_driver(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0")
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIsNone(device_map["devices"]["eno1"]["driver"])

    def test_empty_sysfs_yields_empty_map(self):
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertEqual(device_map["devices"], {})

    # -- retention of devices handed to vfio-pci ---------------------------

    def test_device_no_longer_a_netdev_is_retained_from_existing_map(self):
        # eno4 was a physical netdev on a previous run (recorded in "existing");
        # it has since been handed to vfio-pci and is no longer a netdev at all.
        existing = {"devices": {"eno4": {"pci": "0000:19:00.3", "driver": "i40e"}}}
        self._set_pci_driver("0000:19:00.3", "vfio-pci")

        device_map = self.mod.build_device_map(self.sys_class_net, existing=existing)

        self.assertIn("eno4", device_map["devices"])
        self.assertEqual(device_map["devices"]["eno4"]["pci"], "0000:19:00.3")
        # Driver field is opportunistically refreshed via a live PCI lookup.
        self.assertEqual(device_map["devices"]["eno4"]["driver"], "vfio-pci")

    def test_retained_driver_falls_back_to_stale_value_when_pci_gone(self):
        existing = {"devices": {"eno4": {"pci": "0000:19:00.3", "driver": "i40e"}}}
        # No live PCI entry at all (e.g. device physically removed): keep old value.
        device_map = self.mod.build_device_map(self.sys_class_net, existing=existing)
        self.assertEqual(device_map["devices"]["eno4"]["driver"], "i40e")

    def test_current_netdev_state_wins_over_existing_map(self):
        # eno1 is present as a real netdev right now: use the fresh scan, not
        # whatever was recorded previously.
        self._mk_physical_netdev("eno1", "0000:01:00.0", driver="ice")
        existing = {"devices": {"eno1": {"pci": "0000:99:99.9", "driver": "stale"}}}
        device_map = self.mod.build_device_map(self.sys_class_net, existing=existing)
        self.assertEqual(device_map["devices"]["eno1"]["pci"], "0000:01:00.0")
        self.assertEqual(device_map["devices"]["eno1"]["driver"], "ice")

    def test_cli_retains_stale_entry_across_two_invocations(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0", driver="ice")
        self._mk_physical_netdev("eno4", "0000:19:00.3", driver="i40e")
        out_path = os.path.join(self.tmp, "device_map.yaml")
        env = dict(os.environ)

        subprocess.run(
            [sys.executable, SCRIPT_PATH, "-o", out_path],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        first = self._load_yaml(out_path)
        self.assertIn("eno4", first["devices"])

        # eno4 is now handed to vfio-pci: remove the netdev, rebind the PCI addr.
        shutil.rmtree(os.path.join(self.sys_class_net, "eno4"))
        self._set_pci_driver("0000:19:00.3", "vfio-pci")

        subprocess.run(
            [sys.executable, SCRIPT_PATH, "-o", out_path],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        second = self._load_yaml(out_path)
        self.assertIn("eno4", second["devices"])
        self.assertEqual(second["devices"]["eno4"]["pci"], "0000:19:00.3")
        self.assertEqual(second["devices"]["eno4"]["driver"], "vfio-pci")
        self.assertIn("eno1", second["devices"])

    def test_cli_writes_yaml_file(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0", driver="ice")
        self._mk_virtual_netdev("dummy0")
        out_path = os.path.join(self.tmp, "device_map.yaml")

        env = dict(os.environ)
        subprocess.run(
            [sys.executable, SCRIPT_PATH, "-o", out_path],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        device_map = self._load_yaml(out_path)
        self.assertIn("eno1", device_map["devices"])
        self.assertNotIn("dummy0", device_map["devices"])

    @staticmethod
    def _load_yaml(path):
        import yaml

        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)


if __name__ == "__main__":
    unittest.main()
