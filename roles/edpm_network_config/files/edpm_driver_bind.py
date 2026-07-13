#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0
#
# Validate and apply edpm_network_config_driver_bind entries: for each
# {name, pci_address, driver} tuple, confirm that "name" really identifies
# "pci_address" (using live sysfs first, falling back to the persisted
# nmstate device_map.yaml when the netdev is no longer present, e.g. it was
# already unbound from the kernel network stack), then bind "driver" at
# "pci_address" via driverctl.
#
# Validation runs for every entry before any binding happens, so a single
# bad entry does not leave earlier entries half-applied.

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import List, Optional

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "PyYAML is required (python3-pyyaml on RHEL-family hosts)."
    ) from exc

SYS_CLASS_NET = os.environ.get("EDPM_TEST_SYS_CLASS_NET", "/sys/class/net")
PCI_DEVICES = os.environ.get("EDPM_TEST_PCI_DEVICES", "/sys/bus/pci/devices")
DRIVERCTL_BIN = os.environ.get("EDPM_TEST_DRIVERCTL_BIN", "driverctl")
CHANGED_MARKER = "edpm_driver_bind_changed="


def _device_dir(sys_class_net: str, name: str) -> str:
    return os.path.join(sys_class_net, name, "device")


def _is_physical_netdev(sys_class_net: str, name: str) -> bool:
    return os.path.isdir(_device_dir(sys_class_net, name))


def _pci_address(sys_class_net: str, name: str) -> Optional[str]:
    try:
        return os.path.basename(os.readlink(_device_dir(sys_class_net, name)))
    except OSError:
        return None


def _driver_for_pci(pci_devices: str, pci_address: str) -> Optional[str]:
    driver_link = os.path.join(pci_devices, pci_address, "driver")
    try:
        return os.path.basename(os.readlink(driver_link))
    except OSError:
        return None


def _load_yaml(path: str) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _validate_schema(interfaces: list) -> List[str]:
    errors = []
    for idx, entry in enumerate(interfaces):
        if not isinstance(entry, dict):
            errors.append(f"interfaces[{idx}] is not a mapping")
            continue
        for key in ("name", "pci_address", "driver"):
            if not entry.get(key):
                errors.append(f"interfaces[{idx}] is missing required key '{key}'")
    return errors


def _validate_entry(entry: dict, sys_class_net: str, device_map: dict) -> Optional[str]:
    name = entry["name"]
    pci_address = entry["pci_address"]

    if _is_physical_netdev(sys_class_net, name):
        live_pci = _pci_address(sys_class_net, name)
        if live_pci and live_pci != pci_address:
            return (
                f"{name}: sysfs reports PCI address {live_pci}, but pci_address "
                f"{pci_address} was declared"
            )
        return None

    devices = device_map.get("devices") or {}
    mapped = devices.get(name)
    if isinstance(mapped, dict) and mapped.get("pci") and mapped["pci"] != pci_address:
        return (
            f"{name}: not present in sysfs, but device_map.yaml records PCI address "
            f"{mapped['pci']}, which does not match declared pci_address {pci_address}"
        )

    # Not in sysfs and either absent from device_map, or device_map agrees:
    # nothing to cross-check against, proceed and trust the declared pci_address.
    return None


def validate_interfaces(interfaces: list, sys_class_net: str, device_map: dict) -> List[str]:
    errors = _validate_schema(interfaces)
    if errors:
        return errors

    for entry in interfaces:
        error = _validate_entry(entry, sys_class_net, device_map)
        if error:
            errors.append(error)
    return errors


def bind_driver(pci_devices: str, pci_address: str, driver: str, driverctl_bin: str) -> bool:
    if _driver_for_pci(pci_devices, pci_address) == driver:
        return False
    subprocess.run(
        [driverctl_bin, "set-override", pci_address, driver],
        check=True,
        capture_output=True,
        text=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and apply edpm_network_config_driver_bind entries"
    )
    parser.add_argument(
        "-f", "--template", required=True, help="YAML file with an 'interfaces' list"
    )
    parser.add_argument(
        "-m", "--map", default="", help="nmstate device_map.yaml path (optional)"
    )
    parser.add_argument(
        "--driverctl", default=DRIVERCTL_BIN, help="driverctl binary to invoke"
    )
    args = parser.parse_args()

    state = _load_yaml(args.template)
    interfaces = state.get("interfaces") or []
    device_map = _load_yaml(args.map) if args.map and os.path.isfile(args.map) else {}

    errors = validate_interfaces(interfaces, SYS_CLASS_NET, device_map)
    if errors:
        lines = "\n".join(f"  - {error}" for error in errors)
        raise SystemExit(
            "edpm_network_config_driver_bind validation failed:\n" + lines
        )

    changed = False
    for entry in interfaces:
        pci_address = entry["pci_address"]
        driver = entry["driver"]
        try:
            if bind_driver(PCI_DEVICES, pci_address, driver, args.driverctl):
                changed = True
                print(f"Bound {pci_address} ({entry.get('name')}) to driver {driver}")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise SystemExit(
                f"driverctl set-override {pci_address} {driver} failed"
                + (f": {stderr}" if stderr else "")
            ) from exc

    print(f"{CHANGED_MARKER}{'yes' if changed else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
