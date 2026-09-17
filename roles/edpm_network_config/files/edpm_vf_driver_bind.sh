#!/bin/bash
# Copyright 2026 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0
#
# Bind SR-IOV VF driver overrides for NIC Partitioning.
#
# Installed by edpm-ansible at a fixed path so it can be invoked from a
# NetworkManager dispatcher script attached to a PF interface via nmstate's
# "dispatch.post-activation" (see edpm_network_config role docs). NetworkManager
# invokes that generated dispatcher script as "<script> <interface> <action>
# ...", so within it "$1" is the PF's interface name; forward it via --pf:
#
#   edpm-vf-driver-bind --pf "$1" --dpdk-vfs "0 1" --linux-vfs "2 3"
#
# All arguments are named flags rather than fixed positional args, so a
# missing/misordered one is a clear error instead of e.g. a linux_vfs list
# silently landing in the dpdk_vfs slot. --pf is required; --dpdk-vfs/
# --linux-vfs are each optional (default: none) and take a space-separated
# list of VF ids, literal for the PF being partitioned, chosen by the
# operator authoring the nmstate template.
#
# VFs listed in --dpdk-vfs are bound to vfio-pci (unless the VF's own default
# driver is a Mellanox driver, which manages its VFs in-kernel and must not
# be overridden). VFs listed in --linux-vfs are (re-)bound to their default
# kernel driver; this matters when sriov_drivers_autoprobe is disabled on the
# PF, where nothing is bound automatically.
#
# Ported from os-net-config's _VF_BIND_DRV_SCRIPT
# (os_net_config/impl_nmstate.py), adapted for direct invocation with named
# flags instead of python str.format() templating.

set +e
set -x

usage="usage: edpm-vf-driver-bind --pf <name> [--dpdk-vfs \"<vfids>\"] [--linux-vfs \"<vfids>\"]"
pf=""
dpdk_vfs=""
linux_vfs=""

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "$usage" >&2
    exit 1
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --pf)
            pf="$2"
            shift 2
            ;;
        --dpdk-vfs)
            dpdk_vfs="$2"
            shift 2
            ;;
        --linux-vfs)
            linux_vfs="$2"
            shift 2
            ;;
        *)
            echo "edpm-vf-driver-bind: unrecognized argument: $1" >&2
            echo "$usage" >&2
            exit 1
            ;;
    esac
done

if [ -z "$pf" ]; then
    echo "edpm-vf-driver-bind: missing required --pf <name>" >&2
    echo "$usage" >&2
    exit 1
fi

for vfid in $dpdk_vfs $linux_vfs; do
    vf_pci_id=$(readlink -ve "/sys/class/net/$pf/device/virtfn$vfid") &&
    vf_pci_id=$(basename "$vf_pci_id") &&
    modalias=$(cat "/sys/class/net/$pf/device/virtfn$vfid/modalias") &&
    def_driver=$(modprobe -R "$modalias") &&
    if echo "$dpdk_vfs" | grep -qw "$vfid" && \
        ! echo "$def_driver" | grep -q ^mlx; then
        driver=vfio-pci
    else
        driver="$def_driver"
    fi &&
    cur_drv=$(readlink "/sys/bus/pci/devices/$vf_pci_id/driver" 2>/dev/null)
    cur_drv=$(basename "$cur_drv")
    if ! [ "$cur_drv" = "$driver" ]; then
        driverctl --nosave set-override "$vf_pci_id" "$driver"
    fi
done
