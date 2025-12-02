Contributing Playbooks
----------------------

Addition of new playbooks to the edpm-ansible collection is easy,
thanks to specialized development tooling and CI pipeline.
However, certain requirements must be met by any new playbook,
in order to ensure quality of the collection and a smooth operation
of software consuming it.

These requirements, outlined in the following document, go beyond
syntactic and functional correctness of the code.

Where there isn't an explicit requirement, or recommendation,
provided by this document, the primary `Ansible documentation`_ is considered
to be the source of truth. When this document and official Ansible docs
are in substantial conflict, an issue should be raised.

Playbook design principles
~~~~~~~~~~~~~~~~~~~~~~~~~~

Playbook must not duplicate other playbooks.

If a newly developed playbook requires functionality not already present in existing
roles, a new role should be submitted in the same PR implementing it.

If possible, playbooks should not use tasks directly, only trough a role.

Playbooks must use following basic layout. Exposing variables, `edpm_override_hosts`,
`edpm_max_fail_percentage`, `edpm_any_errors_fatal`, and `edpm_playbook_environment`.

.. code-block:: YAML

    - name: NEWPLAYNAME
      hosts: "{{ edpm_override_hosts | default('all') }}"
      strategy: linear
      become: true
      any_errors_fatal: "{{ edpm_any_errors_fatal | default(true) }}"
      max_fail_percentage: "{{ edpm_max_fail_percentage | default(0) }}"
      environment: "{{ edpm_playbook_environment | default({}) }}"

This allows for more granular error handling and playbook application by operators.

Environment Variables
++++++++++++++++++++++

All playbooks must include the `environment` key at the top level (play level) that
references the `edpm_playbook_environment` variable. This variable allows operators
to set environment variables (such as proxy settings) that will be applied to all
tasks within the playbook.

The `edpm_playbook_environment` variable should be a dictionary containing
environment variable key-value pairs. If not defined, it defaults to an empty
dictionary, ensuring backward compatibility.

Example usage:

.. code-block:: YAML

    edpm_playbook_environment:
      HTTP_PROXY: "http://proxy.example.com:8080"
      HTTPS_PROXY: "http://proxy.example.com:8080"
      NO_PROXY: "localhost,127.0.0.1"
      http_proxy: "http://proxy.example.com:8080"
      https_proxy: "http://proxy.example.com:8080"
      no_proxy: "localhost,127.0.0.1"

Error handling
++++++++++++++

Errors encountered while executing playbooks should be handled in roles which
caused them.

Playbook test development
~~~~~~~~~~~~~~~~~~~~~~~~~

Playbooks themselves don't require tests. However, all of the roles they invoke do.
For further information about testing roles, please refer to the role contribution
section of this guide.


Documenting a new playbook
~~~~~~~~~~~~~~~~~~~~~~~~~~

Playbooks must accurately explain their effects in their documentation, with in-line
comments serving only as a supplement. In complex cases the documentation should link
to other material, but only as a source of additional information.


Primary playbook documentation file must reside at `docs/source/playbooks/<NEWPLAYBOOKNAME>.rst`
and must be a valid, readable rst document.

This file must contain a title and a `literalinclude` directive of the playbook itself
at the `../../../playbooks/<NEWPLAYBOOKNAME>.yml` path.


.. code-block:: rst

    .. literalinclude:: ../../../playbooks/bootstrap.yml
       :language: YAML

Optionally, you can write further information about the playbook,
such as section of examples, in the `docs/source/playbooks/<NEWPLAYBOOKNAME>.rst`.
However, this documentation must be updated manually, together with the playbook.

Create a new playbook
~~~~~~~~~~~~~~~~~~~~~

Each new playbook must follow form and basic outline of existing playbooks.

Before submitting a playbook for review, don't forget to run pre-commit hooks,
as well as molecule tests, if possible.

.. _`Ansible documentation`: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks.html
