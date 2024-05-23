================================
Role - edpm_tripleo_cleanup
================================

Role stops and disables all systemd units enumerated to it.
If the role doesn't recieve list of services, it will instead stop and disable
all units containing string "tripleo" in their name.

This way we can effectivelly prevent any leftovers of original tripleo based
deployment from interfering with post-adoption setup.

.. include::
  ../collections/osp/edpm/edpm_tripleo_cleanup_role.rst
