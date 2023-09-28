FROM quay.io/ansible/creator-ee:v0.14.1 as builder

ARG REMOTE_SOURCE=.
ARG REMOTE_SOURCE_DIR=/var/tmp/edpm-ansible

COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
RUN cd /var/tmp/edpm-ansible && \
    ansible-galaxy collection install -U --timeout 120 -r requirements.yml --collections-path "/usr/share/ansible/collections" && \
    ansible-galaxy collection install -U $REMOTE_SOURCE_DIR --collections-path "/usr/share/ansible/collections"

FROM quay.io/ansible/creator-ee:v0.14.1 as runner

COPY --from=builder /usr/share/ansible /usr/share/ansible

COPY $REMOTE_SOURCE/openstack_ansibleee/settings /runner/env/settings
RUN chmod 775 /runner/env/settings
COPY $REMOTE_SOURCE/openstack_ansibleee/edpm_entrypoint.sh /bin/edpm_entrypoint
RUN sed -i '1d' /bin/entrypoint
RUN cat /bin/entrypoint >> /bin/edpm_entrypoint
RUN chmod +x /bin/edpm_entrypoint
WORKDIR /runner
ENTRYPOINT ["edpm_entrypoint"]
