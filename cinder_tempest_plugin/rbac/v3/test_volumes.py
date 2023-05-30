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
from tempest.lib import exceptions

from cinder_tempest_plugin.rbac.v3 import base as rbac_base

CONF = config.CONF


class VolumeV3RbacVolumesTests(rbac_base.VolumeV3RbacBaseTests):

    min_microversion = '3.12'

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.vol_other_client = cls.os_project_admin.volumes_client_latest

    def _create_volume(self, expected_status, **kwargs):
        """Test create_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        kwargs['size'] = CONF.volume.volume_size
        self.do_request(
            method='create_volume', expected_status=expected_status, **kwargs
        )

    def _show_volume(self, expected_status):
        """Test show_volume operation

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='show_volume', volume_id=volume_id,
            expected_status=expected_status
        )

    def _list_volumes(self, expected_status):
        """Test list_volumes operation

        Args:
            expected_status: The expected HTTP response code
        """
        self.create_volume(client=self.vol_other_client)
        self.do_request(method='list_volumes', expected_status=expected_status)

    def _list_volumes_detail(self, expected_status):
        """Test list_volumes details operation

        Args:
            expected_status: The expected HTTP response code
        """
        self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='list_volumes', detail=True, expected_status=expected_status
        )

    def _show_volume_summary(self, expected_status):
        """Test show_volume_summary operation

        Args:
            expected_status: The expected HTTP response code
        """
        self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='show_volume_summary', expected_status=expected_status
        )

    def _update_volume(self, expected_status):
        """Test update_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        new_desc = self.__name__ + '-update_test'
        self.do_request(
            method='update_volume', volume_id=volume_id, description=new_desc,
            expected_status=expected_status
        )

    def _set_bootable_volume(self, expected_status):
        """Test set_bootable_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='set_bootable_volume', volume_id=volume_id,
            bootable=True, expected_status=expected_status
        )

    def _delete_volume(self, expected_status):
        """Test delete_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='delete_volume', volume_id=volume_id,
            expected_status=expected_status
        )


class ProjectReaderTests(VolumeV3RbacVolumesTests):

    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.volumes_client_latest

    @decorators.skip_because(bug="2020113")
    @decorators.idempotent_id('3d87f960-6210-45f5-b70b-679d67a4e17e')
    def test_create_volume(self):
        self._create_volume(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('9b2667f2-744e-4d1f-8c39-17060010f19f')
    def test_show_volume(self):
        self._show_volume(expected_status=200)

    @decorators.idempotent_id('2f4da8f9-cdc5-4a6e-9143-8237634a629c')
    def test_list_volumes(self):
        self._list_volumes(expected_status=200)

    @decorators.idempotent_id('b11e59cd-d1dd-43e4-9676-22ab394f5d18')
    def test_list_volumes_detail(self):
        self._list_volumes_detail(expected_status=200)

    @decorators.idempotent_id('ef347930-54dc-432f-b742-0a060fc37ae8')
    def test_show_volume_summary(self):
        self._show_volume_summary(expected_status=200)

    @decorators.skip_because(bug="2020113")
    @decorators.idempotent_id('cda92972-7213-4fa0-bc14-ab012dc95931')
    def test_update_volume(self):
        self._update_volume(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2020113")
    @decorators.idempotent_id('9970b57d-8d5d-460e-931b-28a112df81e0')
    def test_set_bootable_volume(self):
        self._set_bootable_volume(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2020113")
    @decorators.idempotent_id('4fd4dce8-ed8a-4f05-8aac-da99858b563d')
    def test_delete_volume(self):
        self._delete_volume(expected_status=exceptions.Forbidden)
