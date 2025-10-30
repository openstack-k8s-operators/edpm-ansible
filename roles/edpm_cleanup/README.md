# edpm_cleanup Role

## Overview

The `edpm_cleanup` role provides a unified mechanism for cleaning up EDPM services and their associated resources. It automatically determines which services to clean up based on `edpm_services` - cleaning up all services in the state file that are NOT in `edpm_services`.

## Basic Usage

### Using the Cleanup Playbook

The cleanup role automatically cleans up all services that are NOT in `edpm_services`. If `edpm_services` is empty or not defined, all services will be cleaned up.

**Keep specific services (cleanup everything else):**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services=['nova', 'neutron_metadata']"
```

This will keep `nova` and `neutron_metadata`, and clean up all other services.

**With inventory/vars file:**
```yaml
# group_vars/all/cleanup.yml
edpm_services:
  - nova
  - neutron_metadata

# Then run:
ansible-playbook playbooks/cleanup.yml
```

**Keep only nova:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services=['nova']"
```

This will keep only `nova` and clean up all other services, including their containers (e.g., neutron_metadata containers, telemetry containers, etc.).

**Clean up everything:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services=[]"
```

This will clean up all services since `edpm_services` is empty.

### Cleanup During Deployment

You can also trigger cleanup during a deployment playbook by using the `edpm_cleanup` role:

```yaml
- hosts: edpm_nodes
  vars:
    edpm_services:
      - nova
      - neutron_dhcp
  roles:
    - osp.edpm.edpm_cleanup
    - edpm_neutron_ovn
```

The cleanup role will clean up all services NOT in `edpm_services`.

## The Cleanup Process

When you run the cleanup playbook:
1. Reads the state file to get all deployed services
2. Compares with `edpm_services` to determine which services to keep
3. Cleans up all services NOT in `edpm_services`
4. Displays which services will be cleaned up
5. For each service:
   - Reads the state file to get all containers
   - Verifies containers have `managed_by=edpm_ansible` label
   - For each container:
     - Stops and disables systemd service
     - Removes healthcheck service and timer
     - Removes systemd requires directory
     - Removes the container
   - Removes container startup config directories
   - Runs service-specific cleanup tasks (if available)
6. Updates state file to remove cleaned up services

## Files and Resources Cleaned Up

The cleanup process automatically removes:

**Container-related:**
- Container instances
- Systemd service files (`/etc/systemd/system/edpm_<container>.service`)
- Systemd healthcheck services (`/etc/systemd/system/edpm_<container>_healthcheck.service`)
- Systemd healthcheck timers (`/etc/systemd/system/edpm_<container>_healthcheck.timer`)
- Systemd requires directories (`/etc/systemd/system/edpm_<container>.service.requires`)

**Configuration files (automatic cleanup):**
- Container startup config directory and all JSON files within:
  - `/var/lib/edpm-config/container-startup-config/<service>/` (entire directory)
  - Contains all `<container>.json` files for the service
- Kolla config files for each container:
  - `/var/lib/kolla/config_files/<container>.json` (one per container)
- Healthcheck scripts:
  - `/var/lib/openstack/healthchecks/<service>`
- Service config directories:
  - `/var/lib/openstack/<service>`

**Configurable:**
- Additional paths can be cleaned up via `edpm_cleanup_generic_paths`
- Each path supports `__SERVICE_NAME__` placeholder that gets replaced with the actual service name

**Service-specific cleanup (optional):**
- Services can provide a `tasks/cleanup.yml` file in their role to clean up additional resources
- Examples: data directories, certificates, logs, etc.

## Configuration Variables

### Required Variables

- `edpm_services`: List of service names to keep (all others will be cleaned up)

### Optional Variables

```yaml
# Generic container variables (shared across roles)
edpm_container_state_file: /var/lib/edpm-config/deployed_services.yaml
edpm_container_startup_config_dir: /var/lib/edpm-config/container-startup-config
edpm_container_kolla_config_dir: /var/lib/kolla/config_files

# Remove container startup config directories during cleanup
edpm_cleanup_remove_config_dirs: true

# Remove containers with managed_by=edpm_ansible label that are not tracked in state file
edpm_cleanup_orphaned_containers: false

# Generic paths to clean up per service
# Use __SERVICE_NAME__ as a placeholder that will be replaced during cleanup
edpm_cleanup_generic_paths:
  - "/var/lib/openstack/healthchecks/__SERVICE_NAME__"
  - "/var/lib/openstack/__SERVICE_NAME__"
```

## Custom Cleanup Paths

Add custom paths to clean up per service:

```yaml
edpm_cleanup_generic_paths:
  - "/var/lib/openstack/healthchecks/__SERVICE_NAME__"
  - "/var/lib/openstack/__SERVICE_NAME__"
  - "/var/log/containers/__SERVICE_NAME__"
  - "/etc/__SERVICE_NAME__/custom-config"
```

The `__SERVICE_NAME__` placeholder is automatically replaced with the actual service name during cleanup.

## Service-Specific Cleanup

Services can provide a `tasks/cleanup.yml` file in their role to clean up additional resources:

```yaml
# roles/edpm_myservice/tasks/cleanup.yml
---
- name: Remove service-specific data
  become: true
  ansible.builtin.file:
    path: "{{ item }}"
    state: absent
  loop:
    - /var/cache/myservice
    - /etc/pki/myservice/special-cert.pem
```

The cleanup role will automatically look for and execute `tasks/cleanup.yml` in each service's role directory if it exists.

## Orphaned Container Cleanup

**What are orphaned containers?**
Containers with `managed_by=edpm_ansible` label that are not tracked in the state file. These can occur due to:
- Failed deployments
- Manual state file modifications
- Bugs or migration issues

**Enable orphaned cleanup:**
```yaml
edpm_cleanup_orphaned_containers: true
```

**How it works:**
1. Queries all containers with `managed_by=edpm_ansible` label
2. Compares against containers tracked in state file
3. Removes any containers not found in state file
4. Logs the list of orphaned containers before removal

**Use Cases:**
- Cleaning up after failed migrations
- Removing containers from manual testing
- Recovering from state file corruption
- General cleanup of untracked resources

## Container Label Requirements

Cleanup only removes containers with the `managed_by=edpm_ansible` label. This label is automatically added by the `edpm_container_manage` role.

All containers also include:
- `container_name=<container_name>`
- `config_data=<container_definition>` (full definition)

## Migrating from edpm_container_manage Cleanup

The old `edpm_container_manage_clean_orphans` feature is **deprecated**. Migrate to using `edpm_cleanup_orphaned_containers` in the `edpm_cleanup` role instead:

**Old approach (deprecated):**
```yaml
edpm_container_manage_clean_orphans: true
```

**New approach:**
```yaml
edpm_cleanup_orphaned_containers: true
```

Benefits of the new approach:
- State-file aware (knows which containers should exist)
- Better logging and visibility
- Unified cleanup mechanism
- More granular control

## Examples

### Cleanup All Services Except Nova

```yaml
- hosts: edpm_nodes
  vars:
    edpm_services:
      - nova
  roles:
    - osp.edpm.edpm_cleanup
```

### Cleanup During Deployment

```yaml
- hosts: edpm_nodes
  vars:
    edpm_services:
      - nova
      - neutron_dhcp
  roles:
    - osp.edpm.edpm_cleanup  # Clean up first
    - osp.edpm.edpm_neutron_ovn  # Then deploy
```

### Cleanup with Orphaned Container Removal

```yaml
- hosts: edpm_nodes
  vars:
    edpm_services:
      - nova
    edpm_cleanup_orphaned_containers: true
  roles:
    - osp.edpm.edpm_cleanup
```
