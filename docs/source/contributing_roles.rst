============
Contributing
============

Adding roles into this project is easy and starts with a compatible skeleton.


Create a new role manually
~~~~~~~~~~~~~~~~~~~~~~~~~~

From with the project root, creating a skeleton for the new role.

.. code-block:: console

    $ ansible-galaxy init --role-skeleton=contribute/_skeleton_role_ --init-path=roles ${NEWROLENAME}

Finally add a role documentation file at
`docs/source/roles/role-${NEWROLENAME}.rst`. This file will need to contain
a title, a literal include of the defaults yaml and a literal include of
the molecule playbook, or playbooks, used to test the role, which is noted
as an "example" playbook.

Local testing of new roles
~~~~~~~~~~~~~~~~~~~~~~~~~~

Launch `make execute_molecule` to test all collections roles.

TBD: test single role


Contributing plugins
~~~~~~~~~~~~~~~~~~~~

All plugins contributed to the edpm-ansible can be found in the
`plugins` directory, from the root of this project.
When contributing a plugin, make sure to also add documentation in the
`docs/source/plugins` folder. All documentation added to this folder will be
automatically indexed and rendered via `sphinx`.

If a contributed plugin is following the Ansible practice of placing
documentation within the plugin itself, the following snippet can be used in a
sphinx template to auto-render the in-code documentation.

.. code-block:: rst

    .. ansibleautoplugin::
        :module: plugins/${DIRECTORY}/${PLUGINFILE}
        :documentation: true
        :examples: true

The snippet can take two options, `documentation` and `examples`. If a given
plugin does not have either of these in-code documentation objects,
documentation for either type can be disabled by omitting the option.

.. code-block:: rst

    .. ansibleautoplugin::
        :module: plugins/${DIRECTORY}/${PLUGINFILE}
        :documentation: true
