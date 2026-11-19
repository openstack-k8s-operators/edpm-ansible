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

SR-IOV VF driver binding for NIC Partitioning (dispatcher script)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For NIC Partitioning, some VFs of a PF are meant to stay on the host under
their default kernel driver (e.g. as bond/OVS members), while others are
meant to be handed to ``vfio-pci`` for DPDK or SR-IOV passthrough to a guest.
nmstate's VF schema has no ``driver`` field, so this binding is done via a
helper script the role installs at ``edpm_network_config_vf_driver_bind_script``
(default ``/usr/local/bin/edpm-vf-driver-bind``), invoked from a
NetworkManager dispatcher script attached to the PF via nmstate's native
``dispatch.post-activation`` interface property. Since NetworkManager
re-runs dispatcher scripts every time the PF activates (including across
reboots), the binding is self-healing and does not depend on an
edpm-ansible run having just happened.

The operator adds the ``dispatch.post-activation`` block directly to the
PF's entry in ``edpm_network_config_nmstate_sriov_pf_template`` (or
``edpm_network_config_template``), passing the PF name and the desired VF
ids (space-separated) via the ``--pf``/``--dpdk-vfs``/``--linux-vfs`` flags
(``--pf`` required, the VF-id flags each optional):

.. code-block:: yaml

    edpm_network_config_nmstate_sriov_pf_template: |
      ---
      interfaces:
        - name: nic3
          type: ethernet
          ethernet:
            sr-iov:
              total-vfs: 4
          dispatch:
            post-activation: |
              /usr/local/bin/edpm-vf-driver-bind --pf "$1" --dpdk-vfs "0 1" --linux-vfs "2 3"

In this example, VFs 0 and 1 are bound to ``vfio-pci`` and VFs 2 and 3 are
(re-)bound to their default kernel driver. NetworkManager invokes
dispatcher scripts as ``<script> <interface> <action> ...``, so ``$1`` is
always the activated PF's interface name; it is forwarded to ``--pf``
rather than relied upon positionally, so every argument is self-describing.

The VF-id flags may each be omitted when there is nothing for them to do,
with no risk of a list landing in the wrong slot, e.g. a PF with only Linux
VFs (no DPDK passthrough) needs just:

.. code-block:: yaml

            post-activation: |
              /usr/local/bin/edpm-vf-driver-bind --pf "$1" --linux-vfs "0 1 2 3"

For each listed VF id, the script:

* Resolves the VF's PCI address via
  ``/sys/class/net/<pf>/device/virtfn<vfid>``.
* Computes the VF's default kernel driver via
  ``modprobe -R $(cat .../virtfn<vfid>/modalias)``.
* Binds to ``vfio-pci`` if the VF is in ``dpdk_vfs`` (unless its default
  driver is a Mellanox driver, which manages its own VFs in-kernel and must
  not be overridden), otherwise binds to the computed default driver.
* Only calls ``driverctl --nosave set-override`` when the VF's currently
  bound driver differs from the target, so re-runs (e.g. on every PF
  activation) are no-ops once correctly bound. Explicitly (re-)binding
  ``linux_vfs`` too matters when ``sriov_drivers_autoprobe`` is disabled on
  the PF, since nothing gets bound automatically in that case.

This mirrors ``os-net-config``'s ``_VF_BIND_DRV_SCRIPT``/dispatcher-script
approach (``os_net_config/impl_nmstate.py``). ``driverctl`` is required on
the host; it is included in
``edpm_network_config_systemrole_nmstate_dependencies``. See
``edpm_vf_driver_bind.sh``.

