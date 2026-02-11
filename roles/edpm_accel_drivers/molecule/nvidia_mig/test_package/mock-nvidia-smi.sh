#!/bin/sh
# Mock nvidia-smi for molecule MIG scenario.
# Returns a fixed PCI BDF for --query-gpu=pci.bus_id; otherwise exits 0.
if echo "$*" | grep -q 'pci.bus_id' && echo "$*" | grep -q 'query-gpu'; then
    echo '00000000:07:00.0'
    exit 0
fi
exit 0
