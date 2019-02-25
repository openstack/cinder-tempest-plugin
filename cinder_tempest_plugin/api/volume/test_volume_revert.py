# Copyright (c) 2017 Huawei.
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
from tempest.lib import exceptions

from cinder_tempest_plugin.api.volume import base
from cinder_tempest_plugin import cinder_clients

CONF = config.CONF


class VolumeRevertTests(base.BaseVolumeTest):
    min_microversion = '3.40'

    @classmethod
    def skip_checks(cls):
        super(VolumeRevertTests, cls).skip_checks()
        if not CONF.volume_feature_enabled.volume_revert:
            raise cls.skipException("Cinder volume revert feature disabled")

    @classmethod
    def setup_clients(cls):
        cls._api_version = 3
        super(VolumeRevertTests, cls).setup_clients()

        manager = cinder_clients.Manager(cls.os_primary)
        cls.volume_revert_client = manager.volume_revert_client

    def setUp(self):
        super(VolumeRevertTests, self).setUp()
        # Create volume
        self.volume = self.create_volume()
        # Create snapshot
        self.snapshot = self.create_snapshot(self.volume['id'],
                                             metadata={'mykey1': 'value1'})

    @decorators.idempotent_id('87b7dcb7-4950-4a3a-802c-ece55491846d')
    def test_volume_revert_to_snapshot(self):
        """Test revert to snapshot"""
        expected_size = self.volume['size']
        # Revert to snapshot
        self.volume_revert_client.revert_to_snapshot(self.volume,
                                                     self.snapshot['id'])
        waiters.wait_for_volume_resource_status(
            self.volumes_client,
            self.volume['id'], 'available')
        waiters.wait_for_volume_resource_status(
            self.snapshots_client,
            self.snapshot['id'], 'available')
        volume = self.volumes_client.show_volume(self.volume['id'])['volume']

        self.assertEqual(expected_size, volume['size'])

    @decorators.idempotent_id('4e8b0788-87fe-430d-be7a-444d7f8e0347')
    def test_volume_revert_to_snapshot_after_extended_negative(self):
        """Test revert to snapshot after extended"""
        # Extend volume to double the size
        expected_size = self.volume['size'] * 2
        # Extend the volume
        self.volumes_client.extend_volume(self.volume['id'],
                                          new_size=expected_size)
        waiters.wait_for_volume_resource_status(self.volumes_client,
                                                self.volume['id'], 'available')

        # Destination volume smaller than source, API should block that
        self.assertRaises(exceptions.BadRequest,
                          self.volume_revert_client.revert_to_snapshot,
                          self.volume, self.snapshot)
