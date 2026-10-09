#!/bin/sh
# Mock readlink -e for molecule MIG scenario.
# Always succeeds
if echo "$*" | grep -q '-e /sys/bus/pci/devices/0000:07:00.0/virtfn0'; then
    echo '/sys/devices/pci0000:42/0000:42:02.0/0000:07:01.4'
fi
exit 0
