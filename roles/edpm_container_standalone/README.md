# edpm_container_standalone Role

## Overview

The `edpm_container_standalone` role provides a unified interface for deploying and managing containerized services in EDPM. It wraps the lower-level `edpm_container_manage` role with additional features including:

- **Automatic state tracking** of deployed services
- **Service lifecycle management** (deployment)
- **Container grouping** under logical service names
- **Atomic state file operations** for safe concurrent deployments

**Key Concept:** Services are defined at the playbook level, not the role level. When a playbook deploys multiple roles, they can all be tracked under a single service name for unified lifecycle management.

## Basic Usage

### Deploying a Simple Service

```yaml
- name: Deploy my service
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_container_standalone_service: myservice
    edpm_container_standalone_container_defs:
      myservice_container:
        image: quay.io/myorg/myservice:latest
        command: /usr/bin/myservice-server
        net: host
        privileged: false
        restart: always
        environment:
          KOLLA_CONFIG_STRATEGY: COPY_ALWAYS
    edpm_container_standalone_kolla_config_files:
      myservice_container:
        command: /usr/bin/myservice-server
        config_files:
          - source: /var/lib/kolla/config_files/myservice.conf
            dest: /etc/myservice/myservice.conf
            owner: myservice
            perm: "0600"
```

This will:
1. Create kolla configuration files in `/var/lib/kolla/config_files/`
2. Create container definition JSON in `/var/lib/edpm-config/container-startup-config/myservice/`
3. Use `edpm_container_manage` to create and start the container
4. Register the service in the state file
5. Create systemd services for the container

### Required Variables

- `edpm_container_standalone_service`: Service name (used for directory naming)
- `edpm_container_standalone_container_defs`: Dictionary of container definitions
- `edpm_container_standalone_kolla_config_files`: Kolla configuration per container

### Optional Variables

- `edpm_service_name`: Override service name for state tracking (enables container grouping)
- `edpm_container_state_append`: Append containers to existing service (default: false)
- `edpm_container_track_state`: Enable state tracking (default: true)

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

## Configuration Variables

### In roles/edpm_container_standalone/defaults/main.yml:

```yaml
# State file tracking
edpm_container_track_state: true
edpm_container_state_file: /var/lib/edpm-config/deployed_services.yaml

# Service name - if set, containers are grouped under this service
# edpm_service_name: ""  # Optional: defaults to edpm_container_standalone_service
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

### State File Management

The state file operations are handled using standard Ansible tasks:

**Features:**
- Read state file using `ansible.builtin.slurp`
- Parse YAML content using `from_yaml` filter
- Update state data using `ansible.builtin.set_fact`
- Write updated state file using `ansible.builtin.copy`
- Supports adding services and appending containers to existing services
- Handles empty or missing state files gracefully

**Implementation:**
The state file updates are handled in `tasks/state_file_update.yml` which:
1. Reads the current state file (if it exists)
2. Parses the YAML content
3. Updates the service entry with container information
4. Writes the updated state file atomically

**Example usage:**
```yaml
- name: Update service state file
  ansible.builtin.include_tasks: state_file_update.yml
  vars:
    _edpm_service_name: nova
    edpm_container_standalone_container_defs:
      nova_compute: {...}
      nova_compute_init: {...}
    edpm_container_state_append: false  # Set true to append containers
```

### Race Condition Prevention

The state file updates use standard Ansible tasks. While file locking is not explicitly implemented, Ansible's task execution model provides some protection:

- **Sequential Execution**: Ansible executes tasks sequentially within a playbook run
- **Idempotency**: The state file operations are designed to be idempotent
- **Directory Safety**: The state file directory is created if it doesn't exist

Note: For environments with concurrent playbook executions, consider implementing additional synchronization mechanisms if needed.

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

## Advanced Configuration

### State Append Mode

When deploying multiple containers under the same service name in separate calls (e.g., in a loop or sequential tasks), use `edpm_container_state_append`:

```yaml
# First container: Replace existing state
- name: Deploy first container
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_service_name: myservice
    edpm_container_state_append: false  # Replace
    edpm_container_standalone_container_defs:
      container1: {...}

# Subsequent containers: Append to state
- name: Deploy additional containers
  ansible.builtin.include_role:
    name: osp.edpm.edpm_container_standalone
  vars:
    edpm_service_name: myservice
    edpm_container_state_append: true  # Append
    edpm_container_standalone_container_defs:
      container2: {...}
```

**Examples in the codebase:**
- `edpm_telemetry`: Loops through exporters, replace on first, append on rest
- `edpm_nova`: Deploys 3 containers sequentially, replace on first, append on rest

### Container Labels

All containers managed by this role include the following labels:
- `managed_by=edpm_ansible` - Identifies containers managed by EDPM Ansible
- `container_name=<container_name>`
- `config_data=<container_definition>` (full definition)

## Removing Containers from State File

To remove a container from the state file, use `state_file_update.yml` with `edpm_container_state_remove: true`:

```yaml
# Remove a container from a service (e.g., multipathd from nova)
- name: Remove multipathd from nova service in state file
  ansible.builtin.include_tasks: state_file_update.yml
  vars:
    edpm_container_state_remove: true
    edpm_service_name: nova                         # Service name
    edpm_container_standalone_service: multipathd   # Container to remove
```

**Note:** When the last container is removed from a service, the service is automatically removed from the state file.

### Required Variables for Removal

- `edpm_container_state_remove: true`: Enable removal mode
- `edpm_service_name`: Service name (e.g., `nova`, `telemetry`, `neutron-metadata`)
- `edpm_container_standalone_service`: Container name to remove from the service

**Note:** If service or container doesn't exist, removal is silently ignored.
