# edpm_ovs molecule<h1>

The edpm_ovs molecule uses a delegated driver to run against localhost.
As such this should only be executed on a disposable host. Alternatively, you
can use the vagrant driver for local development, see the vagrant section below.

The molecule test scenario files are single sourced in the common directory where
execution of some tasks is controlled by the `scenario_name`. The `scenario_name`
is defined respect scenario name directory. Note, `scenario_name` must match the
scenario directory name.

# Vagrant for local development<h2>

An alternative way to run these tests is using the vagrant driver. Vagrant will
Handle starting and destroying a test VM for each test scenario.
In order to use vagrant, the development machine will require following dependencies:

* Vagrant
* Libvirt
* Python

**_NOTE:_** Specific versions are omitted on purpose as every development machine is different.
# Install <h3>

Install dependencies mentioned above. It is a best practice to use [python virtual environment](https://virtualenv.pypa.io/en/latest/)
Install `molecule-plugins` python package
```
$ pip install 'molecule-plugins>=23.5.0'
```

**_NOTE:_** 23.5.0+ is required to avoid a bug in the vagrant driver where molecule utils were
not being imported correctly.

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
