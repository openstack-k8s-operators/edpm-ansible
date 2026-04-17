#!/usr/bin/env python3
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0
#
# EDPM-only NIC alias -> Linux interface name resolution. No dependency on
# os-net-config: mapping logic lives entirely in this module.
#
# Reads and writes /var/lib/edpm-config/derived_nic_mapping.yaml by default
# (same as role var edpm_network_config_derived_nic_mapping_file; override with -f).
# YAML shape:
#   interface_mapping:
#     nic1: <MAC or interface name>
#     nic2: ...
#
# After a run, values are resolved to Linux interface names; unmapped active
# interfaces get nic1, nic2, ... per embedded-first then natural sort ordering.
# Kernel dummy interfaces (dummy0, …) are included for Molecule/lab; they have no
# PCI device/ in sysfs — see _is_available_nic.

import argparse
import glob
import logging
import os
import re
import sys
from typing import Dict, List, Optional

LOG = logging.getLogger(__name__)

DEFAULT_PATH = "/var/lib/edpm-config/derived_nic_mapping.yaml"
SYS_CLASS_NET = "/sys/class/net"


def _natural_sort_key(s):
    nsre = re.compile(r"([0-9]+)")
    return [int(text) if text.isdigit() else text for text in re.split(nsre, s)]


def _normalize_mac(s: str) -> Optional[str]:
    """Canonical aa:bb:cc:dd:ee:ff (lowercase) or None if not 12 hex digits."""
    if not s:
        return None
    hex_only = re.sub(r"[^0-9A-Fa-f]", "", s.strip())
    if len(hex_only) != 12:
        return None
    return ":".join(hex_only[i : i + 2].lower() for i in range(0, 12, 2))


def _is_embedded_nic(nic: str) -> bool:
    return nic.startswith(("em", "eno", "eth"))


def _is_kernel_dummy(interface_name: str) -> bool:
    """True for Linux dummy devices (ip link add … type dummy), e.g. dummy0."""
    return bool(interface_name) and interface_name.startswith("dummy")


def _has_link_layer_address(interface_name: str) -> bool:
    """True if sysfs reports a non-empty address (MAC) for the interface."""
    addr_path = os.path.join(SYS_CLASS_NET, interface_name, "address")
    try:
        with open(addr_path, encoding="utf-8") as f:
            return bool(f.read().rstrip())
    except OSError:
        return False


def _read_mac(ifname: str) -> Optional[str]:
    """MAC for bonding slave (perm_hwaddr) or interface address file."""
    bond_path = os.path.join(SYS_CLASS_NET, ifname, "bonding_slave", "perm_hwaddr")
    try:
        with open(bond_path, encoding="utf-8") as f:
            return f.read().rstrip()
    except OSError:
        pass
    addr_path = os.path.join(SYS_CLASS_NET, ifname, "address")
    try:
        with open(addr_path, encoding="utf-8") as f:
            return f.read().rstrip()
    except OSError:
        return None


def _is_real_nic(interface_name: str) -> bool:
    if interface_name == "lo":
        return True
    device_dir = os.path.join(SYS_CLASS_NET, interface_name, "device")
    if not os.path.isdir(device_dir):
        return False
    addr_path = os.path.join(SYS_CLASS_NET, interface_name, "address")
    try:
        with open(addr_path, encoding="utf-8") as f:
            addr = f.read().rstrip()
    except OSError:
        return False
    return bool(addr)


def _is_vf_by_name(interface_name: str) -> bool:
    physfn = os.path.join(SYS_CLASS_NET, interface_name, "physfn")
    return os.path.isdir(physfn)


def _is_available_nic(interface_name: str, check_active: bool) -> bool:
    if interface_name == "lo":
        return False
    # Dummies have no PCI device/ in sysfs; still mappable by MAC/name (Molecule, etc.)
    if _is_kernel_dummy(interface_name):
        if not _has_link_layer_address(interface_name):
            return False
    elif not _is_real_nic(interface_name):
        return False
    if check_active:
        try:
            with open(
                os.path.join(SYS_CLASS_NET, interface_name, "operstate"),
                encoding="utf-8",
            ) as f:
                operstate = f.read().rstrip().lower()
        except OSError:
            return False
        if operstate != "up":
            return False
    if _is_vf_by_name(interface_name):
        return False
    return True


def _ordered_nics(check_active: bool) -> List[str]:
    embedded_nics: List[str] = []
    nics: List[str] = []
    for name in glob.iglob(SYS_CLASS_NET + "/*"):
        nic = name[len(SYS_CLASS_NET) + 1 :]
        if _is_available_nic(nic, check_active):
            if _is_embedded_nic(nic):
                embedded_nics.append(nic)
            else:
                nics.append(nic)
    active_nics = sorted(embedded_nics, key=_natural_sort_key) + sorted(
        nics, key=_natural_sort_key
    )
    return active_nics


def derive_nic_mapping(nic_mapping: Optional[dict]) -> Dict[str, str]:
    """Resolve user interface_mapping to Linux names; assign nicN for leftovers."""
    mapping = dict(nic_mapping or {})
    mapped: Dict[str, str] = {}

    if mapping:
        available_nics = _ordered_nics(check_active=False)
        for nic_alias, nic_mapped in mapping.items():
            nm = nic_mapped
            nm_mac = _normalize_mac(str(nm))
            if nm_mac:
                found = False
                for nic in available_nics:
                    mac = _read_mac(nic)
                    mac_norm = _normalize_mac(mac) if mac else None
                    if mac_norm and nm_mac == mac_norm:
                        nm = nic
                        found = True
                        break
                if not found:
                    LOG.error(
                        "mac %s not found in available nics %s",
                        nic_mapped,
                        ", ".join(available_nics),
                    )
                    continue
            elif nm not in available_nics:
                LOG.error(
                    "nic %s not found in available nics %s",
                    nic_mapped,
                    ", ".join(available_nics),
                )
                continue

            if nm in mapped.values():
                raise ValueError(
                    "interface %s already mapped, check mapping file for duplicates"
                    % nm
                )
            if _is_available_nic(nic_alias, check_active=True):
                raise ValueError(
                    "cannot map %s to alias %s, alias overlaps with active NIC."
                    % (nm, nic_alias)
                )
            if _is_real_nic(nic_alias) or _is_kernel_dummy(nic_alias):
                LOG.warning(
                    "Mapped nic %s overlaps with name of inactive NIC.", nic_alias
                )

            mapped[nic_alias] = nm
            LOG.info("%s => %s", nic_alias, nm)

    active_nics = _ordered_nics(check_active=True)
    for nic_mapped in set(active_nics).difference(set(mapped.values())):
        nic_alias = "nic%i" % (active_nics.index(nic_mapped) + 1)
        if nic_alias in mapped:
            LOG.warning(
                "no mapping for interface %s because %s is mapped to %s",
                nic_mapped,
                nic_alias,
                mapped[nic_alias],
            )
        else:
            mapped[nic_alias] = nic_mapped
            LOG.info("%s => %s", nic_alias, nic_mapped)

    if not mapped:
        LOG.warning("No active nics found.")
    return mapped


def load_yaml(path: str) -> Dict[str, str]:
    if not os.path.isfile(path):
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required: on RHEL-like hosts install package python3-pyyaml "
            "(see edpm_network_config_systemrole_nmstate_dependencies)."
        ) from exc
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        return {}
    if "interface_mapping" in data:
        return dict(data["interface_mapping"])
    if "mapped_nics" in data:
        return dict(data["mapped_nics"])
    return {}


def save_yaml(path: str, mapped: Dict[str, str]) -> bool:
    """Write derived mapping YAML. Returns True if the file was created or updated."""
    import yaml

    payload = {"interface_mapping": mapped}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
            if existing.get("interface_mapping") == mapped:
                return False
        except OSError:
            pass

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, default_flow_style=False, allow_unicode=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive NIC alias to interface name mapping for EDPM (standalone)."
    )
    parser.add_argument(
        "-f",
        "--file",
        default=DEFAULT_PATH,
        help=f"Read/write derived mapping YAML (default: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="Do not write the output file."
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    nic_mapping = load_yaml(args.file)
    result = derive_nic_mapping(nic_mapping)

    LOG.debug("derived mapping: %r", result)
    if not args.dry_run:
        wrote = save_yaml(args.file, result)
        if wrote:
            LOG.info("Wrote %s", args.file)
        else:
            LOG.info("Derived mapping unchanged for %s", args.file)
        # One line for Ansible changed_when (stdout; logging uses stderr).
        print(
            "edpm_derived_nic_mapping_changed=yes"
            if wrote
            else "edpm_derived_nic_mapping_changed=no"
        )
    else:
        print(result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as e:
        LOG.error("%s", e)
        sys.exit(1)
