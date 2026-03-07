# Deployment Instructions

Instructions for deploying the Neutron OpFlex Agent, OpFlex Agent, DHCP Agent, and LLDP Agent.

## Prerequisites

- OpenStack cluster with dataplane operator configured
- Access to `oc` command-line tool
- Built and pushed the combined-ansibleee-runner image (see [BUILD.md](BUILD.md))

## Deployment Steps

### 1. Apply the Services

Apply the custom EDPM services to your OpenStack namespace:

```bash
oc apply -f ../../edpm_neutron_opflex_agent/docs/neutron-opflex-agent-service.yaml -n openstack
oc apply -f ../../edpm_lldp/docs/ciscoaci-lldp-agent-service.yaml -n openstack
oc apply -f ../docs/cisco-opflex-agent-service.yaml -n openstack
```

> **Note**: Service YAML files are located in each role's `docs/` directory for better organization.

### 2. Verify Services are Created

Check that the services are registered:

```bash
oc get openstackdataplaneservice -n openstack
```

### 3. Configure the NodeSet Patch

Create `nodeset_patch.yaml` based on the template included in this directory.

**Important configuration:**
- Set `edpm_cisco_opflex_agent_aci_apic_systemid` to your ACI APIC system ID
- Verify that the container images specified are correct for your environment

### 4. Configure the Deployment Patch

Create `nodeset_patch_deploy.yaml` based on the template included in this directory.

### 5. Apply the NodeSet Patch

Apply the patch to your data plane nodeset:

```bash
oc patch openstackdataplanenodeset openstack-data-plane -n openstack --type merge --patch-file nodeset_patch.yaml
```

### 6. Apply the Deployment

Trigger the deployment:

```bash
oc apply -f nodeset_patch_deploy.yaml
```

### 7. Monitor the Deployment

The deployment should now be running. Monitor the progress:

```bash
oc get pod -l app=openstackansibleee -n openstack
```

**Example output:**

```
NAME                                                              READY   STATUS      RESTARTS   AGE
bootstrap-data-plane-deploy-openstack-data-plane-kz9g7            0/1     Completed   0          53m
configure-network-data-plane-deploy-openstack-data-plane-c5xlp    0/1     Completed   0          52m
configure-os-data-plane-deploy-openstack-data-plane-9kq27         0/1     Completed   0          50m
install-certs-data-plane-deploy-openstack-data-plane-hgrkx        0/1     Completed   0          49m
install-os-data-plane-deploy-openstack-data-plane-7wjtr           0/1     Completed   0          51m
libvirt-data-plane-deploy-openstack-data-plane-lvddl              0/1     Completed   0          48m
neutron-metadata-data-plane-deploy-openstack-data-plane-vxz79     0/1     Completed   0          48m
neutron-opflex-agent-custom-service-deploy-new-service-opeq5z8g   1/1     Running     0          11s
nova-data-plane-deploy-openstack-data-plane-56chl                 0/1     Completed   0          46m
ovn-data-plane-deploy-openstack-data-plane-qlnm2                  0/1     Completed   0          49m
reboot-os-data-plane-deploy-openstack-data-plane-rl5f6            0/1     Completed   0          49m
run-os-data-plane-deploy-openstack-data-plane-lmgsc               0/1     Completed   0          49m
ssh-known-hosts-data-plane-deploy-jlqwf                           0/1     Completed   0          50m
validate-network-data-plane-deploy-openstack-data-plane-rgv8q     0/1     Completed   0          51m
```

Look for the custom service pods (e.g., `neutron-opflex-agent-custom-service-deploy-*`) to verify deployment.

## Troubleshooting

### Check Service Logs

```bash
oc logs <pod-name> -n openstack
```

### Verify Services are Running on Data Plane Nodes

SSH into your data plane nodes and check container status:

```bash
sudo podman ps | grep opflex
```

## See Also

- [BUILD.md](BUILD.md) - Instructions for building the container image
- [Build Instructions.txt](Build%20Instructions.txt) - Original build documentation
