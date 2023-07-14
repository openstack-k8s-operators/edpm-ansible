Contributing Roles
------------------

Adding roles into this project is easy and starts with a compatible skeleton.


Create a new role
~~~~~~~~~~~~~~~~~

From with the project root, creating a skeleton for the new role.

.. code-block:: console

    $ ansible-galaxy init --role-skeleton=contribute/_skeleton_role_ --init-path=roles ${NEWROLENAME}

Finally add a role documentation file at
`docs/source/roles/role-${NEWROLENAME}.rst`. This file will need to contain
a title and an include directive of the automatically generated documentation
stub at the `../collections/osp/edpm/edpm_<NEWROLENAME>_role.rst` path.

Optionally you can write further information about role operation.
Including section of examples and molecule tests.

Testing roles with molecule
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Launch `make execute_molecule` to test all collections roles.

Roles can be tested individually using the *molecule-venv* created by running
`make execute_molecule`. The *molecule-venv* can also be manually created.

.. code-block:: console

    % python3 -m venv molecule-venv
    % source molecule-venv/bin/activate
    (molecule-venv) % pip install --upgrade pip
    (molecule-venv) % pip install -r ../../molecule-requirements.txt

The `edpm_timezone` role molecule directory is a working example to
borrow from when configuring the molecule directory for a new role.
Copying the default `molecule.yml` file from `edpm_timezone` should
be sufficient for the `molecule test` command to work.

.. code-block:: console

    $ cd roles/${NEWROLENAME}/molecule/default
    $ cp ../../../edpm_timezone/molecule/default/molecule.yml molecule.yml

Use the *molecule-venv* to test a specific role.

.. code-block:: console

    (molecule-venv) % cd roles/edpm_<role>
    (molecule-venv) % molecule test # tests default scenario
    (molecule-venv) % molecule test --all
    (molecule-venv) % molecule test --scenario-name <specific scenario>

Testing roles with ansibleee
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

edpm-ansible is included in the openstack-ansibleee-runner container image,
which is key component used by the dataplane-operator that deploys EDPM
nodes. The dataplane-operator's CRD includes support for specifying additional
volume mounts for the ansibleee pods, which provides a mechanism for accessing
a local copy of edpm-ansible. This makes it possible to develop and test local
changes edpm-ansible without having to build and deploy a new
openstack-ansibleee-runner container image.

.. toctree::

   testing_with_ansibleee

Contributing plugins
~~~~~~~~~~~~~~~~~~~~

All plugins contributed to the edpm-ansible can be found in the
`plugins` directory, from the root of this project.
When contributing a plugin, make sure to also add documentation in the
`docs/source/plugins` folder. All documentation added to this folder will be
automatically indexed and rendered via `sphinx`.
