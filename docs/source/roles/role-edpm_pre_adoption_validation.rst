===================================
Role - edpm_pre_adoption_validation
===================================

Implements a set of checks to be run before the main edpm_ansible deployment
executed during adoption but after the new OpenStackDataPlaneNodeSet CRs are
fully configured. See
[the adoption docs](https://openstack-k8s-operators.github.io/data-plane-adoption/)
for the detailed steps.

The goals of these checks to prevent applying such
new configuration to the edpm nodes that would either cause immediate problems
of the running workload or require a reboot to apply.

.. include::
  ../collections/osp/edpm/edpm_pre_adoption_validation_role.rst
