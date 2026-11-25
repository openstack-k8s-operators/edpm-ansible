#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0

import importlib.util
import os
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
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        driver_link = os.path.join(pci_path, "driver")
        if os.path.islink(driver_link) or os.path.exists(driver_link):
            os.remove(driver_link)
        drv_path = os.path.join(self.pci_drivers, driver)
        os.makedirs(drv_path, exist_ok=True)
        os.symlink(drv_path, driver_link)

    def _rm_netdev(self, name):
        import shutil

        shutil.rmtree(os.path.join(self.sys_class_net, name))


    def _mk_physical_netdev(self, name, pci_bdf, driver=None, mac=None):
        """A real NIC: netdev/device -> PCI device dir, optionally with a driver symlink."""
        net_dir = os.path.join(self.sys_class_net, name)
        os.makedirs(net_dir)
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        os.symlink(pci_path, os.path.join(net_dir, "device"))
        # Real sysfs: device/subsystem -> ../../bus/pci
        bus_pci = os.path.join(self.tmp, "bus", "pci")
        os.symlink(bus_pci, os.path.join(pci_path, "subsystem"))
        if mac is None:
            mac = "aa:bb:cc:dd:ee:01"
        with open(os.path.join(net_dir, "address"), "w", encoding="utf-8") as fh:
            fh.write(mac + "\n")
        if driver:
            drv_path = os.path.join(self.pci_drivers, driver)
            os.makedirs(drv_path, exist_ok=True)
            os.symlink(drv_path, os.path.join(pci_path, "driver"))

    def _mk_non_pci_physical_netdev(self, name, bus_id, bus="usb", driver=None, mac=None):
        """Bus-backed netdev that is not PCI (e.g. USB NIC)."""
        net_dir = os.path.join(self.sys_class_net, name)
        os.makedirs(net_dir)
        bus_devices = os.path.join(self.tmp, "bus", bus, "devices")
        os.makedirs(bus_devices, exist_ok=True)
        dev_path = os.path.join(bus_devices, bus_id)
        os.makedirs(dev_path, exist_ok=True)
        os.symlink(dev_path, os.path.join(net_dir, "device"))
        os.symlink(
            os.path.join(self.tmp, "bus", bus),
            os.path.join(dev_path, "subsystem"),
        )
        if mac is None:
            mac = "11:22:33:44:55:66"
        with open(os.path.join(net_dir, "address"), "w", encoding="utf-8") as fh:
            fh.write(mac + "\n")
        if driver:
            drv_path = os.path.join(self.tmp, "bus", bus, "drivers", driver)
            os.makedirs(drv_path, exist_ok=True)
            os.symlink(drv_path, os.path.join(dev_path, "driver"))

    def _mk_virtual_netdev(self, name):
        """A virtual netdev (bond/bridge/dummy/vlan/loopback): no "device" entry at all."""
        os.makedirs(os.path.join(self.sys_class_net, name))

    def test_includes_physical_ethernet_device(self):
        self._mk_physical_netdev(
            "eno1", "0000:01:00.0", driver="ice", mac="AA:BB:CC:DD:EE:0F"
        )
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIn("eno1", device_map["devices"])
        self.assertEqual(device_map["devices"]["eno1"]["pci"], "0000:01:00.0")
        self.assertEqual(device_map["devices"]["eno1"]["mac"], "aa:bb:cc:dd:ee:0f")
        self.assertEqual(device_map["devices"]["eno1"]["driver"], "ice")
        self.assertIn("updated", device_map)

    def test_device_without_address_file_has_none_mac(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0", driver="ice")
        os.remove(os.path.join(self.sys_class_net, "eno1", "address"))
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIsNone(device_map["devices"]["eno1"]["mac"])

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

    def test_non_pci_physical_netdev_kept_with_null_pci(self):
        self._mk_non_pci_physical_netdev(
            "enx1234", "1-1:1.0", bus="usb", driver="cdc_ether"
        )
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIn("enx1234", device_map["devices"])
        self.assertIsNone(device_map["devices"]["enx1234"]["pci"])
        self.assertEqual(device_map["devices"]["enx1234"]["mac"], "11:22:33:44:55:66")
        self.assertEqual(device_map["devices"]["enx1234"]["driver"], "cdc_ether")

    def test_device_without_driver_has_none_driver(self):
        self._mk_physical_netdev("eno1", "0000:01:00.0")
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertIsNone(device_map["devices"]["eno1"]["driver"])

    def test_empty_sysfs_yields_empty_map(self):
        device_map = self.mod.build_device_map(self.sys_class_net)
        self.assertEqual(device_map["devices"], {})

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

    def test_retains_previous_entry_when_netdev_gone_but_pci_bound_to_vfio(self):
        # Run N-1 snapshot, then PF handed to vfio-pci (netdev leaves sysfs).
        self._mk_physical_netdev(
            "eno3np2", "0000:19:00.2", driver="i40e", mac="e4:43:4b:5c:96:62"
        )
        previous = self.mod.build_device_map(self.sys_class_net)
        self._rm_netdev("eno3np2")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")

        device_map = self.mod.build_device_map(
            self.sys_class_net, previous=previous, pci_devices=self.pci_devices
        )
        self.assertEqual(
            device_map["devices"]["eno3np2"],
            {
                "pci": "0000:19:00.2",
                "mac": "e4:43:4b:5c:96:62",
                "driver": "vfio-pci",
            },
        )

    def test_drops_previous_entry_when_netdev_gone_and_not_vfio(self):
        self._mk_physical_netdev("eno3np2", "0000:19:00.2", driver="i40e")
        previous = self.mod.build_device_map(self.sys_class_net)
        self._rm_netdev("eno3np2")
        # PCI unbound / rebound to something other than vfio-pci.
        self._set_pci_driver("0000:19:00.2", "i40e")

        device_map = self.mod.build_device_map(
            self.sys_class_net, previous=previous, pci_devices=self.pci_devices
        )
        self.assertNotIn("eno3np2", device_map["devices"])

    def test_drops_previous_name_when_same_pci_visible_under_new_netdev(self):
        self._mk_physical_netdev("eno3np2", "0000:19:00.2", driver="i40e")
        previous = self.mod.build_device_map(self.sys_class_net)
        self._rm_netdev("eno3np2")
        # Same PCI BDF reappears under a new netdev name (rename); do not keep
        # the stale name key even if we somehow still saw vfio on that BDF.
        net_dir = os.path.join(self.sys_class_net, "ens3f2")
        os.makedirs(net_dir)
        os.symlink(
            os.path.join(self.pci_devices, "0000:19:00.2"),
            os.path.join(net_dir, "device"),
        )
        with open(os.path.join(net_dir, "address"), "w", encoding="utf-8") as fh:
            fh.write("e4:43:4b:5c:96:62\n")

        device_map = self.mod.build_device_map(
            self.sys_class_net, previous=previous, pci_devices=self.pci_devices
        )
        self.assertNotIn("eno3np2", device_map["devices"])
        self.assertIn("ens3f2", device_map["devices"])


    def test_cli_retains_vfio_entry_across_refresh(self):
        self._mk_physical_netdev(
            "eno3np2", "0000:19:00.2", driver="i40e", mac="e4:43:4b:5c:96:62"
        )
        out_path = os.path.join(self.tmp, "device_map.yaml")
        env = dict(os.environ)
        subprocess.run(
            [sys.executable, SCRIPT_PATH, "-o", out_path],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        self._rm_netdev("eno3np2")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")
        subprocess.run(
            [sys.executable, SCRIPT_PATH, "-o", out_path],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        device_map = self._load_yaml(out_path)
        self.assertEqual(device_map["devices"]["eno3np2"]["driver"], "vfio-pci")
        self.assertEqual(device_map["devices"]["eno3np2"]["pci"], "0000:19:00.2")

    @staticmethod
    def _load_yaml(path):
        import yaml

        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)



if __name__ == "__main__":
    unittest.main()
