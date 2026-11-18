==============
Playbook - frr
==============

FRR's configuration directory is stored on the host at
``{{ edpm_frr_config_basedir }}/etc/frr`` (by default,
``/var/lib/openstack/frr/etc/frr``) and mounted read/write in the container.
Changes saved by FRR persist across container restarts and subsequent role
runs. The role creates ``frr.conf`` if it does not exist. By default, changes
to FRR role variables do not update an existing ``frr.conf``. Set
``edpm_frr_overwrite_config`` to ``true`` to regenerate it from the role's
variables, replacing any runtime changes. The ``daemons`` file is managed
independently. Custom ``edpm_frr_volumes`` must include this writable mount.

On an existing deployment, changes saved only inside the old container are
not present in the host configuration directory. Back up any such changes
before redeploying the role, which replaces the container with the new mount,
and reapply them afterward.

During an update, existing host ``frr.conf``, ``vtysh.conf``, and ``daemons``
files are preserved. If a different legacy configuration also exists under
``/var/lib/config-data/ansible-generated/frr``, that directory is retained
for review.

.. literalinclude:: ../../../playbooks/frr.yml
   :language: YAML
