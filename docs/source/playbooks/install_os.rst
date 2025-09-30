=====================
Playbook - install_os
=====================

Installs services necessary for the EDPM operation.
Uses external `timesync` role from `system roles collection`_ to both install and configure chrony.

--------------------------
Time service configuration
--------------------------

Variables of the `timesync`_ system role can be overridden in a standard ansible way,
while respecting resolution order. Default values are set in the `install_os` playbook,
while allowing for override.

All variables of the timesync role can used while using this playbook.

.. _`system roles collection`: https://linux-system-roles.github.io/
.. _`timesync`: https://github.com/linux-system-roles/timesync

.. literalinclude:: ../../../playbooks/install_os.yml
   :language: YAML
