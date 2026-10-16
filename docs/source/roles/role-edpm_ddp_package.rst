===========================
Role - edpm_ddp_package
===========================

Usage
~~~~~

This Ansible role supports two EDPM deployment modes: package mode on mutable
hosts and image mode on bootc hosts.

In package mode, the role reads the latest matching ``ice*.pkg*`` file under
``edpm_ddp_package_path/<edpm_ddp_package>``, configures the selected package
at ``ddp/ice.pkg``, rebuilds initramfs, and optionally reloads the configured
driver module. The default ``edpm_ddp_package`` value is ``ddp``.

In image mode, ``edpm_ddp_package`` identifies the DDP profile directory baked
into the bootc image (for example, ``ddp-comm``). The role selects the latest
matching package in that directory, checks that
``/lib/firmware/intel/ice/ddp/ice.pkg`` resolves to that package, then uses
``uname -r`` and ``lsinitrd -f`` to compare the canonical runtime file's
SHA-256 with its payload in
``/usr/lib/modules/<running-kernel>/initramfs.img``. A validation failure tells
the user to rebuild and boot an image with the required state. Image mode is
read-only: the role does not install or change a file or symlink, run dracut,
or reload a module. This check validates only the booted image's initramfs
payload; it does not validate hardware compatibility or actual driver
acceptance.

For image-mode bootc customization and independent image-build verification,
see ``dev-docs/bootc.md``. Role validation does not build or customize the
bootc image.

Example role invocation for a ``ddp-comm`` profile:

.. code-block:: yaml

    - name: "Configure DDP Package"
      include_role:
        name: "osp.edpm.edpm_ddp_package"
      vars:
        edpm_ddp_package: "ddp-comm"
