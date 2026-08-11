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

Additional OvS other_config settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most common OvS DPDK ``other_config`` keys have a dedicated variable (see
``roles/edpm_ovs_dpdk/defaults/main.yml``). For anything else, set
``edpm_ovs_dpdk_other_config`` with the raw key/value pairs; these are applied via
``ovs-vsctl set Open_vSwitch . other_config:<key>=<value>``. See
`ovs-vswitchd.conf.db(5) <http://www.openvswitch.org/support/dist-docs/ovs-vswitchd.conf.db.5.txt>`_
for the full list of supported keys. Values set by a dedicated variable above
take precedence over ``edpm_ovs_dpdk_other_config`` for any overlapping key.

.. code-block:: YAML

    - name: "Configure OvS DPDK Configs"
      include_role:
        name: "osp.edpm.edpm_ovs_dpdk"
      vars:
         edpm_ovs_dpdk_pmd_core_list: "1,13,3,15"
         edpm_ovs_dpdk_other_config:
           smc-enable: true
           pmd-rxq-assign: group
           pmd-rxq-isolate: false
