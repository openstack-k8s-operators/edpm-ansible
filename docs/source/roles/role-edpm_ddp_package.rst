===========================
Role - edpm_ddp_package
===========================

Usage
~~~~~

This Ansible role allows to do the following tasks:

* Configure the user provided DDP Package. Reads latest
  available version of required DDP package and configure
  it.

* Remove existing DDP package configuration.

* Checks the DDP package file format either normal or
  compressed and configures the user provided DDP package.

  Note: `edpm_ddp_package` parameter is set to 'ddp' by
  default,
  Here is an example of a playbook:

.. code-block:: YAML

    - name: "Configure DDP Package"
      include_role:
        name: "osp.edpm.edpm_ddp_package"
      vars:
        edpm_ddp_package: "ddp-comm"
