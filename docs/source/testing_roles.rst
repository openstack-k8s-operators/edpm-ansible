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

.. _`AnsibleEE`: testing_with_ansibleee
