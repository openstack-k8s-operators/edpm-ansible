# Manual Build Instructions

> **Note:** An automated build script is available! See [BUILD.md](BUILD.md) for automated build instructions using `build.sh`.

These instructions describe how to manually build the combined Ansible EE runner container image.

## Prerequisites

- `podman` installed and configured
- Access to `quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest`
- Access to your container registry (for pushing)

## Manual Build Steps

### 1. Copy Required Files

Copy the following roles and playbooks to the same folder:

**Roles:**
- `roles/edpm_cisco_opflex_agent`
- `roles/edpm_lldp`
- `roles/edpm_neutron_opflex_agent`

**Playbooks:**
- `playbooks/lldp.yml`
- `playbooks/neutron_opflex_agent.yml`
- `playbooks/opflex_agent.yml`

### 2. Create Containerfile

Create a `Containerfile` in the same directory containing:

```dockerfile
FROM quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest
COPY edpm_lldp /usr/share/ansible/roles/edpm_lldp
COPY edpm_neutron_opflex_agent /usr/share/ansible/roles/edpm_neutron_opflex_agent
COPY edpm_cisco_opflex_agent /usr/share/ansible/roles/edpm_cisco_opflex_agent
COPY lldp.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
COPY neutron_opflex_agent.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
COPY opflex_agent.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
```

### 3. Verify Directory Structure

Your build directory should look like this:

```
[stack@ostack-pt-1-ucloud-17 testbuild-combine]$ ls
Containerfile  edpm_cisco_opflex_agent  edpm_lldp  edpm_neutron_opflex_agent  lldp.yml  neutron_opflex_agent.yml  opflex_agent.yml
```

### 4. Build the Container Image

Build the container image:

```bash
podman build -t 10.30.9.74:8787/osp18/combined-ansibleee-runner:18.0.9 .
```

Replace the registry URL and tag with your values.

### 5. Push to Registry

Push the built image to your container registry:

```bash
podman push 10.30.9.74:8787/osp18/combined-ansibleee-runner:18.0.9
```

## Automated Alternative

Instead of following these manual steps, you can use the automated build script:

```bash
./build.sh -r 10.30.9.74:8787/osp18 -t 18.0.9 --push
```

See [BUILD.md](BUILD.md) for full documentation on the automated build script.
