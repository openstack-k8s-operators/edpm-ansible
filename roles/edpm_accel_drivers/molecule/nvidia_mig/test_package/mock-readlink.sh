#!/bin/sh
# MOCK_READLINK - molecule test mock (marker, do not remove).
#
# Mock readlink -e for molecule MIG scenario.
#
# Only the SR-IOV virtfn0 lookup is faked. Every other invocation is
# delegated to the real readlink binary that the prepare playbook
# saves as /usr/bin/readlink.bak. The delegation is required because
# other tooling resolves paths with readlink while this mock is
# installed: dracut canonicalizes its output file with
#   abs_outfile=$(readlink -f "$outfile") && outfile="$abs_outfile"
# so a mock that always succeeds with empty output blanks the dracut
# outfile and makes the "Regenerate initramfs" task fail with
# "cp: cannot create regular file ''" in any scenario sharing the
# test environment with a MIG scenario (e.g. nvidia_repo).
if echo "$*" | grep -q '-e /sys/bus/pci/devices/0000:07:00.0/virtfn0'; then
    echo '/sys/devices/pci0000:42/0000:42:02.0/0000:07:01.4'
    exit 0
fi
# Delegate to the real readlink, guarding against readlink.bak having
# been overwritten with this very mock by an older, non-idempotent
# prepare run (which would make us exec ourselves forever).
if [ -x /usr/bin/readlink.bak ] && ! grep -q 'MOCK_READLINK' /usr/bin/readlink.bak; then
    exec /usr/bin/readlink.bak "$@"
fi
# Real readlink is not available: fail like readlink does on error,
# so callers relying on the exit code (e.g. dracut) keep working.
exit 1
