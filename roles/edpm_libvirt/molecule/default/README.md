************
edpm_libvirt
************

The edpm_libvirt default molecule scenario uses
the delegated driver to run against localhost.

As such this should only be executed on a disposable host.

The molecule prepare command will install use several roles
to install podman, set the local timezone, configure
the correct repos for the current distro and otherwise
prepare the host to test the edpm_libvirt role.

The molecule converge command will execute the edpm_libvirt
role to install libvirt using the latest tcib images on quay.io

The molecule verify command will assert that the container are deployed correctly.
