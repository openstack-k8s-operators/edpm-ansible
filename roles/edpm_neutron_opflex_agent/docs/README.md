# Neutron OpFlex Agent Service

OpenStack DataPlane service definition for deploying the Neutron OpFlex agent on EDPM nodes.

## Overview

The Neutron OpFlex agent integrates OpenStack Neutron networking with Cisco ACI fabric through the OpFlex protocol. It translates Neutron network configurations into ACI policy model.

## Usage

Apply the service to your OpenStack cluster:

```bash
oc apply -f neutron-opflex-agent-service.yaml -n openstack
```

Verify the service is registered:

```bash
oc get openstackdataplaneservice neutron-opflex-agent-custom-service -n openstack
```

## Configuration

Before applying, ensure the following are configured:

- **Image**: Update `openStackAnsibleEERunnerImage` to point to your registry
- **RabbitMQ Transport**: Ensure `rabbitmq-transport-url-neutron-neutron-transport` secret exists
- **CA Certificates**: Ensure `combined-ca-bundle` is available if using TLS

## Requirements

- Combined Ansible EE runner image with Neutron OpFlex agent role included
- RabbitMQ credentials configured in OpenStack
- Cisco OpFlex agent deployed and running
- Network connectivity to Neutron control plane

## Deployment Order

This service should be deployed after:
1. LLDP agent service (for network discovery)
2. Cisco OpFlex agent service (provides OpFlex communication)

## See Also

- Role defaults: [../defaults/main.yml](../defaults/main.yml)
- Role tasks: [../tasks/main.yml](../tasks/main.yml)
