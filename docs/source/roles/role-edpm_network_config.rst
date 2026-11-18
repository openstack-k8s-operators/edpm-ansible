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

Note: * With nmstate-provider as the default for os-net-config,
        using "edpm_network_config_nonconfigured_cleanup" is not recommended.
        Instead, enabling flag "edpm_network_config_remove_config"
        with appropriate remove_config section added in
        "edpm_network_config_template" is the supported option

      * "edpm_network_config_nonconfigured_cleanup" SHOULD NOT be set for
        update/adoption usecase

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

Here is an example playbook to run os-net-config tool with --remove_config section:

.. code-block:: YAML

    - name: Cleanup and apply network configuration only
      include_role:
        name: edpm_network_config
      vars:
        edpm_network_config_template:
          "{{ nic_config_file }}"
        edpm_network_config:
          remove_config: true

An example of using ``remove_config`` is available in:

.. literalinclude:: ../../../roles/edpm_network_config/molecule/default/converge.yml
   :language: YAML

nmstate tool
~~~~~~~~~~~~

When ``edpm_network_config_tool`` is ``nmstate``, the role applies
``edpm_network_config_template`` as nmstate desired state via the
``linux_system_roles.network`` role (see ``nmstate_tool.yml``).
NetworkManager is configured to manage ``/etc/resolv.conf`` on this path.

The nmstate tool is experimental. Set ``edpm_network_config_tool: nmstate``
and ``edpm_network_config_update: true`` (or rely on first-run / failed-run
logic) so the template is applied.

Templates may use real kernel interface names (for example ``eno12399np0``)
or ``nicN`` aliases. Before apply, ``nicN`` values under nmstate interface
keys are substituted from the derived NIC mapping
(``edpm_substitute_nic_aliases``).

After a successful apply, the role refreshes
``edpm_network_config_nmstate_device_map_file`` (default
``/var/lib/edpm-config/nmstate_device_map.yaml``) with the PCI address, MAC,
and bound kernel driver of each physical network device. This map is
observational; other nmstate-path helpers can use it as a fallback when a
netdev is no longer present in sysfs.

Example playbook (inline template):

.. code-block:: YAML

    - name: Configure host network with nmstate
      ansible.builtin.include_role:
        name: osp.edpm.edpm_network_config
      vars:
        edpm_network_config_tool: nmstate
        edpm_network_config_update: true
        edpm_network_config_template: |
          ---
          interfaces:
            - name: nic1
              type: ethernet
              state: up
              mtu: 1500

Example playbook (template from a file):

.. code-block:: YAML

    - name: Configure host network with nmstate
      ansible.builtin.include_role:
        name: osp.edpm.edpm_network_config
      vars:
        edpm_network_config_tool: nmstate
        edpm_network_config_update: true
        edpm_network_config_template: >-
          {{ lookup('file', playbook_dir + '/files/nmstate_desired_state.yaml') }}

SR-IOV with the nmstate tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the nmstate tool path, SR-IOV uses an optional two-step apply so VF
creation and per-VF configuration are not mixed in one pass.

**Single pass:** set ``edpm_network_config_template`` only (no SR-IOV PF
template).

**Two-step SR-IOV:** set ``edpm_network_config_nmstate_sriov_pf_template``
(phase 1: PF + ``ethernet.sr-iov.total-vfs`` only — create VFs) and
``edpm_network_config_template`` (phase 2: per-VF ``vfs`` settings, bonds,
IPs). Phase 1 runs first; the role optionally waits until sysfs
``sriov_numvfs`` matches ``total-vfs`` before phase 2.

Do **not** include the per-VF ``vfs`` list in phase 1; VF creation and
per-VF configuration cannot be applied reliably in the same pass.

Per-VF settings (``trust``, ``spoof-check``, MAC addresses, rates, VLAN, and
so on), bonds, bridges, and L3 addressing belong in
``edpm_network_config_template`` (phase 2), applied after VFs exist. See the
`nmstate YAML API <https://nmstate.io/devel/yaml_api.html>`_ SR-IOV section.

Use ``sriov:<pf_name>:<vf_id>`` port names or kernel VF netdev names in
phase 2 if resolution fails; see `Referring interface using SR-IOV PF name
and VF ID <https://nmstate.io/features/iface_vf_id.html>`_.

When the ``vfs`` list is present in phase 2, nmstate expects configuration
for every VF up to ``total-vfs``. For OpenStack dataplane NICs,
``trust: true`` on VFs is commonly required before Neutron SR-IOV agent use.

Two-step SR-IOV + bond (copy example files into playbook ``files/``):

.. code-block:: YAML

    - name: Configure host network with nmstate (SR-IOV two-step)
      ansible.builtin.include_role:
        name: osp.edpm.edpm_network_config
      vars:
        edpm_network_config_tool: nmstate
        edpm_network_config_update: true
        edpm_network_config_nmstate_sriov_pf_template: >-
          {{ lookup('file', playbook_dir + '/files/nmstate_sriov_phase1.yaml') }}
        edpm_network_config_template: >-
          {{ lookup('file', playbook_dir + '/files/nmstate_sriov_phase2.yaml') }}

Phase 1 example (PF, ``total-vfs`` only):

.. literalinclude:: ../../../roles/edpm_network_config/examples/nmstate_sriov_phase1.yaml
   :language: yaml

Phase 2 example (per-VF ``vfs`` settings + Linux bond on two VFs):

.. literalinclude:: ../../../roles/edpm_network_config/examples/nmstate_sriov_phase2.yaml
   :language: yaml

For SR-IOV-only hosts (no bond or phase-2 config), set
``edpm_network_config_nmstate_sriov_pf_template`` from phase 1 and leave
``edpm_network_config_template`` empty.

Minimal SR-IOV (VF count only, default VF parameters):

.. code-block:: yaml

    ---
    interfaces:
      - name: eno12399np0
        type: ethernet
        state: up
        ethernet:
          sr-iov:
            drivers-autoprobe: true
            total-vfs: 8

Optional wait tuning after phase 1 (sysfs path uses each PF ``name`` as a
kernel netdev under ``/sys/class/net/<name>/device/sriov_numvfs``):

.. code-block:: yaml

    edpm_network_config_nmstate_sriov_vf_wait: true
    edpm_network_config_nmstate_sriov_vf_wait_timeout: 60
    edpm_network_config_nmstate_sriov_vf_wait_delay: 2

Host SR-IOV in nmstate configures the PF and VFs on the node. Nova
``pci_passthrough:device_spec`` for SR-IOV instances is a separate step: use
the ``edpm_derive_pci_device_spec`` role and ``neutron_sriov`` playbook
(``physical_device_mappings`` on the agent) together with this network config.
