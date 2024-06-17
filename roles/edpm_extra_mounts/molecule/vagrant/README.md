*********************************
Vagrant driver installation guide
*********************************

Requirements
============

* Vagrant
* Libvirt

Install
=======

Please refer to the `Virtual environment`_ documentation for installation best
practices. If not using a virtual environment, please consider passing the
widely recommended `'--user' flag`_ when invoking ``pip``.

.. _Virtual environment: https://virtualenv.pypa.io/en/latest/
.. _'--user' flag: https://packaging.python.org/tutorials/installing-packages/#installing-to-the-user-site

.. code-block:: bash

    $ pip install 'molecule-plugins[vagrant]\>=23.5.0'

23.5.0+ is required to avoid a bug in the vagrant driver where molecule utils were not being imported correctly.
This molecule env will be used for local development only and the default delegated env will be used for ci. As
As a result, it's important that this scenario merely contains the info required to prepare the VM and calls the prepare, converge, and verify playbooks from default to keep them in sync.
