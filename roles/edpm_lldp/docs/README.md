# Cisco ACI LLDP Agent Service

OpenStack DataPlane service definition for deploying the LLDP (Link Layer Discovery Protocol) agent on EDPM nodes.

## Overview

The LLDP agent enables network topology discovery for Cisco ACI integration. It allows ACI fabric to discover and identify compute nodes in the OpenStack environment.

## Usage

Apply the service to your OpenStack cluster:

```bash
oc apply -f ciscoaci-lldp-agent-service.yaml -n openstack
```

Verify the service is registered:

```bash
oc get openstackdataplaneservice ciscoaci-lldp-agent-service -n openstack
```

## Configuration

Before applying, ensure the following are configured:

- **Image**: Update `openStackAnsibleEERunnerImage` to point to your registry
- **CA Certificates**: Ensure `combined-ca-bundle` is available if using TLS

## Requirements

- Combined Ansible EE runner image with LLDP role included
- Network connectivity to ACI fabric

## Deployment Order

This service should typically be deployed before the OpFlex agent, as it provides network discovery capabilities needed by ACI.

## See Also

- Role defaults: [../defaults/main.yml](../defaults/main.yml)
- Role tasks: [../tasks/main.yml](../tasks/main.yml)
