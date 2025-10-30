# Service Cleanup with State Tracking

## Overview

This document explains how to use the service cleanup functionality. **Services are represented by playbooks, not individual roles**. When a playbook deploys multiple roles, they can all be tracked under a single service name for unified lifecycle management.

## State File Tracking

The `edpm_container_standalone` role automatically tracks deployed services in `/var/lib/edpm-config/deployed_services.yaml`.

**Key Concept:** Services are defined at the playbook level, not the role level. A service like "nova" includes all containers deployed by the nova.yml playbook, including dependencies like iscsid and multipathd.

### Automatic Registration

When a role uses `edpm_container_standalone`, its containers are automatically registered in the state file:

```yaml
- name: Deploy my service
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_container_standalone_service: myservice
    edpm_container_standalone_container_defs:
      myservice_container1: {...}
      myservice_container2: {...}
```

This creates an entry in the state file:
```yaml
services:
  myservice:
    containers:
      - myservice_container1
      - myservice_container2
    last_updated: "2025-10-30T10:00:00Z"
```

## Grouping Containers Under a Service

To group multiple containers under a single service, set the `edpm_service_name` variable. All containers will be registered under this service name instead of their individual container names.

### Example: Grouping Nova Containers

```yaml
# In roles/edpm_nova/tasks/install.yml

- name: Deploy nova init container
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_container_standalone_service: "nova_compute_init"
    edpm_service_name: "{{ edpm_nova_service_name }}"  # Group under "nova"
    edpm_container_standalone_container_defs:
      nova_compute_init: {...}

- name: Deploy nova compute container
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_container_standalone_service: "nova_compute"
    edpm_service_name: "{{ edpm_nova_service_name }}"  # Group under "nova"
    edpm_container_standalone_container_defs:
      nova_compute: {...}
```

This results in:
```yaml
services:
  nova:
    containers:
      - nova_compute_init
      - nova_compute
    last_updated: "2025-10-30T10:00:00Z"
```

## Real World Example: Nova Service

The `nova.yml` playbook demonstrates how to group containers from multiple roles under one service:

```yaml
# playbooks/nova.yml
- name: Deploy EDPM Nova storage infrastructure
  ansible.builtin.import_playbook: nova_storage.yml
  vars:
    edpm_service_name: nova  # All storage containers belong to "nova" service

- name: Deploy EDPM Nova
  hosts: all
  tasks:
    - name: Deploy EDPM Nova
      ansible.builtin.import_role:
        name: osp.edpm.edpm_nova
```

The storage roles (iscsid, multipathd, nvmeof) inherit `edpm_service_name: nova` from the playbook import.
The nova role explicitly sets `edpm_service_name: "{{ edpm_nova_service_name }}"` (which defaults to "nova").

This creates ONE service "nova" containing ALL containers:
```yaml
services:
  nova:
    containers:
      - iscsid          # From edpm_iscsid
      - multipathd      # From edpm_multipathd
      - nvmeof          # From edpm_nvmeof
      - nova_compute_init   # From edpm_nova
      - nova_compute        # From edpm_nova
      - nova_nvme_cleaner   # From edpm_nova (if enabled)
    last_updated: "2025-10-30T15:00:00Z"
```

## Service Cleanup

A dedicated `cleanup.yml` playbook is provided to remove services. Specify the services to clean up using the `edpm_services_to_cleanup` variable.

### Using the Cleanup Playbook

**Command line:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services_to_cleanup=['nova', 'neutron_metadata']"
```

**With inventory/vars file:**
```yaml
# group_vars/all/cleanup.yml
edpm_services_to_cleanup:
  - nova
  - neutron_metadata

# Then run:
ansible-playbook playbooks/cleanup.yml
```

**Single service:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services_to_cleanup=['nova']"
```

Cleaning up "nova" removes ALL its containers (nova, iscsid, multipathd, nvmeof).

**Cleaning up telemetry:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services_to_cleanup=['telemetry']"
```

Cleaning up "telemetry" removes all telemetry containers:
- ceilometer_agent_compute
- node_exporter
- podman_exporter
- openstack_network_exporter

**Cleaning up OVN:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services_to_cleanup=['ovn']"
```

Cleaning up "ovn" removes:
- ovn_controller

**Cleaning up Neutron Metadata:**
```bash
ansible-playbook playbooks/cleanup.yml \
  -e "edpm_services_to_cleanup=['neutron-metadata']"
```

Cleaning up "neutron-metadata" removes:
- ovn_metadata_agent

### The Cleanup Process

When you run the cleanup playbook:
1. Validates that `edpm_services_to_cleanup` is provided
2. Displays which services will be cleaned up
3. For each service:
   - Reads the state file to get all containers
   - Verifies containers have `managed_by=edpm_ansible` label
   - For each container:
     - Stops and disables systemd service
     - Removes healthcheck service and timer
     - Removes systemd requires directory
     - Removes the container
   - Removes container startup config directories
   - Runs service-specific cleanup tasks (if available)
4. Updates state file to remove cleaned up services

### Files and Resources Cleaned Up

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

**Configurable:**
- Additional paths can be cleaned up via `edpm_cleanup_generic_paths`
- Each path supports `{{ service_name }}` template variable

**Service-specific cleanup (optional):**
- Services can provide a `tasks/cleanup.yml` file in their role to clean up additional resources
- Examples: data directories, certificates, logs, etc.

### Orphaned Container Cleanup

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

**Safety:**
- Disabled by default (`false`)
- Only removes containers explicitly managed by edpm_ansible
- Runs after regular service cleanup completes
- Provides visibility via debug logging

**Use Cases:**
- Cleaning up after failed migrations
- Removing containers from manual testing
- Recovering from state file corruption
- General cleanup of untracked resources

### Cleanup During Deployment

You can also trigger cleanup during a deployment playbook by setting the variable:

```yaml
- hosts: edpm_nodes
  vars:
    edpm_services_to_cleanup:
      - old_neutron_dhcp
  roles:
    - edpm_nova
    - edpm_neutron_ovn
```

The cleanup will run automatically when any role uses `edpm_container_standalone`.

## Configuration Variables

### In roles/edpm_container_standalone/defaults/main.yml:

```yaml
# State file tracking
edpm_container_standalone_track_state: true
edpm_container_standalone_state_file: /var/lib/edpm-config/deployed_services.yaml

# Service name - if set, containers are grouped under this service
# edpm_service_name: ""  # Optional: defaults to edpm_container_standalone_service

# Explicit cleanup
edpm_services_to_cleanup: []
edpm_cleanup_remove_config_dirs: true        # Remove startup configs
edpm_cleanup_orphaned_containers: false      # Remove containers with managed_by=edpm_ansible not in state file

# Generic paths to clean up per service (supports {{ service_name }} template)
edpm_cleanup_generic_paths:
  - "/var/lib/openstack/healthchecks/{{ service_name }}"
```

## How It Works

### Without `edpm_service_name`
Each container is tracked separately:
```yaml
services:
  nova_compute:
    containers: [nova_compute]
  nova_compute_init:
    containers: [nova_compute_init]
  iscsid:
    containers: [iscsid]
```

### With `edpm_service_name: nova`
All containers are grouped under "nova":
```yaml
services:
  nova:
    containers: [nova_compute, nova_compute_init, iscsid]
```

The state tracking logic:
- If `edpm_service_name` is set and different from `edpm_container_standalone_service`, containers are **appended** to the service
- If `edpm_service_name` is not set, the container is registered as its own service

## Implementation Details

### Ansible Module

The state file operations are handled by the `osp.edpm.edpm_service_state` Ansible module (`plugins/modules/edpm_service_state.py`):

**Features:**
- Atomic read-modify-write operations using file locking (`fcntl.flock()`)
- Supports adding services (`state: present`) and removing them (`state: absent`)
- Handles both full updates and appending containers to existing services
- Ensures data integrity during concurrent deployments
- Proper error handling and reporting

**Example usage:**
```yaml
- name: Add service with containers
  osp.edpm.edpm_service_state:
    state_file: /var/lib/edpm-config/deployed_services.yaml
    service_name: nova
    containers:
      - nova_compute
      - nova_compute_init
    state: present

- name: Append containers to existing service
  osp.edpm.edpm_service_state:
    state_file: /var/lib/edpm-config/deployed_services.yaml
    service_name: nova
    containers:
      - iscsid
      - multipathd
    append: true
    state: present

- name: Remove service
  osp.edpm.edpm_service_state:
    state_file: /var/lib/edpm-config/deployed_services.yaml
    service_name: nova
    state: absent
```

### Race Condition Prevention

The custom module prevents race conditions during concurrent deployments:

- **File Locking**: Acquires exclusive locks using `fcntl.flock()` before any state file operation
- **Atomic Writes**: Changes are written to a temporary file and atomically renamed
- **Automatic Lock Release**: Locks are released when the module execution completes
- **Directory Safety**: Creates state file directory if it doesn't exist

This ensures multiple concurrent playbook runs can safely update the state file without data loss or corruption.

## Implementing for Other Services

To add state tracking to your playbook:

1. **Set service name in playbook** when importing dependencies:
   ```yaml
   - name: Deploy My Service infrastructure
     ansible.builtin.import_playbook: my_service_deps.yml
     vars:
       edpm_service_name: myservice
   ```

2. **Set service name in roles** when calling `edpm_container_standalone`:
   ```yaml
   - ansible.builtin.include_role:
       name: osp.edpm.edpm_container_standalone
     vars:
       edpm_container_standalone_service: "myservice_container"
       edpm_service_name: "{{ edpm_myservice_service_name }}"
   ```

3. **Add custom cleanup paths** (optional) for additional generic patterns:
   ```yaml
   edpm_cleanup_generic_paths:
     - "/var/lib/openstack/healthchecks/{{ service_name }}"
     - "/var/lib/{{ service_name }}"
     - "/etc/{{ service_name }}"
   ```

4. **Add service-specific cleanup** (optional) for unique requirements:
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

5. **Cleanup** by specifying the service name:
   ```yaml
   edpm_services_to_cleanup: ['myservice']
   ```

This will:
- Remove all containers tracked under "myservice"
- Clean up systemd files
- Remove container startup configs
- Remove kolla config JSON files
- Clean up generic paths (healthchecks, etc.)
- Run service-specific cleanup tasks (if provided)

## Safety Features

- Only removes containers with `managed_by=edpm_ansible` label
- Atomic state file updates prevent corruption
- Graceful handling of missing state file
- Cleanup is opt-in via explicit variable

## Benefits

✅ **Unified lifecycle** - Deploy and cleanup services as a unit
✅ **Playbook-centric** - Services defined where they're actually deployed
✅ **Automatic tracking** - State updated on every deployment
✅ **Safe cleanup** - Explicit variable required, with verification
✅ **Handles dependencies** - Storage containers tracked with parent service
✅ **Incremental deployments** - Add services without affecting existing ones

## Advanced Configuration

### State Append Mode

When deploying multiple containers under the same service name in separate calls (e.g., in a loop or sequential tasks), use `edpm_container_standalone_state_append`:

```yaml
# First container: Replace existing state
- name: Deploy first container
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_service_name: myservice
    edpm_container_standalone_state_append: false  # Replace
    edpm_container_standalone_container_defs:
      container1: {...}

# Subsequent containers: Append to state
- name: Deploy additional containers
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_service_name: myservice
    edpm_container_standalone_state_append: true  # Append
    edpm_container_standalone_container_defs:
      container2: {...}
```

**Examples in the codebase:**
- `edpm_telemetry`: Loops through exporters, replace on first, append on rest
- `edpm_nova`: Deploys 3 containers sequentially, replace on first, append on rest

### Container Label Requirements

Cleanup only removes containers with the `managed_by=edpm_ansible` label. This label is automatically added by the `edpm_container_manage` module.

All containers also include:
- `config_id=<container_name>`
- `container_name=<container_name>`
- `config_data=<container_definition>` (full definition)

### Custom Cleanup Paths

Add custom paths to clean up per service:

```yaml
edpm_cleanup_generic_paths:
  - "/var/lib/openstack/healthchecks/{{ service_name }}"
  - "/var/log/containers/{{ service_name }}"
  - "/etc/{{ service_name }}/custom-config"
```

The `{{ service_name }}` variable is automatically replaced with the actual service name during cleanup.

## Migrating from edpm_container_manage Cleanup

The old `edpm_container_manage_clean_orphans` feature is **deprecated**. Migrate to using `edpm_cleanup_orphaned_containers` in `edpm_container_standalone` instead:

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
