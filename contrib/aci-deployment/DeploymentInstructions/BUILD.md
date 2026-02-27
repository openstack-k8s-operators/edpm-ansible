# Building the Combined Ansible EE Runner Container

This directory contains a build script that automates the creation of a combined Ansible Execution Environment container image with Cisco OpFlex support.

## Overview

The `build.sh` script automates the build process described in `Build Instructions.txt`. It creates a container image based on the OpenStack Ansible EE Runner that includes:

- `edpm_cisco_opflex_agent` role
- `edpm_lldp` role
- `edpm_neutron_opflex_agent` role
- Associated playbooks (`opflex_agent.yml`, `lldp.yml`, `neutron_opflex_agent.yml`)

## Prerequisites

- `podman` installed and configured
- Access to `quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest`
- (Optional) Access to your container registry if pushing images

## Quick Start

### Build Only

```bash
./build.sh -r 10.30.9.74:8787/osp18 -t 18.0.9
```

### Build and Push

```bash
./build.sh -r 10.30.9.74:8787/osp18 -t 18.0.9 --push
```

## Usage

```
./build.sh [OPTIONS]

OPTIONS:
    -r, --registry REGISTRY    Registry URL (e.g., 10.30.9.74:8787/osp18)
    -t, --tag TAG             Image tag (default: 18.0.9)
    -n, --name NAME           Image name (default: combined-ansibleee-runner)
    -p, --push                Push image after build
    -h, --help                Show this help message
```

## Examples

### Basic build with default settings
```bash
./build.sh -r myregistry.example.com:5000/osp18 -t 18.0.9
```

### Custom image name and tag
```bash
./build.sh -r myregistry.example.com:5000/osp18 -n my-ansibleee -t 1.0.0
```

### Build and immediately push to registry
```bash
./build.sh -r myregistry.example.com:5000/osp18 -t 18.0.9 --push
```

### Build without registry prefix (local only)
```bash
./build.sh -t latest
```

## How It Works

1. **Generates Containerfile**: Creates a `Containerfile` at the repository root with the necessary COPY directives
2. **Builds from repo root**: Uses the existing file structure without copying files
3. **Tags the image**: Applies the specified registry, name, and tag
4. **Optional push**: Pushes to registry only if `--push` flag is provided

## Output

The script will:
- Display build configuration before starting
- Show podman build output during the build process
- Provide a summary with the full image name
- Show push commands if you didn't use `--push`

## Manual Push

If you built without `--push`, you can push later:

```bash
podman push <registry>/<image-name>:<tag>
```

Example:
```bash
podman push 10.30.9.74:8787/osp18/combined-ansibleee-runner:18.0.9
```

## Troubleshooting

### Permission denied when running script
```bash
chmod +x build.sh
```

### Cannot connect to registry
Ensure you're logged in to your container registry:
```bash
podman login <registry-url>
```

### Build fails with "file not found"
The script expects to be run from the DeploymentInstructions directory. Verify you're in the correct location:
```bash
pwd
# Should show: .../edpm-ansible/roles/edpm_cisco_opflex_agent/DeploymentInstructions
```

## Notes

- The script creates a `Containerfile` at the repository root (will overwrite if exists)
- No temporary files or copies are created - builds directly from the repo structure
- The base image is pulled from `quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest`

## See Also

- `Build Instructions.txt` - Original manual build instructions
- `README.txt` - Deployment instructions for the built container
