# edpm_leapp_upgrade role

## Overview

The `edpm_leapp_upgrade` role performs an in-place OS upgrade from RHEL 9 to RHEL 10
on EDPM nodes using the [Leapp](https://leapp-project.github.io/) framework.

The role is split into three sequential phases, each with a dedicated Ansible tag:

| Phase | Tag | Description |
|---|---|---|
| Pre-validation | `leapp_validate` | Checks OS version and network configuration readiness |
| Prepare | `leapp_prepare` | Installs prerequisite packages and the leapp tool |
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
| `edpm_leapp_upgrade_base_packages` | `""` | Space- or comma-separated list of prerequisite packages to install before leapp |
| `edpm_leapp_packages` | `"leapp-upgrade"` | Leapp package(s) to install |

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

### Pre-validation (`leapp_validate`)

1. Gathers distribution facts if not already present.
2. Asserts that the host is running **RHEL 9** — fails with a descriptive message otherwise.
3. Checks that no NetworkManager connections still use legacy `ifcfg` (sysconfig) files; fails if any are found.

### Prepare (`leapp_prepare`)

1. Runs `edpm_leapp_upgrade_repo_init_command` to enable the target-OS repositories (skipped if the variable is empty).
2. Installs any packages listed in `edpm_leapp_upgrade_base_packages` (skipped if the variable is empty).
3. Installs the package(s) in `edpm_leapp_packages` (default: `leapp-upgrade`).

### Run (`leapp_run`)

1. Executes `leapp upgrade` (with `--debug` when `edpm_leapp_upgrade_debug` is `true`) to download the RHEL 10 packages and prepare the initramfs.
2. Creates the directory `/var/lib/openstack/reboot_required/`.
3. Touches `/var/lib/openstack/reboot_required/leapp_upgrade` as a marker so that the reboot can be triggered by an external orchestrator at the appropriate time.

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
