Contributing plugins
--------------------

Plugins and modules contributed to the edpm-ansible are placed in the `plugins` directory,
from the root of this repository. Both must be developed with reference to
best Python development practices, with emphasis on Ansible specifics.

As with roles, the plugins should be specialized and adhere to the venerable:

    'Doing one thing, and doing it well.'

There is a certain level of confusion regarding the nomenclature. This is partly
caused by the directory structure used by ansible to organize plugins.

.. note::

    There are many more plugin types, including inventory.
    We don't really need to worry about them however.

For our purposes, we can consider modules to be a subset of plugins, just like lookup plugins,
inventory plugins and callback plugins. This approach follows the directory structure of both collections,
and of the default ansible paths for plugins, and thus is easier to follow.

.. code-block::

    /usr/share/ansible/plugins/
    ├── action
    ├── become
    ├── cache
    ├── callback
    ├── cliconf
    ├── connection
    ├── doc_fragments
    ├── filter
    ├── httpapi
    ├── inventory
    ├── lookup
    ├── modules <==== Here be modules!
    ├── module_utils
    ├── netconf
    ├── strategy
    ├── terminal
    ├── test
    └── vars

Therefore, we will use the term **plugin** to denote the general set of auxiliary software used by ansible,
and **module** for those plugins which can be used to perform operations on the target machine.

Before developing plugins first check if the use case isn't already supported by
an existing plugin in either the `ansible` or `commmunity` name space. Alternatively, it may be possible
to derive a new plugin, from an existing counterpart. However, this may cause issues with long term maintenance,
as the parent plugin characteristics may change over time.

.. note::

    Each plugin must be used in at least one role.
    Orphaned plugins will be deprecated, and subsequently removed,
    unless there is a valid reason not to.

Plugins should use existing ansible `module_utils`_ resources, if possible.

Plugin structure
~~~~~~~~~~~~~~~~

Ansible modules are for all intents and purposes specialized, standalone, python scripts.
With that comes certain burden, as they do not entirely follow OOP design principles,
have to be tested with numerous mocks and require a custom virtual env to work.

Furthermore, Ansible places hard `requirements`_ on some aspects of the script structure.
These are, for the most part, related to the metadata needed by ansible runtime to properly
handle usage of the plugins. Without them, the plugin can not function correctly.

Even more `strict requirements`_ are placed on modules. This guide will only focus on parts,
of these requirements that are most relevant to development of cloud.

Each module must have a well defined `argument spec`_, with variable types, default values
and whether or not the arguments are optional. This provides additional checking mechanism
for module call in ansible playbooks.

.. code-block:: python

    module = AnsibleModule(
        argument_spec={
            'are_arg_specs_necessary': {
                'type': 'bool',
                'default': True,
            }
        }
    )

.. note::

    You can define argument specs as a yaml dictionary object within the `DOCUMENTATION` element.

Check mode
~~~~~~~~~~

Modules which do not affect the target machine must be marked as available for `check mode`_.
At the same time, a module running in check mode is resposible for not performing any
actions that may affect the target machine.

Plugin testing
~~~~~~~~~~~~~~

All plugins must have a dedicated unit test module, covering, at least,
the primary use case and the most probable set of parameters.
Unit tests should cover use case that is present in one of the roles utilizing
the plugin. Percentual coverage of the code is not a consideration by itself.


.. note::

    Further reading: `RH plugin best practices`_

.. _`requirements`: https://docs.ansible.com/ansible/6/dev_guide/developing_plugins.html#writing-plugins-in-python
.. _`strict requirements`: https://docs.ansible.com/ansible/6/dev_guide/developing_modules_documenting.html#module-format-and-documentation
.. _`check mode`: https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#declaring-check-mode-support
.. _`argument spec`: https://docs.ansible.com/ansible/6/dev_guide/developing_program_flow_modules.html#argument-spec
.. _`module_utils`: https://docs.ansible.com/ansible/latest/reference_appendices/module_utils.html
.. _`RH plugin best practices`: https://redhat-cop.github.io/automation-good-practices/#_plugins_good_practices
