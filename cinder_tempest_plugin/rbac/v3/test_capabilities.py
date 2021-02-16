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

import abc

from tempest.lib import exceptions

from cinder_tempest_plugin.api.volume import base
from cinder_tempest_plugin.rbac.v3 import base as rbac_base


class VolumeV3RbacCapabilityTests(rbac_base.VolumeV3RbacBaseTests,
                                  metaclass=abc.ABCMeta):

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

    @classmethod
    def setup_credentials(cls):
        super().setup_credentials()
        cls.os_primary = getattr(cls, 'os_%s' % cls.credentials[0])

    @abc.abstractmethod
    def test_get_capabilities(self):
        """Test volume_extension:capabilities policy.

        This test must check:
          * whether the persona can fetch capabilities for a host.

        """
        pass


class ProjectAdminTests(VolumeV3RbacCapabilityTests, base.BaseVolumeTest):

    credentials = ['project_admin', 'system_admin']

    def test_get_capabilities(self):
        pools = self.admin_stats_client.list_pools()['pools']
        host_name = pools[0]['name']
        self.do_request('show_backend_capabilities', expected_status=200,
                        host=host_name)


class ProjectMemberTests(ProjectAdminTests, base.BaseVolumeTest):

    credentials = ['project_member', 'project_admin', 'system_admin']

    def test_get_capabilities(self):
        pools = self.admin_stats_client.list_pools()['pools']
        host_name = pools[0]['name']
        self.do_request('show_backend_capabilities',
                        expected_status=exceptions.Forbidden,
                        host=host_name)


class ProjectReaderTests(ProjectMemberTests, base.BaseVolumeTest):

    credentials = ['project_reader', 'project_admin', 'system_admin']
