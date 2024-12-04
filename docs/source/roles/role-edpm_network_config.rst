============================
Role - edpm_network_config
============================

Usage
~~~~~

This Ansible role does the following tasks:

* Read the configured edpm_network_config_tool
  The following choices can be used to configure the host network:
  - nmstate, i.e based on systemroles.network
  - os-net-config, i.e based on custom tasks
  os-net-config is the default tool for this role

* For os-net-config option, this role prepares the host by
  - creating necessary folders and files for rendering network
  templates and NIC mappings (optional)
  - Checks for the presence of required RPMS
  - Uses "provider" ifcfg/nmstate based on flag "edpm_network_config_nmstate"

Here is an example playbook to run os-net-config tool:

.. code-block:: YAML

    - name: Apply network_config
      block:
        - name: Configure host network with edpm-ansible
          include_role:
            name: edpm_network_config
          vars:
            edpm_network_config_template: "{{ nic_config_file }}"

.. literalinclude:: ../../../roles/edpm_network_config/tasks/os_net_config.yml
   :language: YAML
