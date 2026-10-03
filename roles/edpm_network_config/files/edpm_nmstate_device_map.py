#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0
#
# Build/refresh a device_map.yaml: for every physical network device (i.e. a
# netdev backed by a real bus device, such as a PCI ethernet NIC or SR-IOV VF)
# record its name, PCI address and currently bound kernel driver.
#
# Virtual netdevs (bond, bridge, dummy, vlan, veth, loopback, ...) have no
# "device" symlink in sysfs and are skipped.
#
# The output is merged with any previous map at the same path. A device that
# was previously recorded but is no longer a netdev (e.g. handed to vfio-pci
# by edpm_network_config_driver_bind or an external tool) is RETAINED when its
# PCI address still exists under /sys/bus/pci/devices. That keeps the name/PCI
# identity available for edpm_driver_bind.py's device_map cross-check (and for
# derived NIC mapping) after the netdev disappears. Entries whose PCI device
# is also gone are dropped. The retained "driver" field is refreshed via a
# live PCI lookup when possible so it does not stay stuck at its
# pre-passthrough value.

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "PyYAML is required (python3-pyyaml on RHEL-family hosts)."
    ) from exc

SYS_CLASS_NET = os.environ.get("EDPM_TEST_SYS_CLASS_NET", "/sys/class/net")
PCI_DEVICES = os.environ.get("EDPM_TEST_PCI_DEVICES", "/sys/bus/pci/devices")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _device_dir(sys_class_net: str, name: str) -> str:
    return os.path.join(sys_class_net, name, "device")


def _is_physical_netdev(sys_class_net: str, name: str) -> bool:
    return os.path.isdir(_device_dir(sys_class_net, name))


def _pci_address(sys_class_net: str, name: str) -> Optional[str]:
    try:
        return os.path.basename(os.readlink(_device_dir(sys_class_net, name)))
    except OSError:
        return None


def _driver(sys_class_net: str, name: str) -> Optional[str]:
    driver_link = os.path.join(_device_dir(sys_class_net, name), "driver")
    try:
        return os.path.basename(os.readlink(driver_link))
    except OSError:
        return None


def _pci_device_exists(pci_address: Optional[str]) -> bool:
    if not pci_address:
        return False
    return os.path.isdir(os.path.join(PCI_DEVICES, pci_address))


def _live_driver_for_pci(pci_address: Optional[str]) -> Optional[str]:
    if not pci_address:
        return None
    driver_link = os.path.join(PCI_DEVICES, pci_address, "driver")
    try:
        return os.path.basename(os.readlink(driver_link))
    except OSError:
        return None


def build_device_map(
    sys_class_net: Optional[str] = None, existing: Optional[dict] = None
) -> dict:
    base = sys_class_net or SYS_CLASS_NET
    devices: dict = {}

    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if not _is_physical_netdev(base, name):
                continue
            devices[name] = {
                "pci": _pci_address(base, name),
                "driver": _driver(base, name),
            }

    # Merge previous entries whose netdev is gone but whose PCI device still
    # exists (see module docstring). Live netdev state always wins on name clash.
    for name, info in ((existing or {}).get("devices") or {}).items():
        if name in devices or not isinstance(info, dict):
            continue
        pci = info.get("pci")
        if not _pci_device_exists(pci):
            continue
        devices[name] = {
            "pci": pci,
            "driver": _live_driver_for_pci(pci) or info.get("driver"),
        }

    return {"devices": devices, "updated": _utc_now()}


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)


def _load_existing(path: str) -> dict:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except OSError:
        return {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build/refresh nmstate device_map.yaml for physical network devices"
    )
    parser.add_argument(
        "-o", "--output", default="", help="Write device_map YAML here (default: stdout)"
    )
    args = parser.parse_args()

    existing = _load_existing(args.output)
    device_map = build_device_map(existing=existing)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(_dump_yaml(device_map))
    else:
        sys.stdout.write(_dump_yaml(device_map))

    return 0


if __name__ == "__main__":
    sys.exit(main())
