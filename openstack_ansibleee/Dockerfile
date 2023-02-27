FROM quay.io/ansible/creator-ee:v0.13.0
ARG EDPM_LOCAL_REPO=""
ARG EDPM_REPO_URL="https://github.com/openstack-k8s-operators/edpm-ansible.git"
ARG EDPM_LOCAL_DIR="/var/tmp/edpm-ansible"
USER root
RUN chmod g=u /etc/passwd /etc/group
RUN if [ ! -d "${EDPM_LOCAL_DIR}" ] ; then \
        echo "Cloning from ${EDPM_REPO_URL}"; \
        /usr/bin/git clone ${EDPM_REPO_URL} ${EDPM_LOCAL_DIR}; \
    fi
WORKDIR ${EDPM_LOCAL_DIR}
RUN pip install --no-cache-dir -r requirements.txt
RUN ansible-galaxy role install --timeout 120 -r requirements.yml \
    --roles-path "/usr/share/ansible/roles" && \
    ansible-galaxy collection install --timeout 120 -r requirements.yml \
    --collections-path "/usr/share/ansible/collections"
RUN python3 setup.py install --prefix=/usr
# When local repo of edpm-ansible is mounted as a volume, during podman build
# It will give Device/Resource busy. In order to fix that. Clean up the directory
# Only when EDPM_LOCAL_REPO is defined.
RUN if [ -z "${EDPM_LOCAL_REPO}" ] ; then \
        echo ${EDPM_LOCAL_REPO}; \
        rm -fr ${EDPM_LOCAL_DIR}; \
    fi
RUN chmod -R 777 /usr/share/ansible
COPY settings /runner/env/settings
RUN chmod 777 /runner/env/settings
COPY edpm_entrypoint.sh /bin/edpm_entrypoint
RUN sed -i '1d' /bin/entrypoint && \
    cat /bin/entrypoint >> /bin/edpm_entrypoint && \
    chmod +x /bin/edpm_entrypoint
WORKDIR /runner
RUN rm -rf roles && ln -snf /usr/share/ansible/roles roles && \
    rm -rf project && ln -snf /usr/share/ansible/edpm-playbooks project
USER 1001
ENTRYPOINT ["edpm_entrypoint"]
