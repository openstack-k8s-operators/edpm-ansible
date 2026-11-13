========
growvols
========

Grow one or more LVM volumes.

The ``edpm_growvols`` role ships the ``growvols`` utility in ``files/growvols``
and runs it as ``growvols --yes`` with the volume allocations from the
``growvols_args`` role variable.

This documentation is adapted from the `diskimage-builder growvols element README
<https://docs.openstack.org/diskimage-builder/latest/elements/growvols/README.html>`_.

The utility grows the logical volumes in an LVM group to take available
device space.

The positional arguments specify how available space is allocated. They
have the format <volume>=<amount><unit> where:

<volume> is the label or the mountpoint of the logical volume
<amount> is an integer growth amount in the specified unit
<unit> is one of the supported units

Supported units are:

% percentage of available device space before any changes are made
MiB mebibyte (1048576 bytes)
GiB gibibyte (1073741824 bytes)
MB megabyte (1000000 bytes)
GB gigabyte (1000000000 bytes)

Each argument is processed in order and the requested amount is allocated
to each volume until the disk is full. This means that if space is
overallocated, the last volumes may only grow by the remaining space, or
not grow at all, and a warning will be printed. When space is underallocated
the remaining space will be given to the root volume (mounted at /).

The currently supported partition layout is:
- Exactly one of the partitions containing an LVM group
- The disk having unpartitioned space to grow with
- The LVM logical volumes being formatted with XFS filesystems

Example usage:

growvols /var=80% /home=20GB

growvols /var/log=25GB /var=100%
