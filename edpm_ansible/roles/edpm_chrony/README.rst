chrony
======

A role to manage chrony

Role Variables
--------------

.. list-table:: Variables used for chrony
   :widths: auto
   :header-rows: 1

   * - Name
     - Default Value
     - Description
   * - `epdm_chrony_debug`
     - `False`
     - Enable debug option in chrony
   * - `epdm_chrony_role_action`
     - `all`
     - Ansible action when including the role. Should be one of: [all|install|config|upgrade|online]
   * - `epdm_chrony_package_name`
     - `chrony`
     - chrony system package name
   * - `epdm_chrony_service_name`
     - `chronyd`
     - chrony system service name
   * - `epdm_chrony_manage_service`
     - `True`
     - Flag used to specific if the ansible role should manage the service
   * - `epdm_chrony_manage_package`
     - `True`
     - Flag used to specific if the ansible role should manage the package
   * - `epdm_chrony_service_state`
     - `started`
     - Default service state to configure (started|stopped)
   * - `epdm_chrony_config_file_location`
     - `/etc/chrony.conf`
     - Chrony configuration file location.
   * - `epdm_chrony_driftfile_path`
     - `/var/lib/chrony/drift`
     - Chrony drift file location
   * - `epdm_chrony_logdir_path`
     - `/var/log/chrony`
     - Chrony log directory location
   * - `epdm_chrony_ntp_servers`
     - `[]`
     - List of NTP servers. This can be a list of hashes for advanced configuration.
       If using the hash format, a `server_name` and `server_settings` key should be populated with
       the appropriate data. If this is a list of hostnames, the `epdm_chrony_global_server_settings`
       will be appended to the configuration.
   * - `epdm_chrony_global_server_settings`
     - `<none>`
     - Default setting to apply to the servers configuration
   * - `epdm_chrony_ntp_pools`
     - `[]`
     - List of NTP pools. This can be a list of hashes for advanced configuration.
       If using the hash format, a `pool_name` and `pool_settings` key should be populated with
       the appropriate data. If this is a list of hostnames, the `epdm_chrony_global_pool_settings`
       will be appended to the configuration.
   * - `epdm_chrony_global_pool_settings`
     - `<none>`
     - Default setting to apply to the pools configuration
   * - `epdm_chrony_ntp_peers`
     - `[]`
     - List of NTP peers. This can be a list of hashes for advanced configuration.
       If using the hash format, a `peer_name` and `peer_settings` key should be populated with
       the appropriate data. If this is a list of hostnames, the `epdm_chrony_global_peer_settings`
       will be appended to the configuration.
   * - `epdm_chrony_global_peer_settings`
     - `<none>`
     - Default setting to apply to the peers configuration
   * - `epdm_chrony_bind_addresses`
     - `['127.0.0.1', '::1']`
     - List of addresses to bind to to listen for command packets
   * - `epdm_chrony_acl_rules`
     - `[]`
     - List of specific allow/deny commands for the configuration file
   * - `epdm_chrony_rtc_settings`
     - `['rtcsync']`
     - List of specific real time lock settings
   * - `epdm_chrony_makestep`
     - `1.0 3`
     - The chrony makestep configuration
   * - `epdm_chrony_extra_options`
     - `[]`
     - A list of extra option strings that is added to the end of the configuration file. This list is joined with new lines.


Requirements
------------

 - ansible >= 2.9
 - python >= 2.6

Dependencies
------------

None

Example Playbooks
-----------------

.. code-block::

    - hosts: localhost
      become: true
      roles:
        - chrony

License
-------

Apache 2.0
