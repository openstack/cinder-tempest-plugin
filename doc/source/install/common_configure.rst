2. Edit the ``/etc/cinder_tempest_plugin/cinder_tempest_plugin.conf`` file and complete the following
   actions:

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://cinder_tempest_plugin:CINDER_TEMPEST_PLUGIN_DBPASS@controller/cinder_tempest_plugin
