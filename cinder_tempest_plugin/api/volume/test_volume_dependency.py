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


from tempest.common import utils
from tempest.common import waiters
from tempest import config
from tempest.lib import decorators
import testtools

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

    def _delete_vol_and_wait(self, vol_id):
        self.volumes_client.delete_volume(vol_id)

        self.volumes_client.wait_for_resource_deletion(vol_id)

    def _delete_snap_and_wait(self, snap_id):
        self.snapshots_client.delete_snapshot(snap_id)

        self.snapshots_client.wait_for_resource_deletion(snap_id)

    @decorators.idempotent_id('f8278e5c-50ff-4a1d-8670-3ca0866d411a')
    def test_delete_dep_chain(self):
        """Test a complex chain of volume and snapshot dependency deletion."""
        volume_1 = self.create_volume()['id']
        snapshot_of_vol_1 = self.create_snapshot(volume_1)['id']

        volume_2_args = {'snapshot_id': snapshot_of_vol_1}
        volume_2 = self.create_volume(**volume_2_args)['id']

        snapshot_of_vol_2 = self.create_snapshot(volume_2)['id']

        volume_3_args = {'snapshot_id': snapshot_of_vol_2}
        volume_3 = self.create_volume(**volume_3_args)['id']

        volume_4_args = {'source_volid': volume_3}
        volume_4 = self.create_volume(**volume_4_args)['id']

        self._delete_snap_and_wait(snapshot_of_vol_1)
        self._delete_snap_and_wait(snapshot_of_vol_2)

        self._delete_vol_and_wait(volume_3)
        self._delete_vol_and_wait(volume_1)
        self._delete_vol_and_wait(volume_2)
        self._delete_vol_and_wait(volume_4)

    @decorators.idempotent_id('63447ef8-e667-4796-ba66-1b9b883af1f1')
    def test_delete_dep_chain_2(self):
        """Test a different chain of volume/snapshot dependency deletion."""
        volume_1 = self.create_volume()['id']
        snapshot_of_vol_1 = self.create_snapshot(volume_1)['id']

        volume_2_args = {'snapshot_id': snapshot_of_vol_1}
        volume_2 = self.create_volume(**volume_2_args)['id']

        snapshot_of_vol_2 = self.create_snapshot(volume_2)['id']

        volume_3_args = {'snapshot_id': snapshot_of_vol_2}
        volume_3 = self.create_volume(**volume_3_args)['id']

        self._delete_snap_and_wait(snapshot_of_vol_1)
        self._delete_snap_and_wait(snapshot_of_vol_2)

        self._delete_vol_and_wait(volume_1)
        self._delete_vol_and_wait(volume_2)
        self._delete_vol_and_wait(volume_3)


class VolumeImageDependencyTests(base.BaseVolumeTest):
    """Volume<->image dependency tests.

    These tests perform clones to/from volumes and images,
    deleting images/volumes that other volumes were cloned from.

    Images and volumes are expected to be independent at the OpenStack
    level, but in some configurations (i.e. when using Ceph as storage
    for both Cinder and Glance) it was possible to end up with images
    or volumes that could not be deleted.  This was fixed for RBD in
    Cinder 2024.1 change I009d0748f.

    """

    min_microversion = '3.40'

    @classmethod
    def del_image(cls, image_id):
        images_client = cls.os_primary.image_client_v2
        images_client.delete_image(image_id)
        images_client.wait_for_resource_deletion(image_id)

    @testtools.skipUnless(CONF.volume_feature_enabled.volume_image_dep_tests,
                          reason='Volume/image dependency tests not enabled.')
    @utils.services('image', 'volume')
    @decorators.idempotent_id('7a9fba78-2e4b-42b1-9898-bb4a60685320')
    def test_image_volume_dependencies_1(self):
        # image -> volume
        image_args = {
            'disk_format': 'raw',
            'container_format': 'bare',
            'name': 'image-for-test-7a9fba78-2e4b-42b1-9898-bb4a60685320'
        }
        image = self.create_image_with_data(**image_args)

        # create a volume from the image
        vol_args = {'name': ('volume1-for-test'
                             '7a9fba78-2e4b-42b1-9898-bb4a60685320'),
                    'imageRef': image['id']}
        volume1 = self.create_volume(**vol_args)
        waiters.wait_for_volume_resource_status(self.volumes_client,
                                                volume1['id'],
                                                'available')

        self.volumes_client.delete_volume(volume1['id'])
        self.volumes_client.wait_for_resource_deletion(volume1['id'])

        self.del_image(image['id'])

    @testtools.skipUnless(CONF.volume_feature_enabled.volume_image_dep_tests,
                          reason='Volume/image dependency tests not enabled.')
    @utils.services('image', 'volume')
    @decorators.idempotent_id('0e20bd6e-440f-41d8-9b5d-fc047ac00423')
    def test_image_volume_dependencies_2(self):
        # image -> volume -> volume

        image_args = {
            'disk_format': 'raw',
            'container_format': 'bare',
            'name': 'image-for-test-0e20bd6e-440f-41d8-9b5d-fc047ac00423'
        }
        image = self.create_image_with_data(**image_args)

        # create a volume from the image
        vol_args = {'name': ('volume1-for-test'
                             '0e20bd6e-440f-41d8-9b5d-fc047ac00423'),
                    'imageRef': image['id']}
        volume1 = self.create_volume(**vol_args)
        waiters.wait_for_volume_resource_status(self.volumes_client,
                                                volume1['id'],
                                                'available')

        vol2_args = {'name': ('volume2-for-test-'
                              '0e20bd6e-440f-41d8-9b5d-fc047ac00423'),
                     'source_volid': volume1['id']}
        volume2 = self.create_volume(**vol2_args)
        waiters.wait_for_volume_resource_status(self.volumes_client,
                                                volume2['id'],
                                                'available')

        self.volumes_client.delete_volume(volume1['id'])
        self.volumes_client.wait_for_resource_deletion(volume1['id'])

        self.del_image(image['id'])

    @testtools.skipUnless(CONF.volume_feature_enabled.volume_image_dep_tests,
                          reason='Volume/image dependency tests not enabled.')
    @decorators.idempotent_id('e6050452-06bd-4c7f-9912-45178c83e379')
    @utils.services('image', 'volume')
    def test_image_volume_dependencies_3(self):
        # image -> volume -> snap -> volume

        image_args = {
            'disk_format': 'raw',
            'container_format': 'bare',
            'name': 'image-for-test-e6050452-06bd-4c7f-9912-45178c83e379'
        }
        image = self.create_image_with_data(**image_args)

        # create a volume from the image
        vol_args = {'name': ('volume1-for-test'
                             'e6050452-06bd-4c7f-9912-45178c83e379'),
                    'imageRef': image['id']}
        volume1 = self.create_volume(**vol_args)
        waiters.wait_for_volume_resource_status(self.volumes_client,
                                                volume1['id'],
                                                'available')

        snapshot1 = self.create_snapshot(volume1['id'])

        vol2_args = {'name': ('volume2-for-test-'
                              'e6050452-06bd-4c7f-9912-45178c83e379'),
                     'snapshot_id': snapshot1['id']}
        volume2 = self.create_volume(**vol2_args)
        waiters.wait_for_volume_resource_status(self.volumes_client,
                                                volume2['id'],
                                                'available')

        self.snapshots_client.delete_snapshot(snapshot1['id'])
        self.snapshots_client.wait_for_resource_deletion(snapshot1['id'])

        self.volumes_client.delete_volume(volume2['id'])
        self.volumes_client.wait_for_resource_deletion(volume2['id'])

        self.del_image(image['id'])

        self.volumes_client.delete_volume(volume1['id'])
        self.volumes_client.wait_for_resource_deletion(volume1['id'])
