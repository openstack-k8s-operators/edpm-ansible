****************************
edpm_libvirt (permissive)
****************************

This scenario mirrors the default edpm_libvirt molecule scenario, but
simulates a host without the openstack-selinux package (as on RHOSO 19
Beta hosts, which do not ship this RPM) with SELinux running in
permissive mode.

It verifies that the edpm_libvirt role completes successfully and does
not attempt to enable the os_enable_vtpm SELinux boolean when the
boolean is not provided by openstack-selinux and SELinux is not
enforcing.
