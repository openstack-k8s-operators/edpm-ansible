Testing roles
-------------

Testing roles with molecule
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Launch `make execute_molecule` to test all collections roles.

Roles can be tested individually using the *molecule-venv* created by running
`make execute_molecule`. The *molecule-venv* can also be manually created.

.. code-block:: console

    % python3 -m venv molecule-venv
    % source molecule-venv/bin/activate
    (molecule-venv) % pip install --upgrade pip
    (molecule-venv) % pip install molecule molecule-podman jmespath

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
