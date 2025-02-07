========================
Role - edpm_ovs_dpdk
========================

Usage
~~~~~

This Ansible role allows to do the following tasks:

* Configure the required OvS DPDK configuration
   based on the OvS DPDK edpm ansible variables.

* Remove any existing OvS DPDK configuration based
  on the OvS DPDK edpm ansible variables.

  Here is an example of a playbook:

.. code-block:: YAML

    - name: "Configure OvS DPDK Configs"
      include_role:
        name: "osp.edpm.edpm_ovs_dpdk"
      vars:
         edpm_ovs_dpdk_pmd_core_list: "1,13,3,15"
         edpm_ovs_dpdk_socket_memory: "4096"
         edpm_ovs_dpdk_memory_channels: 4
         edpm_ovs_dpdk_vhost_postcopy_support: true
