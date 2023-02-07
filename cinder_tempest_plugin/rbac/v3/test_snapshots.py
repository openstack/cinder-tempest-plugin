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
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators
from tempest.lib import exceptions

from cinder_tempest_plugin.rbac.v3 import base as rbac_base

CONF = config.CONF


class VolumeV3RbacSnapshotsTests(rbac_base.VolumeV3RbacBaseTests):

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.vol_other_client = cls.os_project_admin.volumes_client_latest
        cls.snap_other_client = cls.os_project_admin.snapshots_client_latest

    def _list_snapshots(self, expected_status):
        """Test list_snapshots operation

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )
        self.do_request(
            expected_status=expected_status, method='list_snapshots'
        )

    def _show_snapshot(self, expected_status):
        """Test show_snapshot operation

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )
        self.do_request(
            expected_status=expected_status, method='show_snapshot',
            snapshot_id=snapshot_id
        )

    def _create_snapshot(self, expected_status):
        """Test create_snapshot operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snap_name = data_utils.rand_name(
            self.__name__ + '-Snapshot'
        )
        if expected_status == 202:
            snapshot_id = self.do_request(
                method='create_snapshot', expected_status=202,
                volume_id=volume_id, name=snap_name
            )['snapshot']['id']
            self.addCleanup(
                test_utils.call_and_ignore_notfound_exc, self.delete_resource,
                client=self.client, snapshot_id=snapshot_id
            )
            waiters.wait_for_volume_resource_status(
                client=self.client, resource_id=snapshot_id, status='available'
            )
        elif expected_status == exceptions.Forbidden:
            self.do_request(
                method='create_snapshot', expected_status=expected_status,
                volume_id=volume_id, name=snap_name
            )

    def _remove_snapshot(self, expected_status):
        """Test create_snapshot operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )

        self.do_request(
            method='delete_snapshot', snapshot_id=snapshot_id,
            expected_status=expected_status
        )
        if expected_status == 202:
            self.client.wait_for_resource_deletion(id=snapshot_id)

    def _reset_snapshot_status(self, expected_status):
        """Test reset_snapshot_status operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )
        self.do_request(
            'reset_snapshot_status', expected_status=expected_status,
            snapshot_id=snapshot_id, status='error'
        )

    def _update_snapshot(self, expected_status):
        """Test update_snapshot operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )
        new_desc = self.__name__ + '-update_test'
        self.do_request(
            method='update_snapshot', expected_status=expected_status,
            snapshot_id=snapshot_id, description=new_desc
        )

    def _update_snapshot_status(self, expected_status):
        """Test update_snapshot_status operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )

        reset_status = 'creating' if expected_status == 202 else 'error'
        request_status = 'error' if expected_status == 202 else 'creating'
        self.os_project_admin.snapshots_client_latest.reset_snapshot_status(
            snapshot_id=snapshot_id, status=reset_status
        )
        waiters.wait_for_volume_resource_status(
            client=self.os_project_admin.snapshots_client_latest,
            resource_id=snapshot_id, status=reset_status
        )

        self.do_request(
            'update_snapshot_status', expected_status=expected_status,
            snapshot_id=snapshot_id, status=request_status, progress='80%'
        )

    def _force_delete_snapshot(self, expected_status):
        """Test force_delete_snapshot operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )
        self.do_request(
            method='force_delete_snapshot', snapshot_id=snapshot_id,
            expected_status=expected_status
        )
        if expected_status != exceptions.Forbidden:
            self.client.wait_for_resource_deletion(id=snapshot_id)
            waiters.wait_for_volume_resource_status(
                client=self.os_project_admin.volumes_client_latest,
                resource_id=volume_id, status='available'
            )

    def _unmanage_snapshot(self, expected_status):
        """Test unmanage_snapshot operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client, volume_id=volume_id
        )
        self.do_request(
            method='unmanage_snapshot',
            expected_status=expected_status, snapshot_id=snapshot_id
        )
        if expected_status != exceptions.Forbidden:
            self.client.wait_for_resource_deletion(id=snapshot_id)

    def _manage_snapshot(self, client, expected_status):
        """Test reset_snapshot_status operation.

        Args:
            client: The client to perform the needed request
            expected_status: The expected HTTP response code
        """
        # Create a volume
        volume_id = self.create_volume(client=self.vol_other_client)

        # Create a snapshot
        snapshot_id = self.create_snapshot(
            client=self.snap_other_client,
            volume_id=volume_id,
            cleanup=False
        )
        # Unmanage the snapshot
        # Unmanage snapshot function works almost the same as delete snapshot,
        # but it does not delete the snapshot data
        self.snap_other_client.unmanage_snapshot(snapshot_id)
        self.client.wait_for_resource_deletion(snapshot_id)

        # Verify the original snapshot does not exist in snapshot list
        params = {'all_tenants': 1}
        all_snapshots = self.snap_other_client.list_snapshots(
            detail=True, **params)['snapshots']
        self.assertNotIn(snapshot_id, [v['id'] for v in all_snapshots])

        # Manage the snapshot
        name = data_utils.rand_name(
            self.__class__.__name__ + '-Managed-Snapshot'
        )
        description = data_utils.rand_name(
            self.__class__.__name__ + '-Managed-Snapshot-Description'
        )
        metadata = {"manage-snap-meta1": "value1",
                    "manage-snap-meta2": "value2",
                    "manage-snap-meta3": "value3"}
        snapshot_ref = {
            'volume_id': volume_id,
            'ref': {CONF.volume.manage_snapshot_ref[0]:
                    CONF.volume.manage_snapshot_ref[1] % snapshot_id},
            'name': name,
            'description': description,
            'metadata': metadata
        }

        new_snapshot = self.do_request(
            client=client,
            method='manage_snapshot', expected_status=expected_status,
            volume_id=volume_id, ref=snapshot_ref
        )
        if expected_status != exceptions.Forbidden:
            snapshot = new_snapshot['snapshot']
            waiters.wait_for_volume_resource_status(
                client=self.snap_other_client,
                resource_id=snapshot['id'],
                status='available'
            )
            self.delete_resource(
                client=self.snap_other_client, snapshot_id=snapshot['id']
            )


class ProjectReaderTests(VolumeV3RbacSnapshotsTests):

    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.snapshots_client_latest

    @decorators.idempotent_id('dd8e19dc-c8fd-443c-8aed-cdffe07fa6be')
    def test_list_snapshots(self):
        self._list_snapshots(expected_status=200)

    @decorators.idempotent_id('6f69e8ed-4e11-40a1-9620-258cf3c45872')
    def test_show_snapshot(self):
        self._show_snapshot(expected_status=200)

    @decorators.skip_because(bug="2017108")
    @decorators.idempotent_id('13ae344f-fa01-44cc-b9f1-d04452940dc1')
    def test_create_snapshot(self):
        self._create_snapshot(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2017108")
    @decorators.idempotent_id('5b58f647-da0f-4d2a-bf68-680fc692efb4')
    def test_delete_snapshot(self):
        self._remove_snapshot(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('809d8c8c-25bf-4f1f-9b77-1a81ce4292d1')
    def test_reset_snapshot_status(self):
        self._reset_snapshot_status(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2017108")
    @decorators.idempotent_id('c46f5df8-9a6f-4ed6-b94c-3b65ef05ee9e')
    def test_update_snapshot(self):
        self._update_snapshot(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2017108")
    @decorators.idempotent_id('c90f98d7-3665-4c9f-820f-3f4c2adfdbf5')
    def test_update_snapshot_status(self):
        self._update_snapshot_status(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('63aa8184-897d-4e00-9b80-d2e7828f1b13')
    def test_force_delete_snapshot(self):
        self._force_delete_snapshot(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('35495666-b663-4c68-ba44-0695e30a6838')
    def test_unmanage_snapshot(self):
        self._unmanage_snapshot(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('d2d1326d-fb47-4448-a1e1-2d1219d30fd5')
    def test_manage_snapshot(self):
        self._manage_snapshot(
            expected_status=exceptions.Forbidden,
            client=self.os_project_reader.snapshot_manage_client_latest
        )


class ProjectMemberTests(VolumeV3RbacSnapshotsTests):

    credentials = ['project_member', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_member.snapshots_client_latest

    @decorators.idempotent_id('5b3ec87f-443f-42f7-bd3c-ab05ea30c5e1')
    def test_list_snapshots(self):
        self._list_snapshots(expected_status=200)

    @decorators.idempotent_id('6fee8967-951c-4957-b51b-97b83c13c7c3')
    def test_show_snapshot(self):
        self._show_snapshot(expected_status=200)

    @decorators.idempotent_id('43f77b31-aab4-46d0-b76f-e17000d23589')
    def test_create_snapshot(self):
        self._create_snapshot(expected_status=202)

    @decorators.idempotent_id('22939122-8b4e-47d5-abaa-774bc55c07fc')
    def test_delete_snapshot(self):
        self._remove_snapshot(expected_status=202)

    @decorators.idempotent_id('da391afd-8baa-458b-b222-f6ab42ab47c3')
    def test_reset_snapshot_status(self):
        self._reset_snapshot_status(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('a774bdca-bfbe-477d-9711-5fb64d7e34ea')
    def test_update_snapshot(self):
        self._update_snapshot(expected_status=200)

    @decorators.idempotent_id('12e00e1b-bf84-41c1-8a1e-8625d1317789')
    def test_update_snapshot_status(self):
        self._update_snapshot_status(expected_status=202)

    @decorators.idempotent_id('e7cb3eb0-d607-4c90-995d-df82d030eca8')
    def test_force_delete_snapshot(self):
        self._force_delete_snapshot(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('dd7da3da-68ef-42f5-af1d-29803a4a04fd')
    def test_unmanage_snapshot(self):
        self._unmanage_snapshot(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('c2501d05-9bca-42d7-9ab5-c0d9133e762f')
    def test_manage_snapshot(self):
        self._manage_snapshot(
            expected_status=exceptions.Forbidden,
            client=self.os_project_member.snapshot_manage_client_latest
        )
