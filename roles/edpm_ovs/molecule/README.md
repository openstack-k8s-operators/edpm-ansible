# edpm_ovs molecule<h1>

The edpm_ovs molecule scenarios use the delegated driver
to run against localhost. As such this should only be executed
on a disposable host. See Vagrant section below for an alternative way
to run these tests during development.
Most of the test stages for different test scenarios are single sourced
in the common directory. The execution of the single sourced test stages
tasks are controlled based on the `scenario_name` whenever needed.

# Vagrant<h2>

An alternative way to run these tests is using the vagrant driver. Vagrant will
start a test VM and run the test on that VM instance instead of the
localhost. In order to use vagrant, the development machine will require
following dependencies:

* Vagrant
* Libvirt
* Python

# Install <h3>

Please refer to the `Virtual environment`_ documentation for installation best
practices. If not using a virtual environment, please consider passing the
widely recommended `'--user' flag`_ when invoking ``pip``.

_Virtual environment: https://virtualenv.pypa.io/en/latest/
_'--user' flag: https://packaging.python.org/tutorials/installing-packages/#installing-to-the-user-site

```
$ pip install 'molecule-plugins[vagrant]\>=23.5.0'
```

23.5.0+ is required to avoid a bug in the vagrant driver where molecule utils were
not being imported correctly. This molecule env will be used for local development
only and the default delegated env will be used for ci. As a result, it's important
that this scenario merely contains the info required to prepare the VM and calls
the prepare, converge, and verify playbooks from default to keep them in sync.

Lastly, to run a test scenario with the vagrant driver replace the `driver` and
`platform` sections inside the `molecule.yml` located in each test scenario directory.
The exact excerpt:

```
driver:
  name: vagrant
  provider:
    name: libvirt
  provision: no
  parallel: true
  default_box: 'generic/centos9s'
platforms:
- name: compute-1
  memory: 1024
  cpus: 2
  provider_options:
    cpu_mode: 'host-passthrough'
    nested: true
    machine_type: 'q35'
  groups:
    - compute
```
