# Cisco OpFlex Agent Service

OpenStack DataPlane service definition for deploying the Cisco OpFlex agent on EDPM nodes.

## Overview

The OpFlex agent provides distributed policy enforcement for Cisco ACI (Application Centric Infrastructure) integration with OpenStack. It communicates with the ACI fabric to implement network policies on compute nodes.

## Usage

Apply the service to your OpenStack cluster:

```bash
oc apply -f cisco-opflex-agent-service.yaml -n openstack
```

Verify the service is registered:

```bash
oc get openstackdataplaneservice cisco-opflex-agent-custom-service -n openstack
```

## Configuration

Before applying, ensure the following are configured in your environment:

- **Image**: Update `openStackAnsibleEERunnerImage` to point to your registry
- **ACI APIC System ID**: Configure `edpm_cisco_opflex_agent_aci_apic_systemid` in your nodeset patch

## Requirements

- Combined Ansible EE runner image with OpFlex agent role included
- Cisco ACI fabric configured and accessible
- LLDP service deployed (for ACI fabric discovery)

## See Also

- Role defaults: [../defaults/main.yml](../defaults/main.yml)
- Role tasks: [../tasks/main.yml](../tasks/main.yml)
- Deployment instructions: [../DeploymentInstructions/README.md](../DeploymentInstructions/README.md)
