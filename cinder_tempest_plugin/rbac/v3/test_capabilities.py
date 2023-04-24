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

from cinder_tempest_plugin.rbac.v3 import base as rbac_base
from tempest.lib import decorators
from tempest.lib import exceptions


class VolumeV3RbacCapabilityTests(rbac_base.VolumeV3RbacBaseTests):

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.volume_capabilities_client_latest
        # NOTE(lbragstad): This admin_client will be more useful later when
        # cinder supports system-scope and we need it for administrative
        # operations. For now, keep os_project_admin as the admin client until
        # we have system-scope.
        admin_client = cls.os_project_admin
        cls.admin_capabilities_client = (
            admin_client.volume_capabilities_client_latest)
        cls.admin_stats_client = (
            admin_client.volume_scheduler_stats_client_latest)

    def _get_capabilities(self, expected_status):
        pools = self.admin_stats_client.list_pools()['pools']
        host_name = pools[0]['name']
        self.do_request(
            'show_backend_capabilities',
            expected_status=expected_status,
            host=host_name
        )


class ProjectReaderTests(VolumeV3RbacCapabilityTests):
    credentials = ['project_reader', 'project_admin', 'system_admin']

    @decorators.idempotent_id('d16034fc-4204-4ea8-94b3-714de59fdfbf')
    def test_get_capabilities(self):
        self._get_capabilities(expected_status=exceptions.Forbidden)


class ProjectMemberTests(VolumeV3RbacCapabilityTests):
    credentials = ['project_member', 'project_admin', 'system_admin']

    @decorators.idempotent_id('dbaf51de-fafa-4f55-875f-7537524489ab')
    def test_get_capabilities(self):
        self._get_capabilities(expected_status=exceptions.Forbidden)


class ProjectAdminTests(VolumeV3RbacCapabilityTests):
    credentials = ['project_admin', 'system_admin']

    @decorators.idempotent_id('1fdbe493-e58f-48bf-bb38-52003eeef8cb')
    def test_get_capabilities(self):
        self._get_capabilities(expected_status=200)
