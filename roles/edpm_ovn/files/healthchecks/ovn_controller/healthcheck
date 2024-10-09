#!/bin/sh

# Ensure ovn-controller connection status is OK
output=$(ovn-appctl -t ovn-controller connection-status)
if [ "$output" != "connected" ]; then
    echo "ERROR - OVN-Controller is not connected to OVN SB database"
    exit 1
fi

# Ensure ovsdb-server is OK
ovsdbserverpidfile=$(find /var/run/openvswitch -name "ovsdb-server.pid")
if [ -n "$ovsdbserverpidfile" ]; then
    pid=$(cat "$ovsdbserverpidfile")
    output=$(ovn-appctl -t /var/run/openvswitch/ovsdb-server."$pid".ctl ovsdb-server/list-dbs)
    if [ -z "$output" ]; then
        echo "ERROR - Failed retrieving list of databases from ovsdb-server"
        exit 1
    fi
else
    echo "ERROR - Failed to get pid for ovsdb-server process"
    exit 1
fi

# Ensure ovs-vswitchd is OK
ovsvswitchdpidfile=$(find /var/run/openvswitch -name "ovs-vswitchd.pid")
if [ -n "$ovsvswitchdpidfile" ]; then
    pid=$(cat "$ovsvswitchdpidfile")
    output=$(ovn-appctl -t /var/run/openvswitch/ovs-vswitchd."$pid".ctl ofproto/list)
    if [ -z "$output" ]; then
        echo "ERROR - Failed to retrieve ofproto instances from ovs-vswitchd"
        exit 1
    fi
else
    echo "ERROR - Failed to get pid for ovs-vswitchd process"
    exit 1
fi

exit 0
