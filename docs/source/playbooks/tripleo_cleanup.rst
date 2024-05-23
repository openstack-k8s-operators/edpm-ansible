==========================
Playbook - tripleo_cleanup
==========================

Stops and disables all tripleo services running on target hosts.
Heuristic based on systemd unit name pattern matching is used to determine
which services should be stopped and disabled.

.. literalinclude:: ../../../playbooks/tripleo_cleanup.yml
   :language: YAML
