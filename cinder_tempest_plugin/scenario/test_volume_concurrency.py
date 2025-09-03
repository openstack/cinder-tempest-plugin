# Copyright 2025 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from tempest.common import utils
from tempest.common import waiters
from tempest import config
from tempest.lib import decorators

from cinder_tempest_plugin.common import concurrency
from cinder_tempest_plugin.scenario import manager

CONF = config.CONF


class ConcurrentVolumeActionsTest(manager.ScenarioTest):

    @classmethod
    def skip_checks(cls):
        super(ConcurrentVolumeActionsTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.concurrency_tests:
            raise cls.skipException(
                "Concurrency tests are disabled.")

    def _resource_create(self, index, resource_ids, create_func,
                         resource_id_key='id', **kwargs):
        """Generic resource creation logic.

        Handles both single and indexed resource creation.
        If any list-type arguments are passed (e.g., volume_ids),
        they are indexed using `index`.
        """

        # Prepare arguments, indexing into lists if necessary
        adjusted_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, list):
                # For list arguments, pick the value by index
                adjusted_kwargs[key] = value[index]
            else:
                adjusted_kwargs[key] = value

        resource = create_func(**adjusted_kwargs)
        resource_ids.append(resource[resource_id_key])

    def _attach_volume_action(self, index, resource_ids, server_id,
                              volume_ids):
        """Attach the given volume to the server."""
        volume_id = volume_ids[index]
        self.servers_client.attach_volume(
            server_id, volumeId=volume_id, device=None)
        waiters.wait_for_volume_resource_status(
            self.volumes_client, volume_id, 'in-use')
        resource_ids.append((server_id, volume_id))

    def _cleanup_resources(self, resource_ids, delete_func, wait_func):
        """Delete and wait for resource cleanup."""
        for res_id in resource_ids:
            delete_func(res_id)
            wait_func(res_id)

    @utils.services('volume')
    @decorators.idempotent_id('ceb4f3c2-b2a4-48f9-82a8-3d32cdb5b375')
    def test_create_volumes(self):
        """Test parallel volume creation."""
        volume_ids = concurrency.run_concurrent_tasks(
            self._resource_create,
            create_func=self.create_volume,
        )

        self._cleanup_resources(volume_ids,
                                self.volumes_client.delete_volume,
                                self.volumes_client.wait_for_resource_deletion)

    @utils.services('volume')
    @decorators.idempotent_id('6aa893a6-dfd0-4a0b-ae15-2fb24342e48d')
    def test_create_snapshots(self):
        """Test parallel snapshot creation from a single volume."""
        volume = self.create_volume()

        snapshot_ids = concurrency.run_concurrent_tasks(
            self._resource_create,
            create_func=self.create_volume_snapshot,
            volume_id=volume['id']
        )

        self._cleanup_resources(
            snapshot_ids,
            self.snapshots_client.delete_snapshot,
            self.snapshots_client.wait_for_resource_deletion)

    @utils.services('compute', 'volume')
    @decorators.idempotent_id('4c038386-00b0-4a6d-a612-48a4e0a96fa6')
    def test_attach_volumes_to_server(self):
        """Test parallel volume attachment to a server."""
        server = self.create_server(wait_until='ACTIVE')
        server_id = server['id']

        volume_ids = concurrency.run_concurrent_tasks(
            self._resource_create,
            create_func=self.create_volume
        )

        attach_ids = concurrency.run_concurrent_tasks(
            self._attach_volume_action,
            server_id=server_id,
            volume_ids=volume_ids
        )

        for server_id, volume_id in attach_ids:
            self.servers_client.detach_volume(server_id, volume_id)
            waiters.wait_for_volume_resource_status(self.volumes_client,
                                                    volume_id, 'available')

        self._cleanup_resources(volume_ids,
                                self.volumes_client.delete_volume,
                                self.volumes_client.wait_for_resource_deletion)

    @utils.services('volume')
    @decorators.idempotent_id('01f66de8-b217-4588-ab7f-e707d1931156')
    def test_create_backups_and_restores(self):
        """Test parallel backup creation and restore from multiple volumes."""

        # Step 1: Create volumes in concurrency
        volume_ids = concurrency.run_concurrent_tasks(
            self._resource_create,
            create_func=self.create_volume
        )

        # Step 2: Create backups in concurrency
        backup_ids = concurrency.run_concurrent_tasks(
            self._resource_create,
            create_func=self.create_backup,
            volume_id=volume_ids
        )

        # Step 3: Restore backups in concurrency
        restored_vol_ids = concurrency.run_concurrent_tasks(
            self._resource_create,
            create_func=self.restore_backup,
            resource_id_key='volume_id',
            backup_id=backup_ids
        )

        # Step 4: Cleanup all resources
        self._cleanup_resources(
            backup_ids,
            self.backups_client.delete_backup,
            self.backups_client.wait_for_resource_deletion)

        self._cleanup_resources(
            volume_ids,
            self.volumes_client.delete_volume,
            self.volumes_client.wait_for_resource_deletion)

        self._cleanup_resources(
            restored_vol_ids,
            self.volumes_client.delete_volume,
            self.volumes_client.wait_for_resource_deletion)
