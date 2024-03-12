=======================================
Playbook - sriov_derive_device_spec.yml
=======================================

Derive the pci device_spec using edpm_derive_pci_device_spec role.

The user will specify the SR-IOV device_spec as a list, for this playbook
execution.
There will be a output conf file generated, which contains the allowed
device_spec configmap

.. literalinclude:: ../../../playbooks/sriov_derive_device_spec.yml
   :language: YAML
