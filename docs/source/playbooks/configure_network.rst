============================
Playbook - configure_network
============================

.. warning::
    When the `edpm_network_config_tool` is set to `'os-net-config'`, the `ctlplane_gateway_ip` and `ctlplane_ip`
    variables must be set on the host for the playbook to function properly.

Calls edpm_network_config role to set up network.
Uses value of the `edpm_network_config_tool` variable to determine which tool to use.
The `'nmstate'` value will leave the process to the `systemroles.network` role,
while the `'os-net-config'` will import custom tasks using os-net-config.

.. literalinclude:: ../../../playbooks/configure_network.yml
   :language: YAML
