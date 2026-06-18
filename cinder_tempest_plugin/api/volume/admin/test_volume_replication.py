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
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.common import waiters
from tempest import config
from tempest.lib import decorators

from cinder_tempest_plugin.api.volume import base


CONF = config.CONF


class VolumeReplicationTest(base.BaseVolumeAdminTest):

    volume_min_microversion = '3.26'
    volume_max_microversion = 'latest'

    @classmethod
    def skip_checks(cls):
        super(VolumeReplicationTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.replication:
            raise cls.skipException("Volume replication feature disabled")
        if len(CONF.volume.backend_names) < 2:
            raise cls.skipException("Requires at least two different "
                                    "backend names")

    @classmethod
    def setup_clients(cls):
        super(VolumeReplicationTest, cls).setup_clients()
        cls.admin_volume_services_client = (
            cls.os_admin.volume_services_client_latest)
        cls.admin_stats_client = (
            cls.os_admin.volume_scheduler_stats_client_latest)

    @classmethod
    def resource_setup(cls):
        super(VolumeReplicationTest, cls).resource_setup()

        pools = cls.admin_stats_client.list_pools(detail=True)['pools']
        replication_pools = [
            pool['name'] for pool in pools if
            pool['capabilities']['replication_enabled']
        ]
        if not replication_pools:
            raise cls.skipException(
                "No backend with replication_enabled=True found.")
        cls.replication_host, replication_backend = (
            replication_pools[0].split('#', 1))
        cls.replication_specs = {
            'replication_enabled': '<is> True',
            'volume_backend_name': replication_backend,
        }

    def _create_replicated_volume(self):
        # Create a volume type with replication support
        replication_volume_type = self.create_volume_type(
            extra_specs=self.replication_specs)

        # Create a volume from the replication volume type
        volume = self.create_volume(volume_type=replication_volume_type['id'])

        # Ensure volume is in 'enabled' replication state
        volume_details = self.volumes_client.show_volume(
            volume['id'])['volume']
        self.assertEqual(volume_details['replication_status'], 'enabled')

        return volume

    @decorators.idempotent_id('4813e87d-89cf-4d5e-b020-eb611135540b')
    def test_replicated_volume(self):
        self._create_replicated_volume()

    @decorators.idempotent_id('9c0e1be5-ded2-4f29-8e97-4a7d20a528c2')
    def test_extend_replicated_volume(self):
        """Test extending a replicated volume."""

        # Step 1: Create a replicated volume
        volume = self._create_replicated_volume()
        original_size = volume['size']
        new_size = original_size + 1

        # Step 2: Extend the volume
        self.volumes_client.extend_volume(volume['id'], new_size=new_size)

        # Step 3: Wait until volume status is 'available'
        waiters.wait_for_volume_resource_status(
            self.volumes_client, volume['id'], 'available')

        # Step 4: Validate new size and replication status
        volume_details = self.volumes_client.show_volume(
            volume['id'])['volume']
        self.assertEqual(volume_details['size'], new_size)

    @decorators.idempotent_id('43c799bf-1a67-4384-9c1c-dd06247b0f53')
    def test_clone_replicated_volume(self):
        volume = self._create_replicated_volume()
        cloned_volume = self.create_volume(source_volid=volume['id'])
        cloned_vol_details = self.volumes_client.show_volume(
            cloned_volume['id'])['volume']

        self.assertEqual(volume['id'],
                         cloned_vol_details['source_volid'])
        self.assertEqual(cloned_vol_details['replication_status'], 'enabled')

    @decorators.idempotent_id('d8c61a5b-4b87-4b46-a97e-9a71ed40a41c')
    def test_snapshot_replicated_volume(self):
        volume = self._create_replicated_volume()
        snapshot = self.create_snapshot(volume['id'])
        snapshot_details = self.snapshots_client.show_snapshot(
            snapshot['id'])['snapshot']
        self.assertEqual(volume['id'], snapshot_details['volume_id'])
