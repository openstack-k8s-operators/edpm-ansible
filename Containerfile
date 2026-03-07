FROM quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest
COPY roles/edpm_lldp /usr/share/ansible/roles/edpm_lldp
COPY roles/edpm_neutron_opflex_agent /usr/share/ansible/roles/edpm_neutron_opflex_agent
COPY roles/edpm_cisco_opflex_agent /usr/share/ansible/roles/edpm_cisco_opflex_agent
COPY playbooks/lldp.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
COPY playbooks/neutron_opflex_agent.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
COPY playbooks/opflex_agent.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
