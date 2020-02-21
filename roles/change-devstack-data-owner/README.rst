Change the ownership of a specific devstack data subdirectory

This is needed in order to have cinderlib functional tests,
which are normally executed by the `zuul` user, run under
a devstack deployment where the `stack` user is the owner.

**Role Variables**

.. zuul:rolevar:: devstack_data_dir
   :default: /opt/stack/data

   The devstack data directory.

.. zuul:rolevar:: devstack_data_subdir_changed
   :default: cinder

   The devstack data subdirectory whose ownership
   is changed.

.. zuul:rolevar:: devstack_data_subdir_owner
   :default: zuul

   The new owner of the specified devstack data subdirectory.
