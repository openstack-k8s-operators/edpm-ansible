Testing roles
-------------

Testing roles with molecule
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Launch `make execute_molecule` to test all collections roles.

Roles can be tested individually using the *molecule-venv* created by running
`make execute_molecule`. The *molecule-venv* can also be created manually.

.. code-block:: console

    % python3 -m venv molecule-venv
    % source molecule-venv/bin/activate
    (molecule-venv) % pip install --upgrade pip
    (molecule-venv) % pip install -r molecule-requirements.txt

Afterwards the *molecule-venv* can be used to test a specific role.
Note however that not all roles can be tested in a container, some may require
a full-fledged VM. To make sure your role can be tested in a container,
check the `driver` section in the `molecule.yml` file.

.. code-block:: console

    (molecule-venv) % cd roles/edpm_<role>
    (molecule-venv) % molecule test # tests default scenario
    (molecule-venv) % molecule test --all
    (molecule-venv) % molecule test --scenario-name <specific scenario>

Alternatively you can test roles in with `AnsibleEE`_.

Writing molecule tests
~~~~~~~~~~~~~~~~~~~~~~

Molecule scenario configutration is made up of several files, all
stored in the `molecule/<scenario>/` directory.

* `molecule/default/molecule.yml` (mandatory):
    Main configuration file for molecule test, where the driver, platforms, images,
    provisioner, verifier etc. are specified. The most important part of the molecule.yml file
    is the `scenario` section where the `test_sequence` is being specified. E.g.:

    .. code-block:: yaml

        test_sequence:
        - dependency
        - destroy
        - create
        - prepare
        - converge
        - destroy

* `molecule/default/converge.yml` (mandatory):
    Corresponding to the converge step.
    Molecule will run this playbook to apply the role to the test instance(s).

* `molecule/default/prepare.yml`:
    Corresponding to the prepare step.
    It is used to perform any setup tasks that need to be done before your role can be applied.

* `molecule/default/verify.yml`:
    Corresponding to the verify step. This playbook is run to verify that the role did what was expected it to do.

The `create`, `destroy`, `dependency`, `side_effect` steps and other `configuration`_ are handled
internally by Molecule and do not require separate playbook files.
For instance, when Molecule executes the `destroy` step, it uses its internal logic,
and any configuration specified in `molecule.yml`, to destroy the test instances.

However they can be customized further based on the specific needs of the role.


.. _`AnsibleEE`: testing_with_ansibleee
.. _`configuration`: https://ansible.readthedocs.io/projects/molecule/configuration/
