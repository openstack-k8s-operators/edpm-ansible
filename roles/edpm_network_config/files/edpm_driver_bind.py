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

# String fields that must never come out of YAML loading as anything other
# than str (see _NoSexagesimalLoader below for why this can otherwise happen).
_STRING_FIELDS = ("name", "pci_address", "driver")


def _string_or_original(base_constructor):
    """Wrap a PyYAML scalar constructor so that colon-containing values fall
    back to a plain string instead of being resolved as int/float.

    YAML 1.1 (which PyYAML implements) auto-converts unquoted scalars like
    "0000:19:00.1" into numbers via a legacy base-60 ("H:MM:SS") notation:
    all-digit groups joined by colons, optionally with a decimal fraction,
    resolve to tag:yaml.org,2002:int or :float. A PCI address such as
    "0000:19:00.1" matches that pattern exactly and silently becomes the
    float 1140.1. Neither the int nor the float grammar ever matches a
    colon-containing scalar any other way, so if the raw text contains ':'
    here, it can only be that legacy notation kicking in - return the
    original string instead of trusting the resolved numeric tag.
    """

    def _construct(loader, node):
        raw = loader.construct_scalar(node)
        if ":" in raw:
            return raw
        return base_constructor(loader, node)

    return _construct


class _NoSexagesimalLoader(yaml.SafeLoader):
    """SafeLoader that never turns a colon-containing scalar (e.g. a PCI
    address like "0000:19:00.1") into a number. See _string_or_original.
    """


_NoSexagesimalLoader.add_constructor(
    "tag:yaml.org,2002:int",
    _string_or_original(yaml.SafeLoader.construct_yaml_int),
)
_NoSexagesimalLoader.add_constructor(
    "tag:yaml.org,2002:float",
    _string_or_original(yaml.SafeLoader.construct_yaml_float),
)


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
        data = yaml.load(fh, Loader=_NoSexagesimalLoader)  # noqa: S506
    return data if isinstance(data, dict) else {}


def _normalize_interfaces(interfaces: list) -> list:
    """Force name/pci_address/driver to str(), in case some other unforeseen
    path (not just plain-unquoted PCI addresses, which _NoSexagesimalLoader
    already handles) hands us a non-string, e.g. an int/float/bool from a
    YAML anchor or a caller that builds this file programmatically. Belt and
    suspenders: fail validation with a clear message rather than crashing
    with a TypeError deep inside os.path.join().
    """
    normalized = []
    for entry in interfaces:
        if isinstance(entry, dict):
            entry = {
                key: (
                    str(value)
                    if key in _STRING_FIELDS and value is not None
                    else value
                )
                for key, value in entry.items()
            }
        normalized.append(entry)
    return normalized


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
    interfaces = _normalize_interfaces(state.get("interfaces") or [])
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
