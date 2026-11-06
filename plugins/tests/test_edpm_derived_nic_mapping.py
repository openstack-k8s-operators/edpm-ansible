#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0

import importlib.util
import os
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
        "edpm_derived_nic_mapping.py",
    )
)


def _load_module():
    spec = importlib.util.spec_from_file_location("edpm_derived_nic_mapping", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEdpmDerivedNicMapping(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sys_class_net = os.path.join(self.tmp, "class", "net")
        self.pci_devices = os.path.join(self.tmp, "bus", "pci", "devices")
        os.makedirs(self.sys_class_net)
        os.makedirs(self.pci_devices)
        os.environ["EDPM_TEST_SYS_CLASS_NET"] = self.sys_class_net
        os.environ["EDPM_TEST_PCI_DEVICES"] = self.pci_devices
        self.mod = _load_module()

    def tearDown(self):
        os.environ.pop("EDPM_TEST_SYS_CLASS_NET", None)
        os.environ.pop("EDPM_TEST_PCI_DEVICES", None)

    def _mk_nic(self, name, mac, up=True, vf_of=None):
        d = os.path.join(self.sys_class_net, name)
        os.makedirs(os.path.join(d, "device"), exist_ok=True)
        with open(os.path.join(d, "address"), "w", encoding="utf-8") as fh:
            fh.write(mac + "\n")
        with open(os.path.join(d, "operstate"), "w", encoding="utf-8") as fh:
            fh.write(("up" if up else "down") + "\n")
        if vf_of:
            # physfn lives under device/, not directly under the net class dir.
            os.makedirs(os.path.join(d, "device", "physfn"), exist_ok=True)

    def _set_pci_driver(self, pci_bdf, driver):
        pci_path = os.path.join(self.pci_devices, pci_bdf)
        os.makedirs(pci_path, exist_ok=True)
        driver_link = os.path.join(pci_path, "driver")
        if os.path.islink(driver_link):
            os.remove(driver_link)
        os.symlink(os.path.join("/fake/drivers", driver), driver_link)

    def _derive(self, user, previous=None, device_map=None, previous_auto=None):
        return self.mod.derive_nic_mapping(
            user, previous or {}, device_map or {}, previous_auto
        )

    # -- basic resolution --------------------------------------------------

    def test_resolves_user_mapping_by_name(self):
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        result, auto = self._derive({"nic1": "eno1np0"})
        self.assertEqual(result["nic1"], "eno1np0")
        self.assertEqual(auto, [])

    def test_resolves_user_mapping_by_mac(self):
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        result, _ = self._derive({"nic1": "e4:43:4b:5c:96:60"})
        self.assertEqual(result["nic1"], "eno1np0")

    def test_fails_user_mapping_when_unavailable_and_not_passthrough(self):
        # device_map has other devices but not this NIC, and it is not in sysfs:
        # typo / removed hardware (not bootstrap — map already exists).
        self._mk_nic("eno2np1", "e4:43:4b:5c:96:61")
        device_map = {
            "devices": {"eno2np1": {"pci": "0000:19:00.1", "driver": "i40e"}}
        }
        with self.assertRaises(ValueError) as ctx:
            self._derive({"nic1": "eno1np0"}, device_map=device_map)
        self.assertIn("unresolved NIC mapping", str(ctx.exception))

    def test_fails_user_mapped_absent_nic_when_device_map_empty(self):
        # Empty device_map: cannot confirm vfio-pci. Do not trust an operator
        # name that is absent from sysfs (typos must fail).
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        with self.assertRaises(ValueError) as ctx:
            self._derive(
                {"nic1": "eno1np0", "nic3": "eno3np2"},
                device_map={},
            )
        self.assertIn("unresolved NIC mapping", str(ctx.exception))
        self.assertIn("nic3=eno3np2", str(ctx.exception))

    def test_auto_numbers_unmapped_active_nics(self):
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        result, auto = self._derive({})
        self.assertEqual(result.get("nic1"), "eno1np0")
        self.assertEqual(auto, ["nic1"])

    def test_vf_by_name_excluded_from_auto_numbering(self):
        self._mk_nic("eno3np2", "e4:43:4b:5c:96:62")
        self._mk_nic("eno3v1", "a6:9a:2a:59:50:d1", vf_of="eno3np2")
        result, _ = self._derive({})
        self.assertIn("eno3np2", result.values())
        self.assertNotIn("eno3v1", result.values())

    # -- vfio-pci passthrough stability -----------------------------------

    def test_retains_user_mapped_alias_when_target_bound_to_vfio_pci(self):
        # eno3np2 (nic3) was configured on a prior run; it has since been handed
        # to vfio-pci (e.g. edpm_network_config_driver_bind) and is gone from
        # sysfs. The user's vars file still says nic3: eno3np2 verbatim.
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")
        device_map = {"devices": {"eno3np2": {"pci": "0000:19:00.2", "driver": "i40e"}}}
        user_mapping = {"nic1": "eno1np0", "nic3": "eno3np2"}
        result, auto = self._derive(user_mapping, device_map=device_map)
        self.assertEqual(result["nic3"], "eno3np2")
        self.assertEqual(result["nic1"], "eno1np0")
        self.assertEqual(auto, [])

    def test_retains_user_mapped_alias_by_mac_when_target_bound_to_vfio_pci(self):
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")
        device_map = {
            "devices": {
                "eno3np2": {
                    "pci": "0000:19:00.2",
                    "mac": "e4:43:4b:5c:96:62",
                    "driver": "vfio-pci",
                }
            }
        }
        result, _ = self._derive(
            {"nic1": "eno1np0", "nic3": "e4:43:4b:5c:96:62"},
            device_map=device_map,
        )
        self.assertEqual(result["nic3"], "eno3np2")

    def test_retains_previously_auto_derived_alias_when_target_bound_to_vfio_pci(self):
        # nic5 was auto-derived on a prior run (not in the operator's mapping);
        # its target has since been passed through to vfio-pci.
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._set_pci_driver("0000:19:0a.1", "vfio-pci")
        device_map = {"devices": {"eno3v1": {"pci": "0000:19:0a.1", "driver": "iavf"}}}
        previous_mapping = {"nic1": "eno1np0", "nic5": "eno3v1"}
        result, auto = self._derive(
            {"nic1": "eno1np0"},
            previous=previous_mapping,
            device_map=device_map,
            previous_auto=["nic5"],
        )
        self.assertEqual(result["nic5"], "eno3v1")
        self.assertEqual(auto, ["nic5"])

    def test_does_not_retain_previous_user_alias_removed_from_operator_mapping(self):
        # Operator had nic3 last run; removed it from vars. Even though eno3np2
        # is still up, previous_mapping must not revive nic3 (it was not auto).
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._mk_nic("eno3np2", "e4:43:4b:5c:96:62")
        previous_mapping = {"nic1": "eno1np0", "nic3": "eno3np2"}
        result, auto = self._derive(
            {"nic1": "eno1np0"},
            previous=previous_mapping,
            previous_auto=[],  # nic3 was operator-specified, not auto
        )
        self.assertNotIn("nic3", result)
        # eno3np2 is still active and unmapped -> may be auto-numbered.
        self.assertIn("eno3np2", result.values())
        self.assertTrue(auto)

    def test_does_not_retain_previous_user_passthrough_alias_after_operator_removal(self):
        # Operator removed nic3 while the NIC is on vfio-pci: must not stick via
        # previous_mapping (only auto_aliases are retained that way).
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")
        device_map = {"devices": {"eno3np2": {"pci": "0000:19:00.2", "driver": "i40e"}}}
        result, _ = self._derive(
            {"nic1": "eno1np0"},
            previous={"nic1": "eno1np0", "nic3": "eno3np2"},
            device_map=device_map,
            previous_auto=[],
        )
        self.assertNotIn("nic3", result)

    def test_does_not_retain_alias_when_target_gone_and_not_passthrough(self):
        # eno3np2 vanished from sysfs but device_map has no record of it (or it
        # is not vfio-pci-bound): no evidence of intentional passthrough, so
        # don't manufacture a stale mapping -- let it drop like before.
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        previous_mapping = {"nic1": "eno1np0", "nic3": "eno3np2"}
        result, _ = self._derive(
            {"nic1": "eno1np0"},
            previous=previous_mapping,
            previous_auto=["nic3"],
        )
        self.assertNotIn("nic3", result)

    def test_other_aliases_unaffected_by_one_passthrough_device(self):
        # The crux of the reported bug: nic3's target going to vfio-pci must not
        # reshuffle nic4's (or any other alias's) number.
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._mk_nic("eno2np1", "e4:43:4b:5c:96:61")
        self._mk_nic("eno4np3", "e4:43:4b:5c:96:63")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")
        device_map = {"devices": {"eno3np2": {"pci": "0000:19:00.2", "driver": "i40e"}}}
        user_mapping = {
            "nic1": "eno1np0",
            "nic2": "eno2np1",
            "nic3": "eno3np2",
            "nic4": "eno4np3",
        }
        result, _ = self._derive(user_mapping, previous=user_mapping, device_map=device_map)
        self.assertEqual(
            result,
            {
                "nic1": "eno1np0",
                "nic2": "eno2np1",
                "nic3": "eno3np2",
                "nic4": "eno4np3",
            },
        )

    def test_passthrough_stable_after_device_map_refresh_retains_vfio_entry(self):
        # Simulate run N+1: device_map refresh already rewrote driver to vfio-pci
        # and kept the name key even though the netdev is gone from sysfs.
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._set_pci_driver("0000:19:00.2", "vfio-pci")
        device_map = {
            "devices": {
                "eno3np2": {
                    "pci": "0000:19:00.2",
                    "mac": "e4:43:4b:5c:96:62",
                    "driver": "vfio-pci",
                }
            }
        }
        result, _ = self._derive(
            {"nic1": "eno1np0", "nic3": "eno3np2"}, device_map=device_map
        )
        self.assertEqual(result["nic3"], "eno3np2")

    def test_auto_numbering_skips_alias_held_by_retained_passthrough(self):
        # Retained auto nic2 (vfio) must not leave the next active NIC unmapped.
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._mk_nic("eno3np2", "e4:43:4b:5c:96:62")
        self._set_pci_driver("0000:19:00.1", "vfio-pci")
        device_map = {"devices": {"eno2np1": {"pci": "0000:19:00.1", "driver": "i40e"}}}
        result, auto = self._derive(
            {"nic1": "eno1np0"},
            previous={"nic1": "eno1np0", "nic2": "eno2np1"},
            device_map=device_map,
            previous_auto=["nic2"],
        )
        self.assertEqual(result["nic2"], "eno2np1")
        self.assertEqual(result["nic3"], "eno3np2")
        self.assertIn("nic3", auto)

    def test_auto_numbering_is_stable_when_preferred_slots_collide(self):
        # Operator maps nic1 to the 3rd NIC; leftovers must take free aliases in
        # active_nics order (not hash-randomized set order).
        self._mk_nic("eno1np0", "e4:43:4b:5c:96:60")
        self._mk_nic("eno2np1", "e4:43:4b:5c:96:61")
        self._mk_nic("eno3np2", "e4:43:4b:5c:96:62")
        result, auto = self._derive({"nic1": "eno3np2"})
        self.assertEqual(
            result, {"nic1": "eno3np2", "nic2": "eno1np0", "nic3": "eno2np1"}
        )
        self.assertEqual(auto, ["nic2", "nic3"])

    def test_user_mapping_takes_priority_over_previous_mapping(self):
        # Operator changed the vars file (nic3 now points elsewhere); the fresh
        # user mapping must win even though a previous_mapping entry exists.
        self._mk_nic("eno3np2", "e4:43:4b:5c:96:62")
        self._mk_nic("eno4np3", "e4:43:4b:5c:96:63")
        previous_mapping = {"nic3": "eno3np2"}
        result, _ = self._derive(
            {"nic3": "eno4np3"}, previous=previous_mapping, previous_auto=["nic3"]
        )
        self.assertEqual(result["nic3"], "eno4np3")

    # -- yaml IO helpers ----------------------------------------------------

    def test_load_device_map_returns_empty_for_missing_file(self):
        self.assertEqual(
            self.mod.load_device_map(os.path.join(self.tmp, "missing.yaml")), {}
        )

    def test_save_and_reload_round_trip_with_auto_aliases(self):
        path = os.path.join(self.tmp, "derived_nic_mapping.yaml")
        wrote = self.mod.save_yaml(path, {"nic1": "eno1np0", "nic2": "eno2"}, ["nic2"])
        self.assertTrue(wrote)
        self.assertEqual(
            self.mod.load_yaml(path), {"nic1": "eno1np0", "nic2": "eno2"}
        )
        mapping, auto = self.mod.load_derived_state(path)
        self.assertEqual(mapping, {"nic1": "eno1np0", "nic2": "eno2"})
        self.assertEqual(auto, {"nic2"})
        # Re-saving the same mapping+auto is a no-op (changed_when in Ansible).
        wrote_again = self.mod.save_yaml(
            path, {"nic1": "eno1np0", "nic2": "eno2"}, ["nic2"]
        )
        self.assertFalse(wrote_again)

    def test_missing_or_empty_auto_aliases_are_not_retention_eligible(self):
        # Fresh / no-autos: missing key and explicit [] both yield empty
        # previous_auto — prior interface_mapping keys are not revived.
        import yaml

        for name, payload in (
            (
                "missing_auto.yaml",
                {"interface_mapping": {"nic1": "eno1np0", "nic5": "eno3v1"}},
            ),
            (
                "empty_auto.yaml",
                {
                    "interface_mapping": {"nic1": "eno1np0", "nic5": "eno3v1"},
                    "auto_aliases": [],
                },
            ),
        ):
            path = os.path.join(self.tmp, name)
            with open(path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(payload, fh)
            mapping, auto = self.mod.load_derived_state(path)
            self.assertEqual(mapping, {"nic1": "eno1np0", "nic5": "eno3v1"})
            self.assertEqual(auto, set())


if __name__ == "__main__":
    unittest.main()
