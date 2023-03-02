EDPM Ansible
============

EDPM Ansible project repository. Contains Ansible playbooks, roles, and
plugins for use with EDPM.

WIP

Test ansible roles with molecule
--------------------------------

The tests are done with a common environment provided by the
`ci-framework <https://github.com/openstack-k8s-operators/ci-framework/>`__
project. This project provides all the requirement files and
configurations needed for setting up the environment to execute the
``molecule test`` command under the roles. It actually requires
``podman`` for executing the tests in a container.

For setting up the environment and executing the tests:

.. code:: bash

   $ make execute_molecule_tests

In case the ci-framework project is already cloned we can provide the
folder with ``ENV_DIR=/path/repository``

Note: the instruction ``execute_molecule`` has the
``TEST_ALL_ROLES=yes`` option in the podman command. It will execute
tests in all the roles. In case we want to execute the tests just in
modified roles we should delete it.

Build and push the openstack-ansibleee-runner container image
-------------------------------------------------------------

In order to test a local change to edpm-ansible, the ansible-runner container
image can be rebuilt and pushed to a container repository.

To build the image:

.. code:: bash

    $ export IMG_BASE_TAG=quay.io/<user>/openstack-ansibleee-runner
    $ make openstack_ansibleee_build

To push the image:

.. code:: bash

    $ export IMG_BASE_TAG=quay.io/<user>/openstack-ansibleee-runner
    $ make openstack_ansibleee_push

Depending on the repository, a ``podman login quay.io/<user>`` may be required
before pushing.

License
-------

Copyright 2023.

Licensed under the Apache License, Version 2.0 (the “License”); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

::

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an “AS IS” BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
