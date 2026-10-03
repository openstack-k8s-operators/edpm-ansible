============================
Playbook - configure_network
============================

.. warning::
    When the `edpm_network_config_tool` is set to `'os-net-config'`, the `ctlplane_gateway_ip` and `ctlplane_ip`
    variables must be set on the host for the playbook to function properly.


.. warning::
   When migrating between network providers, you MUST include ``minimum_config``
   in your ``edpm_network_config_template`` to maintain control plane connectivity.

Example::

   .. code-block:: yaml

      - edpm_network_config_template:
          network_config:
            - ...
          minimum_config:
            - ...

Calls edpm_network_config role to set up network.
Uses value of the `edpm_network_config_tool` variable to determine which tool to use.
The `'nmstate'` value will leave the process to the `systemroles.network` role,
while the `'os-net-config'` will import custom tasks using os-net-config.

For SR-IOV on the nmstate path, set ``edpm_network_config_tool: nmstate``,
``edpm_network_config_tool_nmstate_override: true``, and use two explicit templates:
``edpm_network_config_nmstate_sriov_pf_template`` (phase 1, PF SR-IOV) and
``edpm_network_config_template`` (phase 2, VFs and other network settings). See
:doc:`../roles/role-edpm_network_config` (sections *nmstate tool* and
*SR-IOV with the nmstate tool*) and
``roles/edpm_network_config/examples/nmstate_sriov_phase1.yaml`` /
``roles/edpm_network_config/examples/nmstate_sriov_phase2.yaml``.

.. literalinclude:: ../../../playbooks/configure_network.yml
   :language: YAML
