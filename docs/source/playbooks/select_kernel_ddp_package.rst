====================================
Playbook - select_kernel_ddp_package
====================================

Runs the ``edpm_ddp_package`` role to select and validate DDP state.

In package mode on mutable hosts, the role configures the selected firmware
package, rebuilds initramfs, and may reload the ``ice`` module. In image mode
on bootc hosts, the role validates the profile baked into the image and the
matching payload in the currently running kernel's initramfs; it does not
modify firmware, run dracut, or reload the driver.

Set ``edpm_ddp_package`` to the selected profile directory before invoking the
playbook. The default is ``ddp``. For example, use ``ddp-comm`` when the
profile is baked under ``/lib/firmware/intel/ice/ddp-comm``:

.. code-block:: console

   ansible-playbook playbooks/select_kernel_ddp_package.yml \
       --extra-vars edpm_ddp_package=ddp-comm

For image-mode bootc customization and image-build verification, see
``dev-docs/bootc.md``. Runtime role validation does not customize the image.

.. literalinclude:: ../../../playbooks/select_kernel_ddp_package.yml
   :language: YAML
