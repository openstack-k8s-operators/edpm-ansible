====================================
Playbook - select_kernel_ddp_package
====================================

Installs ddp package using edpm_ddp_package role.

The package must be specified before playbook execution using the `edpm_ddp_package` variable.
Otherwise the default value "ddp" is used.

.. literalinclude:: ../../../playbooks/select_kernel_ddp_package.yml
   :language: YAML
