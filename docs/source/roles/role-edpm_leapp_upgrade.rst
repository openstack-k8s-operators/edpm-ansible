=========================
Role - edpm_leapp_upgrade
=========================

Usage
~~~~~

This Ansible role performs an in-place OS upgrade of EDPM nodes from RHEL 9
to RHEL 10. It is a thin EDPM wrapper around the ``infra.leapp``
collection: the role owns the EDPM pre-flight validation (OS version, NIC
naming, nmstate migration, stale leapp job logs), while the analysis and
the upgrade itself, including the reboot and the post-upgrade tasks, are
delegated to the ``infra.leapp.analysis`` and ``infra.leapp.upgrade``
roles.

The role runs in three phases that can be selected with the
``leapp_validate``, ``leapp_analysis`` and ``leapp_run`` tags. Note that
the node reboots as part of the ``leapp_run`` phase.

Here is an example of a playbook using the role:

.. code-block:: YAML

    - name: Upgrade OS to next Major version (leapp)
      hosts: all
      tasks:
        - name: Import leapp upgrade role
          ansible.builtin.import_role:
            name: osp.edpm.edpm_leapp_upgrade

.. include::
   ../collections/osp/edpm/edpm_leapp_upgrade_role.rst
