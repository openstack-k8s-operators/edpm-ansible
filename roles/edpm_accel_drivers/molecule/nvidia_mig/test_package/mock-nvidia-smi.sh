#!/bin/sh
# Mock nvidia-smi for molecule MIG scenario.
# Returns a fixed PCI BDF for --query-gpu=pci.bus_id
# Returns a fixed MIG layout for mig -lgi
# Always succeeds
if echo "$*" | grep -q 'pci.bus_id' && echo "$*" | grep -q 'query-gpu'; then
    echo '00000000:07:00.0'
fi
if echo "$*" | grep -q 'mig -lgi'; then
    echo '+---------------------------------------------------------+'
    echo '| GPU instances:                                          |'
    echo '| GPU   Name               Profile  Instance   Placement  |'
    echo '|                            ID       ID       Start:Size |'
    echo '|=========================================================|'
    echo '|   0  MIG 1g.6gb            14        3          0:1     |'
    echo '+---------------------------------------------------------+'
    echo '|   0  MIG 1g.6gb            14        4          1:1     |'
    echo '+---------------------------------------------------------+'
    echo '|   0  MIG 1g.6gb            14        5          2:1     |'
    echo '+---------------------------------------------------------+'
    echo '|   0  MIG 1g.6gb            14        6          3:1     |'
    echo '+---------------------------------------------------------+'
fi
exit 0
