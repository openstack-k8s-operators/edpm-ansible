Contributing Roles
------------------

Addition of new roles to the edpm-ansible collection is easy,
thanks to specialized development tooling and CI pipeline.
However, certain requirements must be met by any new role,
in order to ensure quality of the collection and a smooth operation
of software consuming it.

These requirements, outlined in the following document, go beyond
syntactic and functional correctness of the code.

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
Prerequisite tasks can be performed by roles added as dependencies, or by preceding roles
in the playbook, and declared in the role documentation.

If a newly developed role has a prerequisite that isn't already fulfilled
by any of the existing roles, and that is tangential to the primary purpose of the role,
another role can be contributed, fulfilling this prerequisite.

All roles must have an `argument specification`_ metadata, for all of their endpoints,
in the `roles/<NEWROLENAME>/meta/argument_specs.yml` file.

Argument specs allow for validity checks on arguments passed to the role in playbooks,
while also providing bulk of the information necessary for automated doc build.
This both prevents unnecessary bugs, and simplifies documentation upkeep.

Argument specification must contain definition of argument types, defaults and descriptions.

All uses of the role, across playbooks and other roles, must utilize one of the endpoints
defined in the argument specification metadata. No other variables than those defined
as part of an endpoint may be used for role invocation.

Properties of endpoints in argument specs are considered the source of truth.
When they are in conflict with the actual implementation, for example when the default
value of a variable in `roles/<NEWROLENAME>/defaults/main.yml` doesn't match
the definition in metadata, the conflict must be resolved.

Argument spec is essentially an API definition of the role. And as such must not be changed
without regard to backward compatibility, or dependent software.
Removal of variable from an argument spec must be preceded by a deprecation period.
The same goes for a renaming of a variable, with a period of time when both new, and original
names are accepted as part of the spec.

Variables added to an existing spec must be defined as optional and with appropriate defaults.

Variables
+++++++++

Role variables must be named in a way that both denotes their origin and their purpose.
Choice of a correct name is especially important when variable is expected to be used
outside of the role itself, or when it is a part of role arguments.

The standard variable name should take a following form:

.. code-block::

    edpm_<role_name>_<variable_purpose>

This format should virtually guarantee uniqueness. However conflicts may still occur.
It is up to the developer then to ensure that the resolution provides a readable result.

.. note::

    Since Ansible has several layers of variable precedence, with additional criterion of scope,
    the variable names should be checked for possible name space conflicts.

Default variable values should be constants, and contain as little logic as possible otherwise.
The variable defaults should therefore avoid Jinja templating or use of filters.

The default variable values must be viable, so the role can run without failure with no adjustment
from the operator, at least in minimal scenario. Invoking role without any parameters specified,
should be possible.

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
modules which do not properly implement change reporting, for example `ansible.builtin.cmd`.

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

`Privilege escalation`_, or `become`, must be used only when necessary.
Only tasks that have to be executed under root privileges should receive them.
Even if there are multiple tasks requiring root privileges, separated by others that can operate
under normal user, the entire role must not operate under them.

The same applies when using `become` to switch to a different, non-root, user.

Special care must be taken when using `become` with modules executing scripts,
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

This file must contain a title and an `include` directive of the automatically generated documentation
stub at the `../collections/osp/edpm/edpm_<NEWROLENAME>_role.rst` path.

.. code-block:: rst

    .. include::
        ../collections/osp/edpm/edpm_<NEWROLENAME>_role.rst


Optionally, you can write further information about the role,
such as section of examples and molecule tests, in the `docs/source/roles/role-<NEWROLENAME>.rst`.
However, this documentation must be updated manually, together with the role.

Create a new role
~~~~~~~~~~~~~~~~~

From within the project root, creating a skeleton for the new role.

.. code-block:: console

    $ ansible-galaxy init --role-skeleton=contribute/_skeleton_role_ --init-path=roles ${NEWROLENAME}

While the role skeleton contains the most common reasonable defaults, it may not be completely
suited for your use case. All unused, undesirable, or unnecessary remnants of the role skeleton,
must be removed before the role is published.

Before submitting a role for review, don't forget to run pre-commit hooks,
as well as molecule tests, if possible.

.. _`Ansible documentation`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks.html
.. _`argument specification`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html#role-argument-validation
.. _`Privilege escalation`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_privilege_escalation.html
.. _`conditionals`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_conditionals.html
.. _`changed_when`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html#defining-changed
.. _`failed_when`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html#defining-failure
