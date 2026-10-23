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

Set ``edpm_network_config_tool: nmstate`` and
``edpm_network_config_update: true`` (or rely on first-run / failed-run
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

PCI driver binding (driverctl)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the nmstate tool path only, set ``edpm_network_config_driver_bind`` to bind
a kernel driver at a PCI address **before** the main nmstate apply (for
example hand a NIC to ``vfio-pci`` for DPDK, or return it to its native
driver).

Requires ``driverctl`` on the node. Non-bootc hosts get it from
``edpm_bootstrap`` (``edpm_bootstrap_packages_bootstrap``). Bootc hosts skip
package installation, so the bootc image must already include ``driverctl``;
the role preflights for the binary before binding.

Each entry is ``{name, pci_address, driver}``. ``name`` may be a real
interface name or an EDPM NIC alias (``nic1``, ``nic2``, ...); aliases are
resolved from the derived NIC mapping before the bind input is written.

.. code-block:: yaml

    edpm_network_config_driver_bind: |
      ---
      interfaces:
        - name: nic2
          pci_address: "0000:8a:00.0"
          driver: vfio-pci

For every entry, the role confirms that ``name`` identifies ``pci_address``:

* If ``name`` is a physical netdev in sysfs (has a ``device`` symlink),
  its live PCI address must match ``pci_address``. A mismatch fails the run.
* If ``name`` is not a physical netdev (absent, or a virtual interface such
  as a bridge), the role falls back to
  ``edpm_network_config_nmstate_device_map_file``. A recorded PCI for
  ``name`` must match ``pci_address``; a mismatch fails the run.
* If neither a live physical netdev nor a device-map PCI entry can confirm
  ``name``, the run fails (the declared ``pci_address`` is not trusted).

All entries are validated before any bind runs, so a validation failure does
not leave earlier entries half-applied. Binding itself is not atomic: if a
later ``driverctl set-override`` fails, earlier successful binds remain in
place. Re-running the role after fixing the failure is safe because binding
skips entries already on the requested driver. See ``edpm_driver_bind.py``
and ``driver_bind.yml``.
