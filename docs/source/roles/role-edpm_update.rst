==================
Role - edpm_update
==================

Updates the services that are managed by the included roles. Typically through
just including the roles `run.yml` tasks file. As such, it does not run the full
set of tasks that would be run on an initial deployment by other playbooks.

If additional tasks need to be run on update, they should be included in the
`edpm_update` role through some mechanism.


.. include::
  ../collections/osp/edpm/edpm_update_role.rst
