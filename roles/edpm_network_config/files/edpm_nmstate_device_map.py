#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0
#
# Build a simple nmstate device_map.yaml: for every physical network device
# (i.e. a netdev backed by a real bus device, such as a PCI ethernet NIC or
# SR-IOV VF) record its name, PCI address and currently bound kernel driver.
#
# Virtual netdevs (bond, bridge, dummy, vlan, veth, loopback, ...) have no
# "device" symlink in sysfs and are skipped.
#
# This is intentionally minimal: no filtering/skip policy, no persistence
# merge logic. It just answers "what physical devices does this host have,
# and what is their current PCI/driver identity right now?".

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


def build_device_map(sys_class_net: Optional[str] = None) -> dict:
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

    device_map = build_device_map()

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(_dump_yaml(device_map))
    else:
        sys.stdout.write(_dump_yaml(device_map))

    return 0


if __name__ == "__main__":
    sys.exit(main())
