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


class VolumeV3RbacVolumeActionsTests(rbac_base.VolumeV3RbacBaseTests):

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.vol_other_client = cls.os_project_admin.volumes_client_latest

    def _extend_volume(self, expected_status):
        """Test extend_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='extend_volume', volume_id=volume_id,
            new_size=2, expected_status=expected_status
        )

    def _reset_volume_status(self, expected_status):
        """Test reset_volume_status operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='reset_volume_status', volume_id=volume_id,
            status='error', expected_status=expected_status
        )

    def _retype_volume(self, expected_status):
        """Test retype_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='retype_volume', volume_id=volume_id,
            new_type='dedup-tier-replication', expected_status=expected_status
        )

    def _update_volume_readonly(self, expected_status):
        """Test update_volume_readonly operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='update_volume_readonly', volume_id=volume_id,
            readonly=True, expected_status=expected_status
        )

    def _force_delete_volume(self, expected_status):
        """Test force_delete_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='force_delete_volume', volume_id=volume_id,
            expected_status=expected_status
        )

    def _reserve_volume(self, expected_status):
        """Test reserve_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='reserve_volume', volume_id=volume_id,
            expected_status=expected_status
        )

    def _unreserve_volume(self, expected_status):
        """Test unreserve_volume operation.

        Args:
            expected_status: The expected HTTP response code
        """
        volume_id = self.create_volume(client=self.vol_other_client)
        self.do_request(
            method='unreserve_volume', volume_id=volume_id,
            expected_status=expected_status
        )


class ProjectReaderTests(VolumeV3RbacVolumeActionsTests):

    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.volumes_client_latest

    @decorators.skip_because(bug="2020261")
    @decorators.idempotent_id('4d721c58-2f6f-4857-8f4f-0664d5f7bf49')
    def test_extend_volume(self):
        self._extend_volume(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('434b454a-5cbe-492d-a416-70b8ff41f636')
    def test_reset_volume_status(self):
        self._reset_volume_status(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2020261")
    @decorators.idempotent_id('4675295a-7c72-4b04-8a43-03d7c88ab6bf')
    def test_retype_volume(self):
        self._retype_volume(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2020261")
    @decorators.idempotent_id('3beecd52-e314-40d8-875d-a0e7db8dd88f')
    def test_update_volume_readonly(self):
        self._update_volume_readonly(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('b025ff12-73a4-4f15-af55-876cd43cade3')
    def test_force_delete_volume(self):
        self._force_delete_volume(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2020261")
    @decorators.idempotent_id('d2c13bf9-267a-4a71-be5c-391f22e9b433')
    def test_reserve_volume(self):
        self._reserve_volume(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug="2020261")
    @decorators.idempotent_id('725d85cf-96b2-4338-98f4-2f468099c4ed')
    def test_unreserve_volume(self):
        self._unreserve_volume(expected_status=exceptions.Forbidden)
