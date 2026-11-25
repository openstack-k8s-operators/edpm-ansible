# edpm_leapp_upgrade role

## Overview

The `edpm_leapp_upgrade` role performs an in-place OS upgrade from RHEL 9 to RHEL 10
on EDPM nodes. It is a thin EDPM wrapper around the upstream
[infra.leapp](https://github.com/redhat-cop/infra.leapp) collection, which is shipped
in the AnsibleEE image (see `openstack_ansibleee/ansibleee-requirements.yaml`).

The role keeps only the EDPM-specific glue:

- pre-flight validation of the node (OS version, NIC naming, nmstate migration,
  stale leapp job logs),
- the collection FQCN indirection (`EDPM_LEAPP_COLLECTION`, defaulting to
  `infra.leapp`, mirroring the `EDPM_SYSTEMROLES` pattern used for system roles),
- a small set of EDPM-sane defaults.

Everything else is delegated to the `infra.leapp.analysis` and `infra.leapp.upgrade`
roles. All upstream `leapp_*` variables can be set directly through `ansibleExtraVars`
and are documented in the
[infra.leapp README](https://github.com/redhat-cop/infra.leapp/blob/main/README.md);
the wrapper does not shadow them.

The role is split into three sequential phases, each with a dedicated Ansible tag:

| Phase | Tag | Description |
|---|---|---|
| Pre-validation | `leapp_validate` | Checks OS version, NIC naming and network configuration readiness, archives stale leapp job logs |
| Analysis | `leapp_analysis` | Runs `infra.leapp.analysis` (`leapp preupgrade`) and fails when inhibitors are reported |
| Run | `leapp_run` | Runs `infra.leapp.upgrade`: installs packages, runs `leapp upgrade`, **reboots the node**, waits for the upgrade to finish, then runs post-upgrade validation and cleanup |

## Requirements

- RHEL 9.6 or newer on the node being upgraded
- Network connections must be managed by **nmstate/NetworkManager**; legacy `ifcfg` files must be migrated before the upgrade runs
- Predictable NIC naming: the kernel command line must not contain `net.ifnames=0`
- ansible-core 2.16 or newer (required by the `infra.leapp` collection; the AnsibleEE image ships 2.16.1+)
- The `infra.leapp` collection available to the runner; it is part of the image built from `openstack_ansibleee/`

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
      value: "18000"
  ansibleLimit: compute-xxxxx-0
  ansibleExtraVars:
    leapp_upgrade_type: cdn
```

```bash
oc apply -f leapp-upgrade.yml
```

`RUNNER_IDLE_TIMEOUT` must comfortably exceed the time the whole upgrade takes:
`infra.leapp.upgrade` waits up to `leapp_upgrade_timeout` (14400 s by default) for
the node to return after the reboot, so values below that kill the job mid-upgrade.

## Variables

### `defaults/main.yml`

| Variable | Default | Description |
|---|---|---|
| `edpm_leapp_upgrade_validate` | `true` | Run the EDPM pre-flight validation phase |
| `edpm_leapp_upgrade_analysis` | `true` | Run the `infra.leapp.analysis` pre-upgrade analysis; also decides whether `infra.leapp.upgrade` requires the analysis report to be present |
| `edpm_leapp_upgrade_fail_on_inhibitors` | `true` | Fail when the pre-upgrade analysis reports inhibitors |
| `edpm_leapp_upgrade_source_major_version` | `"9"` | Minimum source RHEL major version |
| `edpm_leapp_upgrade_source_min_version` | `"9.6"` | Minimum source RHEL minor version |
| `edpm_leapp_upgrade_clean_stale_logs` | `true` | Archive a stale `/var/log/leapp/ansible_leapp_*.log` from an aborted run; the upstream roles refuse to start otherwise |
| `edpm_leapp_upgrade_copr_enabled` | `false` | Enable a Copr repository on the node before `infra.leapp` installs the leapp packages |
| `edpm_leapp_upgrade_copr_project` | `"@oamg/leapp"` | Copr project to enable, in `owner/project` form |
| `edpm_leapp_upgrade_copr_chroot` | `"epel-{{ ansible_facts['distribution_major_version'] }}-$basearch"` | Copr chroot to pull builds from |
| `edpm_leapp_upgrade_copr_remove_after_upgrade` | `true` | Remove the Copr repository again once `infra.leapp.upgrade` has finished |
| `edpm_leapp_upgrade_copy_reports` | `true` | Forwarded to `leapp_copy_reports`; copy leapp reports to the controller |
| `edpm_leapp_upgrade_workdir_controller` | `"$HOME/edpm_leapp_reports"` | Forwarded to `leapp_workdir_controller`; where collected reports are written on the controller |

All other `leapp_*` variables of the upstream roles (for example `leapp_upgrade_type`,
`leapp_preupg_opts`, `leapp_env_vars`, `leapp_local_repos_pre`, `leapp_upgrade_timeout`
or `leapp_satellite_organization`) can be passed directly through `ansibleExtraVars`.

## Testing a leapp build from Copr

`infra.leapp` has no Copr support: it installs `leapp-upgrade` with
`ansible.builtin.package` from whatever repositories are already enabled on the
node. To test a pre-release leapp, set `edpm_leapp_upgrade_copr_enabled` and the
role configures the Copr repository before either upstream role runs:

```yaml
ansibleExtraVars:
  edpm_leapp_upgrade_copr_enabled: true
  edpm_leapp_upgrade_copr_project: "@oamg/leapp"
```

This is the equivalent of `dnf copr enable "@oamg/leapp" epel-9-x86_64`, written
straight to `/etc/yum.repos.d/_copr:copr.fedorainfracloud.org:group_oamg:leapp.repo`
rather than shelling out to the dnf Copr plugin. Writing the file directly keeps
the task idempotent, drops the `dnf-plugins-core` dependency, and avoids the
plugin's chroot guessing — it derives `rhel-9-x86_64` from `/etc/os-release` and
fails, because `@oamg/leapp` has no RHEL chroot. The chroot therefore defaults to
the **source** EPEL chroot (`epel-9` when upgrading RHEL 9 to RHEL 10);
`@oamg/leapp` builds for `epel-7`, `epel-8` and `epel-9` only.

Two things worth knowing:

- The repository file carries `skip_if_unavailable=1`, matching what Copr itself
  publishes. An unreachable Copr therefore does not fail the run, it silently
  falls back to the distribution build of `leapp-upgrade`. Check the installed
  NEVRA if you need to be certain the Copr build was used.
- The repository stays enabled for the whole upgrade — the upgrade phase
  reinstalls the leapp packages — and is removed afterwards by
  `edpm_leapp_upgrade_copr_remove_after_upgrade`, so an EPEL 9 Copr is not left
  configured on an upgraded RHEL 10 node. Removal matches on the repository id
  and file name, neither of which depends on the chroot.

Copr builds are not supported by Red Hat; use this for development and testing
only.

## Tags

Run only selected phases by passing `--tags`:

```bash
# Validate only
ansible-playbook playbooks/leapp_upgrade.yml --tags leapp_validate

# Analysis only
ansible-playbook playbooks/leapp_upgrade.yml --tags leapp_analysis

# Run the upgrade (includes the reboot and post-upgrade tasks)
ansible-playbook playbooks/leapp_upgrade.yml --tags leapp_run
```

## Notes on the reboot and the reports

- The node reboots **inside** the `leapp_run` phase: `infra.leapp.upgrade` reboots the
  node itself and waits for the upgrade to complete. The role no longer stages a
  `/var/lib/openstack/reboot_required/` marker and `edpm_reboot` plays no part in the
  OS upgrade workflow.
- When reports are copied to the controller they land under
  `edpm_leapp_upgrade_workdir_controller`, which defaults to
  `$HOME/edpm_leapp_reports` (`/runner/edpm_leapp_reports` in the AnsibleEE pod).
  The upstream default, `{{ playbook_dir }}`, cannot be used in EDPM: the playbook
  is served from the collection mounted read-only under
  `/usr/share/ansible/collections`, so the copy fails with
  `[Errno 30] Read-only file system`. Point the variable at a mounted path if the
  reports need to outlive the pod; the reports also stay on the node in
  `/var/log/leapp`. If the configured directory cannot be created the role warns
  and collects the reports in `$TMPDIR/edpm_leapp_reports` instead of failing the
  upgrade.
- `infra.leapp.common` refuses to start while `/var/log/leapp/ansible_leapp_analysis.log`
  or `/var/log/leapp/ansible_leapp_upgrade.log` exists from an aborted run. The
  validation phase archives such files (renaming them with a timestamp suffix) so a
  retried deployment is not blocked by the stale lock. Set
  `edpm_leapp_upgrade_clean_stale_logs: false` to keep the upstream behaviour.

## Example: Pre-migration Network Check

Before running this role, migrate any `ifcfg` connections to nmstate. You can check
for legacy connections with:

```bash
nmcli -f name,uuid,filename connection show | grep sysconfig
```

If any connections are listed, migrate them:

```bash
nmcli connection migrate
```
