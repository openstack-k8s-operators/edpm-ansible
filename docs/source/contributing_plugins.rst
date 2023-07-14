Contributing plugins
--------------------

Plugins contributed to the edpm-ansible are placed in the `plugins` directory,
from the root of this repository. Plugins must be developed with reference to
best Python development practices, with emphasis on Ansible specifics.

.. note::
    Each plugin must be used in at least one role.
    Orphaned plugins will be deprecated, and subsequently removed,
    unless there is a valid reason not to.



Plugin testing
~~~~~~~~~~~~~~

All plugins must have a dedicated unit test module, covering, at least,
the primary use case and most probable set of parameters.
Unit tests should cover use case that is present in one of the roles utilizing
the plugin. Percentual coverage of the code is not a consideration by itself.
