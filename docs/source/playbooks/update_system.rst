========================
Playbook - update_system
========================

The ``update_system`` playbook is the host operating system half of the split
update interface. It invokes the ``edpm_update_system`` role to update the host
operating system through RPM package updates or the bootc update path, with
optional kpatch use. It does not update OpenStack service containers.

.. literalinclude:: ../../../playbooks/update_system.yml
   :language: YAML
