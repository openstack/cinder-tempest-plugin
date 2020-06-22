# Copyright 2017 NEC Corporation.
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

from tempest.api.volume import api_microversion_fixture
from tempest.common import compute
from tempest.common import waiters
from tempest import config
from tempest.lib.common import api_version_utils
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest import test

CONF = config.CONF


class BaseVolumeTest(api_version_utils.BaseMicroversionTest,
                     test.BaseTestCase):
    """Base test case class for all Cinder API tests."""

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(BaseVolumeTest, cls).skip_checks()

        if not CONF.service_available.cinder:
            skip_msg = ("%s skipped as Cinder is not available" % cls.__name__)
            raise cls.skipException(skip_msg)

        api_version_utils.check_skip_with_microversion(
            cls.min_microversion, cls.max_microversion,
            CONF.volume.min_microversion, CONF.volume.max_microversion)

    @classmethod
    def setup_clients(cls):
        super(BaseVolumeTest, cls).setup_clients()
        cls.backups_client = cls.os_primary.backups_client_latest
        cls.volumes_client = cls.os_primary.volumes_client_latest
        cls.snapshots_client = cls.os_primary.snapshots_client_latest

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super(BaseVolumeTest, cls).setup_credentials()

    def setUp(self):
        super(BaseVolumeTest, self).setUp()
        self.useFixture(api_microversion_fixture.APIMicroversionFixture(
            self.request_microversion))

    @classmethod
    def resource_setup(cls):
        super(BaseVolumeTest, cls).resource_setup()
        cls.request_microversion = (
            api_version_utils.select_request_microversion(
                cls.min_microversion,
                CONF.volume.min_microversion))

    @classmethod
    def create_volume(cls, wait_until='available', **kwargs):
        """Wrapper utility that returns a test volume.

           :param wait_until: wait till volume status.
        """
        if 'size' not in kwargs:
            kwargs['size'] = CONF.volume.volume_size

        if 'imageRef' in kwargs:
            image = cls.os_primary.image_client_v2.show_image(
                kwargs['imageRef'])
            min_disk = image['min_disk']
            kwargs['size'] = max(kwargs['size'], min_disk)

        if 'name' not in kwargs:
            name = data_utils.rand_name(cls.__name__ + '-Volume')
            kwargs['name'] = name

        volume = cls.volumes_client.create_volume(**kwargs)['volume']
        cls.addClassResourceCleanup(
            cls.volumes_client.wait_for_resource_deletion, volume['id'])
        cls.addClassResourceCleanup(test_utils.call_and_ignore_notfound_exc,
                                    cls.volumes_client.delete_volume,
                                    volume['id'])
        waiters.wait_for_volume_resource_status(cls.volumes_client,
                                                volume['id'], wait_until)
        return volume

    @classmethod
    def create_snapshot(cls, volume_id=1, **kwargs):
        """Wrapper utility that returns a test snapshot."""
        if 'name' not in kwargs:
            name = data_utils.rand_name(cls.__name__ + '-Snapshot')
            kwargs['name'] = name

        snapshot = cls.snapshots_client.create_snapshot(
            volume_id=volume_id, **kwargs)['snapshot']
        cls.addClassResourceCleanup(
            cls.snapshots_client.wait_for_resource_deletion, snapshot['id'])
        cls.addClassResourceCleanup(test_utils.call_and_ignore_notfound_exc,
                                    cls.snapshots_client.delete_snapshot,
                                    snapshot['id'])
        waiters.wait_for_volume_resource_status(cls.snapshots_client,
                                                snapshot['id'], 'available')
        return snapshot

    def create_backup(self, volume_id, backup_client=None, **kwargs):
        """Wrapper utility that returns a test backup."""
        if backup_client is None:
            backup_client = self.backups_client
        if 'name' not in kwargs:
            name = data_utils.rand_name(self.__class__.__name__ + '-Backup')
            kwargs['name'] = name

        backup = backup_client.create_backup(
            volume_id=volume_id, **kwargs)['backup']
        self.addCleanup(backup_client.wait_for_resource_deletion, backup['id'])
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        backup_client.delete_backup, backup['id'])
        waiters.wait_for_volume_resource_status(backup_client, backup['id'],
                                                'available')
        return backup

    def create_server(self, wait_until='ACTIVE', **kwargs):
        name = kwargs.pop(
            'name',
            data_utils.rand_name(self.__class__.__name__ + '-instance'))

        tenant_network = self.get_tenant_network()
        body, _ = compute.create_test_server(
            self.os_primary,
            tenant_network=tenant_network,
            name=name,
            wait_until=wait_until,
            **kwargs)

        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        waiters.wait_for_server_termination,
                        self.os_primary.servers_client, body['id'])
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.os_primary.servers_client.delete_server,
                        body['id'])
        return body


class BaseVolumeAdminTest(BaseVolumeTest):
    """Base test case class for all Volume Admin API tests."""

    credentials = ['primary', 'admin']

    @classmethod
    def setup_clients(cls):
        super(BaseVolumeAdminTest, cls).setup_clients()

        cls.admin_volume_types_client = cls.os_admin.volume_types_client_latest
        cls.admin_backups_client = cls.os_admin.backups_client_latest
        cls.admin_volumes_client = cls.os_admin.volumes_client_latest

    @classmethod
    def create_volume_type(cls, name=None, **kwargs):
        """Create a test volume-type"""

        name = name or data_utils.rand_name(cls.__name__ + '-volume-type')
        volume_type = cls.admin_volume_types_client.create_volume_type(
            name=name, **kwargs)['volume_type']
        cls.addClassResourceCleanup(cls._clear_volume_type, volume_type)
        return volume_type

    @classmethod
    def _clear_volume_type(cls, volume_type):
        # If image caching is enabled, we must delete the cached volume
        # before cinder will allow us to delete the volume_type.  This function
        # solves that problem by taking the brute-force approach of deleting
        # any volumes of this volume_type that exist *no matter what project
        # they are in*.  Since this won't happen until the teardown of the
        # test class, that should be OK.
        type_id = volume_type['id']
        type_name = volume_type['name']

        volumes = cls.admin_volumes_client.list_volumes(
            detail=True, params={'all_tenants': 1})['volumes']
        for volume in [v for v in volumes if v['volume_type'] == type_name]:
            test_utils.call_and_ignore_notfound_exc(
                cls.admin_volumes_client.delete_volume, volume['id'])
            cls.admin_volumes_client.wait_for_resource_deletion(volume['id'])

        test_utils.call_and_ignore_notfound_exc(
            cls.admin_volume_types_client.delete_volume_type, type_id)
        test_utils.call_and_ignore_notfound_exc(
            cls.admin_volume_types_client.wait_for_resource_deletion, type_id)
