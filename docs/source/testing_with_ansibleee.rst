.. _testing with ansibleee:

======================
Testing with ansibleee
======================

edpm-ansible is included in the openstack-ansibleee-runner container image,
which is a key component used by the dataplane-operator that deploys EDPM nodes.
The dataplane-operator's CRD includes support for specifying additional
volume mounts for the ansibleee pods, which provides a mechanism for accessing
a local copy of edpm-ansible. This makes it possible to develop and test local
changes to edpm-ansible without having to build and deploy a new
openstack-ansibleee-runner container image.

Provide NFS access to your edpm-ansible directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The technique described here uses NFS to access the edpm-ansible directory on
your development system, so you'll need to install an NFS server and create
an appropriate export on your development system. Of course, this implies
your OpenShift deployment that runs the dataplane-operator has access to
the NFS server, including any required firewall rules.

* `EL 8 instructions <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/deploying_different_types_of_servers/exporting-nfs-shares_deploying-different-types-of-servers#assembly_configuring-the-nfs-server-to-run-behind-a-firewall_exporting-nfs-shares>`_
* `EL 9 instructions <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/managing_file_systems/exporting-nfs-shares_managing-file-systems#assembly_configuring-the-nfs-server-to-run-behind-a-firewall_exporting-nfs-shares>`_

When using OpenShift Local (aka CRC), your export will be something like this:

.. code-block:: console

    % cat <<EOF >/etc/exports
    ${HOME}/edpm-ansible 192.168.130.0/24(rw,sync,no_root_squash)
    EOF

    % exportfs -r

.. tip::

   CRC installs its own firewall rules, which likely will need to be adjusted
   depending on the location of your NFS server. If your edpm-ansible
   directory is on the same system that hosts your CRC, then the simplest
   thing to do is insert a rule that essentially circumvents the other rules:

   % nft add rule inet firewalld filter_IN_libvirt_pre accept

Create edpm-ansible PV and PVC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create an NFS PV, and a PVC that can be mounted on the ansibleee pods.

.. note::

   While it's possible to add an NFS volume directly to a pod, the default k8s
   Security Context Constraint (SCC) for non-privileged pods does not permit
   NFS volume mounts. The approach of using an NFS PV and PVC works just as
   well, and avoids the need to fiddle with SCC policies.

.. code-block:: console

    % # E.g. ${HOME}/edpm-ansible
    % NFS_SHARE=<Path to your edpm-ansible directory>
    % NFS_SERVER=<IP of your NFS server>
    % cat <<EOF >edpm-ansible-storage.yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: edpm-ansible
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
      name: edpm-ansible
    spec:
      storageClassName: edpm-ansible
      accessModes:
        - ReadOnlyMany
      resources:
        requests:
          storage: 1Gi
    EOF

    % oc apply -f edpm-ansible-storage.yaml

Add extraMount to your OpenStackDataPlane CR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use kustomize or "oc edit" to add the edpm-ansible PVC to the
OpenStackDataPlane's /spec/nodeTemplate/extraMounts. The
mountPath is where the edpm-ansible *roles* and *plugins* directories are
located inside the openstack-ansibleee-runner container image. The
OpenStackDataPlane CR should contain the following snippet:

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
            claimName: edpm-ansible
            readOnly: true
