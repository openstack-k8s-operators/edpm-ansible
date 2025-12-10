.. _testing with ansibleee:

======================
Testing with ansibleee
======================

edpm-ansible is included in the openstack-ansibleee-runner container image,
which is a key component used by the openstack-operator that deploys EDPM nodes.
The openstack-operator's CRD includes support for specifying additional
volume mounts for the ansibleee pods, which provides a mechanism for accessing
a local copy of edpm-ansible. This makes it possible to develop and test local
changes to edpm-ansible without having to build and deploy a new
openstack-ansibleee-runner container image.

Provide NFS access to your edpm-ansible directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The technique described here uses NFS to access the edpm-ansible directory on
your development system, so you'll need to install an NFS server and create
an appropriate export on your development system. Of course, this implies
your OpenShift deployment that runs the openstack-operator has access to
the NFS server, including any required firewall rules.

* `EL 8 instructions <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/deploying_different_types_of_servers/deploying-an-nfs-server_deploying-different-types-of-servers>`_
* `EL 9 instructions <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/deploying-an-nfs-server_configuring-and-using-network-file-services>`_

When using OpenShift Local (aka CRC), your export will be something like this:

.. code-block:: console

    % echo "${HOME}/edpm-ansible 192.168.130.0/24(rw,sync,no_root_squash,insecure)" > /etc/exports

    % exportfs -r

Make sure nfs-server and firewalld are started:

.. code-block:: console

    % systemctl start firewalld
    % systemctl start nfs-server

.. tip::

   CRC installs its own firewall rules, which likely will need to be adjusted
   depending on the location of your NFS server. If your edpm-ansible
   directory is on the same system that hosts your CRC, then the simplest
   thing to do is insert a rule that essentially circumvents the other rules:

   % nft add rule inet firewalld filter_IN_libvirt_pre accept

.. note::

  If using NFSv4, ensure your edpm-ansible directory has a minimum permission
  of ``2775`` (or ``2777`` for testing). The ansibleee runner container runs as
  a non-root user, so it requires "others" read and execute permissions to
  access the directory contents.

    .. code-block:: console

       % chmod 2775 ${HOME}/edpm-

Create edpm-ansible PV and PVC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create an NFS PV, and a PVC that can be mounted on the ansibleee pods.

.. note::

   While it's possible to add an NFS volume directly to a pod, the default k8s
   Security Context Constraint (SCC) for non-privileged pods does not permit
   NFS volume mounts. The approach of using an NFS PV and PVC works just as
   well, and avoids the need to fiddle with SCC policies.

.. code-block:: shell

    # E.g. ${HOME}/edpm-ansible
    NFS_SHARE=<Path to your edpm-ansible directory>
    NFS_SERVER=<IP of your NFS server>
    cat <<EOF >edpm-ansible-storage.yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      # Do not use just "edpm-ansible" for the metadata name!
      name: edpm-ansible-dev
    spec:
      capacity:
        storage: 1Gi
      volumeMode: Filesystem
      accessModes:
        - ReadOnlyMany
      # IMPORTANT! The persistentVolumeReclaimPolicy must be "Retain" or else
      # your code will be deleted when the volume is reclaimed!
      persistentVolumeReclaimPolicy: Retain
      storageClassName: edpm-ansible
      mountOptions:
        - nfsvers=4.1
      nfs:
        path: ${NFS_SHARE}
        server: ${NFS_SERVER}
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      # Do not use just "edpm-ansible" for the metadata name!
      name: edpm-ansible-dev
    spec:
      storageClassName: edpm-ansible
      accessModes:
        - ReadOnlyMany
      resources:
        requests:
          storage: 1Gi
    EOF

    oc apply -f edpm-ansible-storage.yaml

Add extraMount to your OpenStackDataPlaneNodeSet CR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use kustomize or "oc edit" to add the edpm-ansible PVC to the
OpenStackDataPlaneNodeSet's /spec/nodeTemplate/extraMounts. The
mountPath is where the edpm-ansible *roles* and *plugins* directories are
located inside the openstack-ansibleee-runner container image. The
OpenStackDataPlaneNodeSet CR should contain the following snippet:

.. code-block:: console

  spec:
    nodeTemplate:
      extraMounts:
      - extraVolType: edpm-ansible
        mounts:
        - mountPath: /usr/share/ansible/collections/ansible_collections/osp/edpm
          name: edpm-ansible
        volumes:
        - name: edpm-ansible
          persistentVolumeClaim:
            claimName: edpm-ansible-dev
            readOnly: true
