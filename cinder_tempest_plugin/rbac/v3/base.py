
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
from tempest.lib.common import api_version_utils
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib.decorators import cleanup_order
from tempest import test

CONF = config.CONF


class VolumeV3RbacBaseTests(
    api_version_utils.BaseMicroversionTest, test.BaseTestCase
):
    identity_version = 'v3'

    @classmethod
    def skip_checks(cls):
        super(VolumeV3RbacBaseTests, cls).skip_checks()
        if not CONF.enforce_scope.cinder:
            raise cls.skipException(
                "Tempest is not configured to enforce_scope for cinder, "
                "skipping RBAC tests. To enable these tests set "
                "`tempest.conf [enforce_scope] cinder=True`."
            )
        if not CONF.service_available.cinder:
            skip_msg = ("%s skipped as Cinder is not available" % cls.__name__)
            raise cls.skipException(skip_msg)
        api_version_utils.check_skip_with_microversion(
            cls.min_microversion, cls.max_microversion,
            CONF.volume.min_microversion, CONF.volume.max_microversion)

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super(VolumeV3RbacBaseTests, cls).setup_credentials()

    def setUp(self):
        super(VolumeV3RbacBaseTests, self).setUp()

    @classmethod
    def resource_setup(cls):
        super(VolumeV3RbacBaseTests, cls).resource_setup()
        cls.request_microversion = (
            api_version_utils.select_request_microversion(
                cls.min_microversion,
                CONF.volume.min_microversion))
        cls.setup_api_microversion_fixture(
            volume_microversion=cls.request_microversion)

    def do_request(self, method, expected_status=200, client=None, **payload):
        """Perform API call

        Args:
            method: Name of the API call
            expected_status: HTTP desired response code
            client: Client object if exists, None otherwise
            payload: API call required parameters

        Returns:
            HTTP response
        """
        if not client:
            client = self.client
        if isinstance(expected_status, type(Exception)):
            self.assertRaises(expected_status,
                              getattr(client, method),
                              **payload)
        else:
            response = getattr(client, method)(**payload)
            self.assertEqual(response.response.status, expected_status)
            return response

    @cleanup_order
    def create_volume(self, client, **kwargs):
        """Wrapper utility that returns a test volume

        Args:
            client: Client object

        Returns:
            ID of the created volume
        """
        kwargs['size'] = CONF.volume.volume_size
        kwargs['name'] = data_utils.rand_name(
            VolumeV3RbacBaseTests.__name__ + '-Volume'
        )

        volume_id = client.create_volume(**kwargs)['volume']['id']
        self.cleanup(
            test_utils.call_and_ignore_notfound_exc, func=self.delete_resource,
            client=client, volume_id=volume_id
        )
        waiters.wait_for_volume_resource_status(
            client=client, resource_id=volume_id, status='available'
        )

        return volume_id

    @cleanup_order
    def create_snapshot(self, client, volume_id, cleanup=True, **kwargs):
        """Wrapper utility that returns a test snapshot.

        Args:
            client: Client object
            volume_id: ID of the volume
            cleanup: Boolean if should delete the snapshot

        Returns:
            ID of the created snapshot
        """
        kwargs['name'] = data_utils.rand_name(
            VolumeV3RbacBaseTests.__name__ + '-Snapshot'
        )

        snapshot_id = client.create_snapshot(
            volume_id=volume_id, **kwargs)['snapshot']['id']
        if cleanup:
            self.cleanup(
                test_utils.call_and_ignore_notfound_exc,
                func=self.delete_resource,
                client=client, snapshot_id=snapshot_id
            )
        waiters.wait_for_volume_resource_status(
            client=client, resource_id=snapshot_id, status='available'
        )

        return snapshot_id

    @classmethod
    def delete_resource(cls, client, **kwargs):
        """Delete a resource by a given client

        Args:
            client: Client object

        Keyword Args:
            snapshot_id: ID of a snapshot
            volume_id: ID of a volume
        """
        key, resource_id = list(kwargs.items())[0]
        resource_name = key.split('_')[0]

        del_action = getattr(client, f'delete_{resource_name}')
        test_utils.call_and_ignore_notfound_exc(del_action, resource_id)
        test_utils.call_and_ignore_notfound_exc(
            client.wait_for_resource_deletion, resource_id)

    @classmethod
    def create_backup(
            cls, volume_id, backup_client=None, add_cleanup=True, **kwargs
    ):
        """Wrapper utility that returns a test backup."""
        if backup_client is None:
            backup_client = cls.backups_client
        if 'name' not in kwargs:
            name = data_utils.rand_name(cls.__class__.__name__ + '-Backup')
            kwargs['name'] = name

        backup = backup_client.create_backup(
            volume_id=volume_id, **kwargs
        )['backup']
        if add_cleanup:
            cls.addClassResourceCleanup(
                test_utils.call_and_ignore_notfound_exc,
                cls.delete_resource,
                client=backup_client,
                backup_id=backup['id']
            )
        waiters.wait_for_volume_resource_status(
            backup_client, backup['id'], 'available'
        )
        return backup
