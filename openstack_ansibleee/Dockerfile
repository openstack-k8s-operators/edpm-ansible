FROM quay.io/ansible/creator-ee:v0.14.1

ARG REMOTE_SOURCE=.
ARG REMOTE_SOURCE_DIR=/var/tmp/edpm-ansible

USER root

RUN microdnf upgrade --refresh -y && microdnf clean all
RUN chmod g=u /etc/passwd /etc/group

COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
RUN ls -laR $REMOTE_SOURCE_DIR

WORKDIR ${REMOTE_SOURCE_DIR}

RUN pip-3 install --no-cache-dir -r requirements.txt
RUN ansible-galaxy role install --timeout 120 -r requirements.yml \
    --roles-path "/usr/share/ansible/roles" && \
    ansible-galaxy collection install --timeout 120 -r requirements.yml \
    --collections-path "/usr/share/ansible/collections"
RUN python3 setup.py install --prefix=/usr
RUN chmod -R 777 /usr/share/ansible

COPY $REMOTE_SOURCE/openstack_ansibleee/settings /runner/env/settings
RUN chmod 777 /runner/env/settings

COPY $REMOTE_SOURCE/openstack_ansibleee/edpm_entrypoint.sh /bin/edpm_entrypoint
RUN sed -i '1d' /bin/entrypoint && \
    cat /bin/entrypoint >> /bin/edpm_entrypoint && \
    chmod +x /bin/edpm_entrypoint

WORKDIR /runner

RUN rm -rf roles && ln -snf /usr/share/ansible/roles roles && \
    rm -rf project && ln -snf /usr/share/ansible/edpm-playbooks project

USER 1001

ENTRYPOINT ["edpm_entrypoint"]
