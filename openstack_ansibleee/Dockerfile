FROM ghcr.io/ansible/community-ansible-dev-tools:v24.10.0 as builder

ARG REMOTE_SOURCE=.
ARG REMOTE_SOURCE_DIR=/var/tmp/edpm-ansible

COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
RUN cd $REMOTE_SOURCE_DIR && \
    ansible-galaxy collection install -U --timeout 120 -r requirements.yml --collections-path "/usr/share/ansible/collections" && \
    ansible-galaxy collection install -U $REMOTE_SOURCE_DIR --collections-path "/usr/share/ansible/collections"

FROM ghcr.io/ansible/community-ansible-dev-tools:v24.10.0 as runner

COPY --from=builder /usr/share/ansible /usr/share/ansible
COPY $REMOTE_SOURCE/openstack_ansibleee/settings /runner/env/settings
COPY $REMOTE_SOURCE/openstack_ansibleee/edpm_entrypoint.sh /opt/builder/bin/edpm_entrypoint

RUN sed '1d' /opt/builder/bin/entrypoint >> /opt/builder/bin/edpm_entrypoint
RUN chmod 775 /runner/env/settings && chmod +x /opt/builder/bin/edpm_entrypoint && chmod ug+rw /etc/passwd

ENV EDPM_SYSTEMROLES='fedora.linux_system_roles'
WORKDIR /runner
LABEL ansible-execution-environment=true
ENTRYPOINT ["/opt/builder/bin/edpm_entrypoint", "dumb-init"]
