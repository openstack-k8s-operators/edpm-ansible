#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0
#
# Build a simple nmstate device_map.yaml: for every physical network device
# (i.e. a netdev backed by a real bus device, such as a PCI ethernet NIC or
# SR-IOV VF) record its name, PCI address (null when not on the PCI bus),
# MAC address, and currently bound kernel driver.
#
# Virtual netdevs (bond, bridge, dummy, vlan, veth, loopback, ...) have no
# "device" symlink in sysfs and are skipped.
#
# Persistence for vfio-pci passthrough: when a prior device_map entry's netdev
# has left /sys/class/net (typical after binding the PF/VF to vfio-pci for
# DPDK/SR-IOV), keep that name -> pci/mac entry if the recorded PCI BDF is
# still bound to vfio-pci and is not already visible under another live
# netdev name. edpm_derived_nic_mapping.py relies on that name key to confirm
# intentional passthrough across runs; a pure live snapshot would drop the
# entry on the first refresh after bind and break alias stability on the
# next derive.

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
    """Return the PCI BDF for a netdev, or None if it is not on the PCI bus.

    Physical non-PCI devices (e.g. USB NICs) still have a ``device`` symlink;
    only record an address in the ``pci`` field when sysfs reports subsystem
    ``pci``.
    """
    device = _device_dir(sys_class_net, name)
    try:
        subsystem = os.path.basename(os.readlink(os.path.join(device, "subsystem")))
    except OSError:
        return None
    if subsystem != "pci":
        return None
    try:
        return os.path.basename(os.readlink(device))
    except OSError:
        return None


def _driver(sys_class_net: str, name: str) -> Optional[str]:
    driver_link = os.path.join(_device_dir(sys_class_net, name), "driver")
    try:
        return os.path.basename(os.readlink(driver_link))
    except OSError:
        return None


def _mac_address(sys_class_net: str, name: str) -> Optional[str]:
    """Read and normalize the permanent/current MAC from sysfs address."""
    address_path = os.path.join(sys_class_net, name, "address")
    try:
        with open(address_path, encoding="utf-8") as fh:
            mac = fh.read().strip().lower()
    except OSError:
        return None
    return mac or None


def _live_driver_for_pci(
    pci_address: Optional[str], pci_devices: Optional[str] = None
) -> Optional[str]:
    if not pci_address:
        return None
    base = pci_devices or PCI_DEVICES
    driver_link = os.path.join(base, pci_address, "driver")
    try:
        return os.path.basename(os.readlink(driver_link))
    except OSError:
        return None


def _load_previous_device_map(path: str) -> dict:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _retain_vfio_passthrough(
    live_devices: dict,
    previous: Optional[dict],
    pci_devices: Optional[str] = None,
) -> dict:
    """Keep prior name keys whose netdev left sysfs but PCI is still vfio-pci.

    Without this, the first refresh after a vfio bind drops the name from
    device_map.yaml and the next edpm_derived_nic_mapping.py run can no longer
    confirm intentional passthrough.
    """
    retained: dict = {}
    prev_devices = (previous or {}).get("devices") or {}
    if not isinstance(prev_devices, dict):
        return retained

    live_pcis = {
        info.get("pci")
        for info in live_devices.values()
        if isinstance(info, dict) and info.get("pci")
    }

    for name, info in prev_devices.items():
        if name in live_devices:
            continue
        if not isinstance(info, dict):
            continue
        pci = info.get("pci")
        if not pci or pci in live_pcis:
            # No BDF to confirm, or the function moved to another live netdev name.
            continue
        if _live_driver_for_pci(pci, pci_devices) != "vfio-pci":
            continue
        retained[name] = {
            "pci": pci,
            "mac": info.get("mac"),
            "driver": "vfio-pci",
        }
    return retained


def build_device_map(
    sys_class_net: Optional[str] = None,
    previous: Optional[dict] = None,
    pci_devices: Optional[str] = None,
) -> dict:
    base = sys_class_net or SYS_CLASS_NET
    devices: dict = {}

    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if not _is_physical_netdev(base, name):
                continue
            devices[name] = {
                "pci": _pci_address(base, name),
                "mac": _mac_address(base, name),
                "driver": _driver(base, name),
            }

    devices.update(_retain_vfio_passthrough(devices, previous, pci_devices))
    return {"devices": devices, "updated": _utc_now()}


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build nmstate device_map.yaml for physical network devices"
    )
    parser.add_argument(
        "-o", "--output", default="", help="Write device_map YAML here (default: stdout)"
    )
    args = parser.parse_args()

    previous = _load_previous_device_map(args.output) if args.output else {}
    device_map = build_device_map(previous=previous)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(_dump_yaml(device_map))
    else:
        sys.stdout.write(_dump_yaml(device_map))

    return 0


if __name__ == "__main__":
    sys.exit(main())
