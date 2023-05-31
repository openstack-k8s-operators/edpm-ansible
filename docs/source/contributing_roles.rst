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
a title and an include directive of the automatically generated documentation
stub at the `../collections/osp/edpm/edpm_<NEWROLENAME>_role.rst` path.

Optionally you can write further information about role operation.
Including section of examples and molecule tests.

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
