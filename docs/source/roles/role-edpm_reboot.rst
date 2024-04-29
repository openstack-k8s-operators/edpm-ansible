========================
Role - edpm_reboot
========================

Usage
~~~~~

This Ansible role allows to do the following tasks:

* Check if EDPM compute reboot is required.
  It takes care of checking EDPM hosts to see if other roles set flag to
  indicate need of reboot and if needs-restarting yum plugin reported that
  reboot is required.

* Reboot EDPM computes.
  During deployment reboot is triggered automatically if required. During
  post-deployment reconfiguration or adoption process reboot is not started.
  User has to plan reboot maintenance window and set `edpm_reboot_strategy`
  flag to force.


Here is an example of a playbook to  force start reboot:

.. code-block:: YAML

    - name: Force start reboot of nodes
      block:
        - name: "Force start reboot of nodes"
          include_role:
            name: edpm_reboot
           vars:
             edpm_reboot_strategy: force


.. include::
   ../collections/osp/edpm/edpm_reboot_role.rst
