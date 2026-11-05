==========================
Playbook - update_services
==========================

The ``update_services`` playbook is the service half of the split
update interface. It invokes the ``edpm_update_services`` role to
update service containers and the limited service package set. It does
not update the operating system.

.. literalinclude:: ../../../playbooks/update_services.yml
   :language: YAML
