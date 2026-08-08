# edpm_leapp_upgrade role

## Overview

The `edpm_leapp_upgrade` role performs an in-place OS upgrade from RHEL 9 to RHEL 10
on EDPM nodes using the [Leapp](https://leapp-project.github.io/) framework.

The role is split into three sequential phases, each with a dedicated Ansible tag:

| Phase | Tag | Description |
|---|---|---|
| Prepare | `leapp_prepare` | Runs init commands and installs prerequisite packages and the leapp tool |
| Pre-validation | `leapp_validate` | Checks OS version and network configuration readiness |
| Run | `leapp_run` | Executes the upgrade and stages a reboot marker |

## Requirements

- RHEL 9 (any minor version)
- Network connections must be managed by **nmstate/NetworkManager**. Legacy `ifcfg` files must be migrated before the upgrade runs

## Basic Usage

```yaml
---
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneDeployment
metadata:
  name: leapp-upgrade
spec:
  backoffLimit: 1
  deploymentRequeueTime: 15
  nodeSets:
  - openstack-edpm
  preserveJobs: true
  servicesOverride:
  - leapp-upgrade
  env:
    - name: RUNNER_IDLE_TIMEOUT
      value: "3600"
  ansibleLimit: compute-xxxxx-0
  ansibleExtraVars:
    edpm_leapp_upgrade_repo_init_command: |
      dnf copr -y enable @oamg/leapp
    edpm_leapp_upgrade_init_command: |
      nmcli conn migrate
```

```bash
oc apply -f leapp-upgrade.yml
```

## Variables

### `defaults/main.yml`

| Variable | Default | Description |
|---|---|---|
| `edpm_leapp_upgrade_debug` | `true` | Pass `--debug` to the `leapp upgrade` command |
| `edpm_leapp_upgrade_packages` | `"leapp-upgrade"` | Leapp package(s) to install |
| `edpm_leapp_upgrade_repo_init_command` | `""` | Command to run for initialising the leapp upgrade repository (empty = skip) |
| `edpm_leapp_upgrade_init_command` | `""` | Command to run pre leapp (empty = skip) |

### Required Variables

## Tags

Run only selected phases by passing `--tags`:

```bash
# Validate only
ansible-playbook upgrade.yml --tags leapp_validate

# Prepare only (install packages)
ansible-playbook upgrade.yml --tags leapp_prepare

# Run the upgrade (downloads packages and stages reboot)
ansible-playbook upgrade.yml --tags leapp_run
```

## What Each Phase Does

### Prepare (`leapp_prepare`)

Runs any configured init commands, enables the target-OS repositories, and
installs the prerequisite and `leapp-upgrade` packages. See the
[Variables](#variables) section for how to customize repos, commands, and
package pinning.

### Pre-validation (`leapp_validate`)

Confirms the node is actually eligible for the upgrade and fails fast with
a descriptive error.

### Run (`leapp_run`)

Executes `leapp upgrade` to download the target-OS packages and prepare the initramfs, then stages a
reboot marker for the orchestration layer.

> **Note:** The role itself does **not** reboot the node. The reboot marker is read by the EDPM orchestration layer, which schedules the reboot at a controlled point in the upgrade workflow.

## Example: Pre-migration Network Check

Before running this role, migrate any `ifcfg` connections to nmstate. You can check for legacy connections with:

```bash
nmcli -f name,uuid,filename connection show | grep sysconfig
```

If any connections are listed, migrate them:

```bash
# Example: migrate a connection named "eth0"
nmcli connection migrate
```
