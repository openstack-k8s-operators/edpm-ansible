===============
Playbook - nova
===============

.. literalinclude:: ../../../playbooks/nova.yml
   :language: YAML

Graceful shutdown
=================

The nova-compute Quadlet pairs Podman's ``StopTimeout`` with systemd's
``TimeoutStopSec`` so that Nova has time to finish its graceful shutdown.
``StopTimeout`` requires Podman 5.0 or newer.

With the defaults, the timeout ordering in seconds is::

   manager_shutdown_timeout = 160 (Nova)
   graceful_shutdown_timeout = 180 (Nova)
   StopTimeout = 200 (Podman)
   TimeoutStopSec = 220 (systemd)

Set ``edpm_nova_compute_stop_timeout`` through the dataplane Ansible variables
to change the Podman timeout. The systemd timeout is automatically set to this
value plus 20 seconds, allowing Podman to complete container cleanup before
systemd terminates it.

This variable does not change Nova's configuration. If you increase Nova's
``graceful_shutdown_timeout``, also increase ``edpm_nova_compute_stop_timeout``
to allow at least another 20 seconds. For example, a Nova graceful shutdown
timeout of 300 seconds needs ``edpm_nova_compute_stop_timeout: 320``, which
sets systemd's timeout to 340 seconds.
