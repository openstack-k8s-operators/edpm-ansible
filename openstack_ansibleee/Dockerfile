FROM quay.io/ansible/creator-ee:v0.13.0

ARG REMOTE_SOURCE=.
ARG REMOTE_SOURCE_DIR=/var/tmp/edpm-ansible

USER root
RUN chmod g=u /etc/passwd /etc/group

COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
RUN ls -laR $REMOTE_SOURCE_DIR
RUN microdnf -y install python3-tenacity
RUN cd /var/tmp/edpm-ansible && \
    ansible-galaxy collection install --timeout 120 -r requirements.yml --collections-path "/usr/share/ansible/collections" && \
    ansible-galaxy collection install $REMOTE_SOURCE_DIR --collections-path "/usr/share/ansible/collections"
RUN ln -sfv /usr/share/ansible/collections/ansible_collections/osp/edpm/plugins /usr/share/ansible/plugins
RUN chmod -R 777 /usr/share/ansible
COPY $REMOTE_SOURCE/openstack_ansibleee/settings /runner/env/settings
RUN chmod 777 /runner/env/settings
COPY $REMOTE_SOURCE/openstack_ansibleee/edpm_entrypoint.sh /bin/edpm_entrypoint
RUN sed -i '1d' /bin/entrypoint
RUN cat /bin/entrypoint >> /bin/edpm_entrypoint
RUN chmod +x /bin/edpm_entrypoint
WORKDIR /runner
RUN rm -rf roles && ln -snf /usr/share/ansible/collections/ansible_collections/osp/edpm/roles roles
RUN rm -rf project && ln -snf /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks project
RUN rm -rf $REMOTE_SOURCE_DIR
USER 1001
ENTRYPOINT ["edpm_entrypoint"]
