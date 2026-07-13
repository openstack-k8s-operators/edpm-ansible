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

The nmstate tool is experimental; set
``edpm_network_config_tool_nmstate_override: true`` to run it.
Set ``edpm_network_config_update: true`` (or rely on first-run / failed-run
logic) so the template is applied.

Example playbook (inline template):

.. code-block:: YAML

    - name: Configure host network with nmstate
      ansible.builtin.include_role:
        name: osp.edpm.edpm_network_config
      vars:
        edpm_network_config_tool: nmstate
        edpm_network_config_tool_nmstate_override: true
        edpm_network_config_update: true
        edpm_network_config_template: |
          ---
          interfaces:
            - name: nic1
              type: ethernet
              state: up
              mtu: 1500

Example playbook (template from file; copy
``roles/edpm_network_config/examples/nmstate_sriov.yaml`` into your playbook
``files/`` directory):

.. code-block:: YAML

    - name: Configure host network with nmstate (SR-IOV template file)
      ansible.builtin.include_role:
        name: osp.edpm.edpm_network_config
      vars:
        edpm_network_config_tool: nmstate
        edpm_network_config_tool_nmstate_override: true
        edpm_network_config_update: true
        edpm_network_config_template: >-
          {{ lookup('file', playbook_dir + '/files/nmstate_sriov.yaml') }}

SR-IOV with the nmstate tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SR-IOV is configured in ``edpm_network_config_template`` under the PF
(physical function) ``ethernet.sr-iov`` section. Nmstate creates or updates
VFs according to ``total-vfs`` and optional per-VF settings (``trust``,
``spoof-check``, MAC addresses, and so on). See the
`nmstate YAML API <https://nmstate.io/devel/yaml_api.html>`_ SR-IOV section.

When the ``vfs`` list is present, nmstate expects configuration for every VF
up to ``total-vfs`` (see nmstate documentation). For OpenStack dataplane NICs,
``trust: true`` on VFs is commonly required before Neutron SR-IOV agent use.

A full example template ships with this role:

.. literalinclude:: ../../../roles/edpm_network_config/examples/nmstate_sriov.yaml
   :language: yaml

Minimal SR-IOV (VF count only, default VF parameters):

.. code-block:: yaml

    ---
    interfaces:
      - name: nic1
        type: ethernet
        state: up
        ethernet:
          sr-iov:
            drivers-autoprobe: true
            total-vfs: 8

PCI device_map (nmstate tool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After a successful nmstate apply, the role records the PCI address and
currently bound kernel driver of every physical network device (PCI
ethernet NIC or SR-IOV VF) in ``edpm_network_config_nmstate_device_map_file``
(default ``/var/lib/edpm-config/nmstate_device_map.yaml``). Devices are
identified by the presence of a ``device`` symlink in sysfs, which naturally
excludes virtual netdevs (bond, bridge, dummy, vlan, veth, loopback). This is
observational only; see ``edpm_nmstate_device_map.py``.

PCI driver binding (driverctl)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set ``edpm_network_config_driver_bind`` (nmstate tool path only) to bind a
kernel driver at a specific PCI address before the main nmstate apply runs,
e.g. to hand a NIC to ``vfio-pci`` for DPDK/SR-IOV passthrough, or to return
one to its native driver:

.. code-block:: yaml

    edpm_network_config_driver_bind: |
      ---
      interfaces:
        - name: eno12399np0
          pci_address: "0000:8a:00.0"
          driver: vfio-pci

For every entry, the role first confirms that ``name`` really identifies
``pci_address``:

* If the netdev named ``name`` is present in sysfs, its live PCI address
  must match the declared ``pci_address``. A mismatch fails the run.
* If the netdev is not present in sysfs (e.g. it was already unbound from
  the host network stack), the role falls back to the persisted
  ``edpm_network_config_nmstate_device_map_file``. If that map has a
  recorded PCI address for ``name`` which does not match ``pci_address``,
  the run still fails.
* If neither sysfs nor the device_map have anything recorded for ``name``,
  there is nothing to cross-check; the declared ``pci_address`` is trusted
  and binding proceeds.

Validation runs for every entry before any binding happens, so one bad entry
does not leave earlier entries half-applied. Once validated, each entry is
bound with ``driverctl set-override <pci_address> <driver>`` (idempotent:
if the PCI address is already bound to the requested driver, that entry is
a no-op). See ``edpm_driver_bind.py``.

