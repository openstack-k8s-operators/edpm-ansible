==================================
Role - edpm_derive_pci_device_spec
==================================

Usage
~~~~~

This Ansible role allows to do the following tasks:

* Derives the config map pci device_spec

* Using the user provided device_spec list and sriov-phys_dev_map,
  derive the pci device_spec config map for a
  nic-partitioned deployment

  Here is an example of the playbook:

.. code-block:: YAML

    - name: "Derive the NIC partition config map of pci device_spec"
      include_role:
        name: "osp.edpm.edpm_derive_pci_device_spec"
      vars:
        edpm_derive_sriov_device_spec_list: [{"address": "0000:17:00.*", "trusted": "true"}]
        sriov_phydev_map: ''
        sriov_nova_conf_file: 20-sriov-nova.conf
