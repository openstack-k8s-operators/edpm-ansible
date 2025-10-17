=====
Usage
=====

The edpm-ansible collection is installed using standard `ansible CLI utilities`_.
Once it is installed, all roles, plugins and other files are accessible in paths
set by appropriate environment variables, unless overrides were given during
the installation process.


Using roles in playbooks
++++++++++++++++++++++++

Plabyooks should import roles whole, not only import specific subset of tasks.
Situations when this is necessary indicate inappropriate problem decomposition
and could point towards need for refactoring.

Roles must be invoked using their FQN, in order to prevent potential collisions
and to clarify collection dependencies.

Only variables that don't have appropriate defaults should be set explicitly
in the role invocation. The notable exception being repeated use of the same
role within the playbook, when it may be more beneficial, from the maintenance perspective,
to explicitly set other variables.

The role invocation in a playbook is analogous to call of function in other languages.
However, output of one role shouldn't impact operations of other roles, not including
cases when role execution fails.

Roles must not be imported using the plain `include`_ module, as it has been deprecated.
Instead the `roles`_ keyword should be used on the playbook level when possible.
Other modules of the `include_*` and `import_*` names are also allowed.

Roles should be only invoked with their parameters. Additional variables are permissible,
but should be avoided, as they will remain accessible to following tasks in playbook.


.. code-block:: yaml

    # playbook.yaml
    - hosts: webservers
      roles:
        - role: osp.edpm.edpm_telemetry
          edpm_telemetry_node_exporter_image: "wecollecttelemetrynow.img"


.. _`ansible CLI utilities`: https://galaxy.ansible.com/docs/using/installing.html
.. _`include`: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/include_module.html#include-module
.. _`roles`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html#roles-keyword
