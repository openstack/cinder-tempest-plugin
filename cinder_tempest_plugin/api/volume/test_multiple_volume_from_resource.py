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

from tempest.common import waiters
from tempest import config
from tempest.lib import decorators

from cinder_tempest_plugin.api.volume import base

CONF = config.CONF


class CreateVolumesFromSnapshotTest(base.CreateMultipleResourceTest):

    @decorators.idempotent_id('3b879ad1-d861-4ad3-b2c8-c89162e867c3')
    def test_create_multiple_volume_from_snapshot(self):
        """Create multiple volumes from a snapshot."""

        volume = self.create_volume()
        snapshot = self.create_snapshot(volume_id=volume['id'])
        kwargs_create = {"'snapshot_id": snapshot['id'], "wait_until": None}
        res = self._create_multiple_resource(self.create_volume,
                                             **kwargs_create)
        kwargs_wait = {"client": self.volumes_client, "status": "available"}
        self._wait_for_multiple_resources(
            waiters.wait_for_volume_resource_status, res, **kwargs_wait)


class CreateVolumesFromSourceVolumeTest(base.CreateMultipleResourceTest):

    @decorators.idempotent_id('b4a250d1-3ffd-4727-a2f5-9d858b298558')
    def test_create_multiple_volume_from_source_volume(self):
        """Create multiple volumes from a source volume.

        The purpose of this test is to check the synchronization
        of driver clone method with simultaneous requests.
        """

        volume = self.create_volume()
        kwargs_create = {"'source_volid": volume['id'], "wait_until": None}
        res = self._create_multiple_resource(self.create_volume,
                                             **kwargs_create)
        kwargs_wait = {"client": self.volumes_client, "status": "available"}
        self._wait_for_multiple_resources(
            waiters.wait_for_volume_resource_status, res, **kwargs_wait)


class CreateVolumesFromBackupTest(base.CreateMultipleResourceTest):

    @classmethod
    def skip_checks(cls):
        super(CreateVolumesFromBackupTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.backup:
            raise cls.skipException("Cinder backup feature disabled")

    @decorators.idempotent_id('9db67083-bf1a-486c-8f77-3778467f39a1')
    def test_create_multiple_volume_from_backup(self):
        """Create multiple volumes from a backup."""

        volume = self.create_volume()
        backup = self.create_backup(volume_id=volume['id'])
        kwargs_create = {"'backup_id": backup['id'], "wait_until": None}
        res = self._create_multiple_resource(self.create_volume,
                                             **kwargs_create)
        kwargs_wait = {"client": self.volumes_client, "status": "available"}
        self._wait_for_multiple_resources(
            waiters.wait_for_volume_resource_status, res, **kwargs_wait)


class CreateVolumesFromImageTest(base.CreateMultipleResourceTest):

    @classmethod
    def skip_checks(cls):
        super(CreateVolumesFromImageTest, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException("Glance service is disabled")

    @decorators.idempotent_id('8976a11b-1ddc-49b6-b66f-8c26adf3fa9e')
    def test_create_from_image_multiple(self):
        """Create a handful of volumes from the same image at once.

        The purpose of this test is to stress volume drivers,
        image download, the image cache, etc., within Cinder.
        """

        img_uuid = CONF.compute.image_ref

        kwargs_create = {"'imageRef": img_uuid, "wait_until": None}
        res = self._create_multiple_resource(self.create_volume,
                                             **kwargs_create)
        kwargs_wait = {"client": self.volumes_client, "status": "available"}
        self._wait_for_multiple_resources(
            waiters.wait_for_volume_resource_status, res, **kwargs_wait)
