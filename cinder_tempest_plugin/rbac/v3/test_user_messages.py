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


class RbacV3UserMessagesTests(rbac_base.VolumeV3RbacBaseTests):
    min_microversion = '3.3'

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        admin_client = cls.os_project_admin
        cls.admin_messages_client = admin_client.volume_messages_client_latest
        cls.admin_volumes_client = admin_client.volumes_client_latest
        cls.admin_types_client = admin_client.volume_types_client_latest

    def create_user_message(self):
        """Trigger a 'no valid host' situation to generate a message."""
        bad_protocol = data_utils.rand_name('storage_protocol')
        bad_vendor = data_utils.rand_name('vendor_name')
        extra_specs = {'storage_protocol': bad_protocol,
                       'vendor_name': bad_vendor}
        vol_type_name = data_utils.rand_name(
            self.__class__.__name__ + '-volume-type'
        )
        bogus_type = self.admin_types_client.create_volume_type(
            name=vol_type_name, extra_specs=extra_specs
        )['volume_type']
        self.addCleanup(
            self.admin_types_client.delete_volume_type, bogus_type['id']
        )

        params = {
            'volume_type': bogus_type['id'], 'size': CONF.volume.volume_size
        }
        volume = self.admin_volumes_client.create_volume(**params)['volume']
        waiters.wait_for_volume_resource_status(
            self.admin_volumes_client, volume['id'], 'error'
        )
        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.admin_volumes_client.delete_volume,
            volume['id']
        )

        messages = self.admin_messages_client.list_messages()['messages']
        message_id = None
        for message in messages:
            if message['resource_uuid'] == volume['id']:
                message_id = message['id']
                break
        self.assertIsNotNone(
            message_id, f"No user message generated for volume {volume['id']}"
        )
        return message_id

    def _list_messages(self, expected_status):
        message_id = self.create_user_message()
        self.addCleanup(
            self.admin_messages_client.delete_message, message_id
        )
        self.do_request(
            method='list_messages', expected_status=expected_status
        )

    def _show_message(self, expected_status):
        message_id = self.create_user_message()
        self.addCleanup(self.admin_messages_client.delete_message, message_id)
        self.do_request(
            method='show_message', expected_status=expected_status,
            message_id=message_id
        )

    def _delete_message(self, expected_status):
        message_id = self.create_user_message()
        self.do_request(
            method='delete_message', expected_status=expected_status,
            message_id=message_id
        )
        if expected_status == exceptions.Forbidden:
            self.addCleanup(
                self.admin_messages_client.delete_message, message_id
            )
        else:
            self.client.wait_for_resource_deletion(id=message_id)


class ProjectReaderTests(RbacV3UserMessagesTests):
    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.volume_messages_client_latest

    @decorators.idempotent_id('1bef8bf9-6457-40f8-ada2-bc4d27602a07')
    def test_list_messages(self):
        self._list_messages(expected_status=200)

    @decorators.idempotent_id('689c53a9-6db9-44a8-9878-41d28899e0af')
    def test_show_message(self):
        self._show_message(expected_status=200)

    @decorators.skip_because(bug='2009818')
    @decorators.idempotent_id('c6e8744b-7749-425f-81b6-b1c3df6c7162')
    def test_delete_message(self):
        self._delete_message(expected_status=exceptions.Forbidden)


class ProjectMemberTests(RbacV3UserMessagesTests):
    credentials = ['project_member', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_member.volume_messages_client_latest

    @decorators.idempotent_id('fb470249-a482-49c6-84af-eda34891a714')
    def test_list_messages(self):
        self._list_messages(expected_status=200)

    @decorators.idempotent_id('43d248ef-008d-4aff-8c7f-37959a0fa195')
    def test_show_message(self):
        self._show_message(expected_status=200)

    @decorators.idempotent_id('a77cd089-cb74-4b44-abcb-06f1a6f80378')
    def test_delete_message(self):
        self._delete_message(expected_status=204)


class ProjectAdminTests(RbacV3UserMessagesTests):
    credentials = ['project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_admin.volume_messages_client_latest

    @decorators.idempotent_id('f3567efc-863c-4668-8fb1-6aa3f836451d')
    def test_list_messages(self):
        self._list_messages(expected_status=200)

    @decorators.idempotent_id('eecc7045-017b-492c-8594-2d40f5fda139')
    def test_show_message(self):
        self._show_message(expected_status=200)

    @decorators.idempotent_id('1f2db6f2-148f-44c2-97ef-dcff0fccd49a')
    def test_delete_message(self):
        self._delete_message(expected_status=204)
