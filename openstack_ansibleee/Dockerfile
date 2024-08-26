FROM quay.io/ansible/creator-ee:v0.21.0 as builder

ARG REMOTE_SOURCE=.
ARG REMOTE_SOURCE_DIR=/var/tmp/edpm-ansible

COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
RUN cd $REMOTE_SOURCE_DIR && \
    ansible-galaxy collection install -U --timeout 120 -r requirements.yml --collections-path "/usr/share/ansible/collections" && \
    ansible-galaxy collection install -U $REMOTE_SOURCE_DIR --collections-path "/usr/share/ansible/collections"

FROM quay.io/ansible/creator-ee:v0.21.0 as runner

RUN \
microdnf install -y \
# we are installing ansible.posix with rsync, but we aren't installing rsync itself
rsync
COPY --from=builder /usr/share/ansible /usr/share/ansible

COPY $REMOTE_SOURCE/openstack_ansibleee/settings /runner/env/settings
RUN chmod 775 /runner/env/settings
COPY $REMOTE_SOURCE/openstack_ansibleee/edpm_entrypoint.sh /bin/edpm_entrypoint
RUN sed -i '1d' /bin/entrypoint
RUN cat /bin/entrypoint >> /bin/edpm_entrypoint
RUN chmod +x /bin/edpm_entrypoint
ENV EDPM_SYSTEMROLES='fedora.linux_system_roles'
WORKDIR /runner
ENTRYPOINT ["edpm_entrypoint"]
