# Copyright 2022 Red Hat, Inc.
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

from tempest import config
from tempest.lib import decorators

from cinder_tempest_plugin.api.volume import base

CONF = config.CONF


class VolumeDependencyTests(base.BaseVolumeTest):
    min_microversion = '3.40'

    @classmethod
    def setup_clients(cls):
        super(VolumeDependencyTests, cls).setup_clients()

    @decorators.idempotent_id('42e9df95-854b-4840-9d55-ae62f65e9b8e')
    def test_delete_source_volume(self):
        """Test basic dependency deletion

        * Create a volume with source_volid
        * Delete the source volume
        """
        source_volume = self.create_volume()
        kwargs = {'source_volid': source_volume['id']}
        cloned_volume = self.create_volume(**kwargs)
        self.assertEqual(source_volume['id'], cloned_volume['source_volid'])
        self.volumes_client.delete_volume(source_volume['id'])
        self.volumes_client.wait_for_resource_deletion(source_volume['id'])

    @decorators.idempotent_id('900d8ea5-2afd-4fe5-a0c3-fab4744f0d40')
    def test_delete_source_snapshot(self):
        """Test basic dependency deletion with snapshot

        * Create a snapshot from source volume
        * Create a volume from that snapshot
        * Delete the source snapshot
        * Delete the source volume
        """
        source_volume = self.create_volume()
        snapshot_source_volume = self.create_snapshot(source_volume['id'])
        kwargs = {'snapshot_id': snapshot_source_volume['id']}
        volume_from_snapshot = self.create_volume(**kwargs)
        self.assertEqual(volume_from_snapshot['snapshot_id'],
                         snapshot_source_volume['id'])

        self.snapshots_client.delete_snapshot(snapshot_source_volume['id'])
        self.snapshots_client.wait_for_resource_deletion(
            snapshot_source_volume['id'])
        self.volumes_client.delete_volume(source_volume['id'])
        self.volumes_client.wait_for_resource_deletion(source_volume['id'])
