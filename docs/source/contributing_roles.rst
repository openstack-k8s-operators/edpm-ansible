Contributing Roles
------------------

Addition of new roles to edpm-ansible collection is easy, thanks
to specialized development tooling and CI pipeline.
However, certain requirements must be met by any new role,
in order to ensure quality of the collection and a smooth operation
of software consuming it.

These requirements, outlined in the following document, go beyond
syntactic and functional correctness of the code. ....

Where there isn't an explicit requirement, or recommendation,
provided by this document, the primary `Ansible documentation`_ is considered
to be the source of truth. When this document and official Ansible docs
are in substantial conflict, an adjustment should be made.

Role design principles
~~~~~~~~~~~~~~~~~~~~~~

Roles are software like any other. However, ansible allows considerable
freedom when it comes to ways for doing even very simple things.
Each role should represent a self-contained unit of functionality
and follow the venerable principle of 'Doing one thing, and doing it well.'

Therefore, roles must not reimplement functionality already present in other roles,
or functionality that is not part of their intended purpose.
Prequisite tasks can be performed by roles added as dependencies, or by preceding roles
in the playbook, and declared in the role documentation.

If a newly developed role has a prerequisite that isn't already fulfilled
by any of the existing roles, and that is tangential to the primary purpose of the role,
another role can be contributed, fulfilling this prerequisite.

All roles must have an `argument specification`_ metadata, for all of their endpoints,
in the `roles/<NEWROLENAME>/meta/argument_specs.yml` file.

Argument specs allow for validity checks on arguments passed to the role in playbooks,
while also providing bulk of the information neccessary for automated doc build.
This both prevents unnecessary bugs, and simplifies documentation upkeep.

Argument specification must contain definition of argument types, defaults and descritptions.

All uses of the role, across playbooks and other roles, must utilize one of the endpoints
defined in the arugment specification metadata. No other variables than those definined
as part of an endpoint may be used for role invocation.

Properties of endpoints in argument specs are considered the source of truth.
When they are in conflict with the actual implementation, for example when the default
value of a variable in `roles/<NEWROLENAME>/defaults/main.yml` doesn't match
the definition in metadata, the conflict must be resolved.

Conditionals
++++++++++++

Conditions for execution of tasks must not use Jinja templating, as that is already implicit
in the construct and can impact readability.

.. code-block:: yaml

    - name: Look! No Jinja!
      debug:
        msg: Just read the title!
      when: not needs_jinja

Multiple conditions can be used at the same time, using boolean operators.
However, the resulting increase in complexity must be considered.
Even though you know the purpose behind every single condition, and meaning of every variable,
your colleagues may not. Nor will you in a couple of weeks.

.. code-block:: yaml

    - name: This task is super important
      debug:
        msg: If this message doesn't reach the operator, we are in serious trouble.
      when:
        - stars_align
        - openstack_stuck | bool or penguins == "marching"
        - not coder_knows_what_is_going_on

Tasks
+++++

All tasks of the role must accurately report whether or not they have performed
changes on the target machine. This is especially important when tasks invoke
modules which do not properly implement change reporting, for example `ansible.buildin.cmd`.

In these cases, `changed_when`_ and `failed_when`_ constructs must be used.
Just like other `conditionals`_, the conditionals used to define change and failure should
emphasize readability and simplicity.

.. note::
    If possible, roles should avoid modules wrapping scripts,
    such as `ansible.builtin.cmd` and `ansible.builtin.shell`. Since they are inherently
    less secure and harder to debug.
    In most cases there already is a built-in module, or a collection module,
    providing the same functionality.

Tasks must have a descriptive name, ideally without use of templating.

Error handling
++++++++++++++

Roles must accurately report all failures, with a concise, yet descriptive, message that can point
administrator in the right direction. Error messages should not include complex data structures,
like dictionaries or lists, in order to strain on human parser.

Privilege escalation
++++++++++++++++++++

`Privilege escalation`_, or `become`, must be used only when neccessary.
Only a tasks that have to be executed under root privileges should receive them.
Even if there are multiple tasks requiring root privileges, separated by others that can operate
under normal user, the entire role must not operate under them.

The same applies when using `become` to switch to a different, non-root, user.

Special care must be taken when using become with modules executing scripts,
like the `ansible.builtin.cmd`. And when invoking other roles.

Role test development
~~~~~~~~~~~~~~~~~~~~~

Roles must have molecule tests with at least one scenario representing the most common
expected usage. Tests must be included in the CI layout and executed after every
change that may conceivably affect role function.

Molecule tests should be generated with tooling provided in the repository, or derived
from a test suite of an existing role.

Tests should utilize either podman, or delegated driver, with podman given precedence.
Delegated driver, or other drivers, should be used only when it isn't possible to properly
test the role inside of a container.

Roles with multiple execution paths should have multiple scenarios. All molecule scenarios,
apart from the default, must have a descriptive name.


Documenting a new role
~~~~~~~~~~~~~~~~~~~~~~

Roles must accurately explain their effects in their documentation, with in-line
comments serving only as a supplement. In complex cases the documentation should link
to other material, but only as a source of additional information. Beware the link rot.

Furthermore, documentation should include an example of an ideal use case.

Primary role metadata, placed in the `roles/<NEWROLENAME>/meta/main.yml`,
must include declaration of ownership, license, minimal ansible version and dependencies.
The license must be compatible with the primary repo license `Apache v2.0`.

The metadata should also include information about system compatibility.

Primary role documentation file must reside at `docs/source/roles/role-<NEWROLENAME>.rst`
and must be a valid, readable rst document.

This file must contain a title and an include directive of the automatically generated documentation
stub at the `../collections/osp/edpm/edpm_<NEWROLENAME>_role.rst` path.

.. code-block:: rst

    .. include::
        ../collections/osp/edpm/edpm_<NEWROLENAME>_role.rst


Optionally, you can write further information about the role,
such as section of examples and molecule tests, in the `docs/source/roles/role-<NEWROLENAME>.rst`.
However, this documentation must be updated manually, together with the role.

Create a new role
~~~~~~~~~~~~~~~~~

From with the project root, creating a skeleton for the new role.

.. code-block:: console

    $ ansible-galaxy init --role-skeleton=contribute/_skeleton_role_ --init-path=roles ${NEWROLENAME}

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


.. _`Ansible documentation`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks.html
.. _`argument specification`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html#role-argument-validation
.. _`Privilege escalation`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_privilege_escalation.html
.. _`conditionals`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_conditionals.html
.. _`changed_when`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html#defining-changed
.. _`failed_when`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html#defining-failure
