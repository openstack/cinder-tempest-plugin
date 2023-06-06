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

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions

from cinder_tempest_plugin.rbac.v3 import base as rbac_base


class RbacV3VolumeTypesTests(rbac_base.VolumeV3RbacBaseTests):

    min_microversion = '3.3'
    extra_spec_key = 'key1'
    encryption_type_key_cipher = 'cipher'
    create_kwargs = {
        'provider': 'LuksEncryptor',
        'key_size': 256,
        encryption_type_key_cipher: 'aes-xts-plain64',
        'control_location': 'front-end'
    }

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        admin_client = cls.os_project_admin
        cls.admin_volumes_client = admin_client.volumes_client_latest
        cls.admin_types_client = admin_client.volume_types_client_latest
        cls.admin_encryption_types_client = \
            admin_client.encryption_types_client_latest

    @classmethod
    def resource_setup(cls):
        """Create a new volume-type for the test"""
        super(RbacV3VolumeTypesTests, cls).resource_setup()
        # create a volume type
        cls.volume_type = cls.create_volume_type()

    @classmethod
    def create_volume_type(
            cls, name=None, with_encryption=True, cleanup=True
    ):
        # create a volume type
        if not name:
            name = data_utils.rand_name("volume-type")
        extra_specs = {cls.extra_spec_key: 'value1'}
        params = {'name': name,
                  'description': "description",
                  'extra_specs': extra_specs,
                  'os-volume-type-access:is_public': True}
        volume_type = cls.admin_types_client.create_volume_type(
            **params
        )['volume_type']

        if with_encryption:
            # Create encryption_type
            cls.encryption_type = \
                cls.admin_encryption_types_client.create_encryption_type(
                    volume_type['id'], **cls.create_kwargs)['encryption']

        if cleanup:
            cls.addClassResourceCleanup(
                cls.admin_types_client.delete_volume_type, volume_type['id']
            )

        return volume_type

    def _update_volume_type(self, expected_status):
        """Update volume type"""
        self.do_request(
            method='update_volume_type',
            expected_status=expected_status,
            volume_type_id=self.volume_type['id'],
            description='Updated volume type description'
        )

    def _create_or_update_extra_specs_for_volume_type(self, expected_status):
        """Create or update extra specs"""
        volume_type = self.create_volume_type(with_encryption=False)
        # Create extra spec 'key2' with value 'value2'
        extra_spec = {'key2': 'value2'}
        self.do_request(
            method='create_volume_type_extra_specs',
            expected_status=expected_status,
            volume_type_id=volume_type['id'],
            extra_specs=extra_spec
        )

        # Update extra spec 'key2' with value 'updated value'
        extra_spec = {'key2': 'updated value'}
        self.do_request(
            method='update_volume_type_extra_specs',
            expected_status=expected_status,
            volume_type_id=volume_type['id'],
            extra_spec_name='key2',
            extra_specs=extra_spec
        )

    def _list_all_extra_specs_for_volume_type(self, expected_status):
        """List all extra_specs for a volume type"""
        extra_specs = self.do_request(
            method='list_volume_types_extra_specs',
            expected_status=expected_status,
            volume_type_id=self.volume_type['id']
        )['extra_specs']
        self.assertIn(
            self.extra_spec_key,
            list(extra_specs.keys()),
            message=f"Key '{self.extra_spec_key}' not found in extra_specs."
        )

    def _show_extra_spec_for_volume_type(self, expected_status):
        """Show extra_spec for a volume type"""
        self.do_request(
            method='show_volume_type_extra_specs',
            expected_status=expected_status,
            volume_type_id=self.volume_type['id'],
            extra_specs_name=self.extra_spec_key
        )

    def _update_extra_spec_for_volume_type(self, expected_status):
        """Update extra_spec for a volume type"""
        spec_name = self.extra_spec_key
        extra_spec = {spec_name: 'updated value'}
        self.do_request(
            method='update_volume_type_extra_specs',
            expected_status=expected_status,
            volume_type_id=self.volume_type['id'],
            extra_spec_name=spec_name,
            extra_specs=extra_spec
        )

    def _delete_extra_spec_for_volume_type(self, expected_status):
        """Delete a volume type extra_spec"""
        volume_type = self.create_volume_type(with_encryption=False)

        self.do_request(
            method='delete_volume_type_extra_specs',
            expected_status=expected_status,
            volume_type_id=volume_type['id'],
            extra_spec_name=self.extra_spec_key
        )

    def _show_volume_type_detail(self, expected_status):
        """Show volume type"""
        self.do_request(
            method='show_volume_type',
            expected_status=expected_status,
            volume_type_id=self.volume_type['id']
        )

    def _show_default_volume_type(self, expected_status):
        """Show default volume type"""
        self.do_request(
            method='show_default_volume_type',
            expected_status=expected_status
        )

    def _delete_volume_type(self, expected_status):
        """Delete a volume type"""
        cleanup = True if expected_status == exceptions.Forbidden\
            else False
        volume_type = self.create_volume_type(
            with_encryption=False, cleanup=cleanup
        )

        self.do_request(
            method='delete_volume_type',
            expected_status=expected_status,
            volume_type_id=volume_type['id']
        )

    def _list_volume_types(self, expected_status):
        """List all volume types"""
        self.do_request(
            method='list_volume_types',
            expected_status=expected_status
        )

    def _create_volume_type(self, expected_status):
        """Create a volume type"""
        volume_type = self.do_request(
            method='create_volume_type',
            expected_status=expected_status,
            name="test-new-volume-type"
        )
        if expected_status != exceptions.Forbidden:
            volume_type = volume_type['volume_type']
            self.admin_types_client.delete_volume_type(
                volume_type_id=volume_type['id']
            )

    def _show_encryption_type(self, expected_status):
        """Show volume type's encryption type"""
        self.do_request(
            method='show_encryption_type',
            expected_status=expected_status,
            client=self.encryption_types_client,
            volume_type_id=self.volume_type['id']
        )

    def _show_encryption_spec_item(self, expected_status):
        """Show encryption spec item"""
        self.do_request(
            method='show_encryption_specs_item',
            expected_status=expected_status,
            client=self.encryption_types_client,
            volume_type_id=self.volume_type['id'],
            key=self.encryption_type_key_cipher
        )

    def _delete_encryption_type(self, expected_status):
        """Delete encryption type"""
        volume_type = self.create_volume_type(with_encryption=True)

        self.do_request(
            method='delete_encryption_type',
            expected_status=expected_status,
            client=self.encryption_types_client,
            volume_type_id=volume_type['id']
        )

    def _create_encryption_type(self, expected_status):
        """Create encryption type"""
        volume_type = self.create_volume_type(with_encryption=False)

        self.do_request(
            method='create_encryption_type',
            expected_status=expected_status,
            client=self.encryption_types_client,
            volume_type_id=volume_type['id'],
            **self.create_kwargs
        )

    def _update_encryption_type(self, expected_status):
        """Update encryption type"""
        update_kwargs = {'key_size': 128}

        self.do_request(
            method='update_encryption_type',
            expected_status=expected_status,
            client=self.encryption_types_client,
            volume_type_id=self.volume_type['id'],
            **update_kwargs
        )


class VolumeTypesReaderTests(RbacV3VolumeTypesTests):
    """Test Volume types using 'reader' user"""
    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.volume_types_client_latest
        cls.encryption_types_client = \
            cls.os_project_reader.encryption_types_client_latest

    @decorators.idempotent_id('e3fdabf0-fd8c-4bab-9870-5a67fe25c6e4')
    def test_update_volume_type(self):
        self._update_volume_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('b046a4d7-79a0-436b-9075-863e2299b73d')
    def test_create_or_update_extra_specs_for_volume_type(self):
        self._create_or_update_extra_specs_for_volume_type(
            expected_status=exceptions.Forbidden
        )

    @decorators.skip_because(bug='2018467')
    @decorators.idempotent_id('9499752c-3b27-41a3-8f55-4bdba7297f92')
    def test_list_all_extra_specs_for_volume_type(self):
        self._list_all_extra_specs_for_volume_type(
            expected_status=200
        )

    @decorators.skip_because(bug='2018467')
    @decorators.idempotent_id('a38f7248-3a5b-4e51-8e32-d2dcf9c771ea')
    def test_show_extra_spec_for_volume_type(self):
        self._show_extra_spec_for_volume_type(expected_status=200)

    @decorators.idempotent_id('68689644-22a8-4ba6-a642-db4258681586')
    def test_update_extra_spec_for_volume_type(self):
        self._update_extra_spec_for_volume_type(
            expected_status=exceptions.Forbidden
        )

    @decorators.idempotent_id('a7cdd9ae-f389-48f6-b144-abf336b1637b')
    def test_delete_extra_spec_for_volume_type(self):
        self._delete_extra_spec_for_volume_type(
            expected_status=exceptions.Forbidden
        )

    @decorators.skip_because(bug='2016402')
    @decorators.idempotent_id('7ea28fc2-ce5a-48c9-8d03-31c2826fe566')
    def test_show_volume_type_detail(self):
        self._show_volume_type_detail(expected_status=200)

    @decorators.skip_because(bug='2016402')
    @decorators.idempotent_id('aceab52a-c503-4081-936e-b9df1c31046d')
    def test_show_default_volume_type(self):
        self._show_default_volume_type(expected_status=200)

    @decorators.idempotent_id('35581811-6288-4698-aaaf-7f5a4fe662e8')
    def test_delete_volume_type(self):
        self._delete_volume_type(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug='2016402')
    @decorators.idempotent_id('e8a438f9-e9c1-4f3f-8ae3-ad80ee02cd6a')
    def test_list_volume_types(self):
        self._list_volume_types(expected_status=200)

    @decorators.idempotent_id('3c3a39b1-fff5-492b-8c1c-9520063901ef')
    def test_create_volume_type(self):
        self._create_volume_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('84bd20f1-621c-416d-add2-fbae57137239')
    def test_show_encryption_type(self):
        self._show_encryption_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('ab9c7149-fab7-4584-b4ff-8b997cd62e75')
    def test_show_encryption_spec_item(self):
        self._show_encryption_spec_item(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('8d85ec39-bc32-4f49-88e6-63adc7e1f832')
    def test_delete_encryption_type(self):
        self._delete_encryption_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('c7c0892e-08d1-45e0-8ebf-be949cb4ab02')
    def test_create_encryption_type(self):
        self._create_encryption_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('8186d5bc-183a-4fcc-9c6a-e2b247a0caee')
    def test_update_encryption_type(self):
        self._update_encryption_type(expected_status=exceptions.Forbidden)


class VolumeTypesMemberTests(RbacV3VolumeTypesTests):
    """Test Volume types using 'member' user"""
    credentials = ['project_member', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_member.volume_types_client_latest
        cls.encryption_types_client = \
            cls.os_project_member.encryption_types_client_latest

    @decorators.idempotent_id('e5e642bf-2f31-4d04-ad43-6ad75562b7e4')
    def test_update_volume_type(self):
        self._update_volume_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('fda21e7e-9292-49b8-9754-f3c25b8e5f57')
    def test_create_or_update_extra_specs_for_volume_type(self):
        self._create_or_update_extra_specs_for_volume_type(
            expected_status=exceptions.Forbidden
        )

    @decorators.skip_because(bug='2018467')
    @decorators.idempotent_id('82fd0d34-17b3-4f45-bd2e-728c9a8bff8c')
    def test_list_all_extra_specs_for_volume_type(self):
        self._list_all_extra_specs_for_volume_type(
            expected_status=200
        )

    @decorators.skip_because(bug='2018467')
    @decorators.idempotent_id('67aa0b40-7c0a-4ae7-8682-fb4f20abd390')
    def test_show_extra_spec_for_volume_type(self):
        self._show_extra_spec_for_volume_type(expected_status=200)

    @decorators.idempotent_id('65470a71-254d-4152-bdaa-6b7f43e9c74f')
    def test_update_extra_spec_for_volume_type(self):
        self._update_extra_spec_for_volume_type(
            expected_status=exceptions.Forbidden
        )

    @decorators.idempotent_id('3695be33-bd22-4090-8252-9c42eb7eeef6')
    def test_delete_extra_spec_for_volume_type(self):
        self._delete_extra_spec_for_volume_type(
            expected_status=exceptions.Forbidden
        )

    @decorators.idempotent_id('319f3ca1-bdd7-433c-9bed-03c7b093e7a2')
    def test_show_volume_type_detail(self):
        self._show_volume_type_detail(expected_status=200)

    @decorators.skip_because(bug='2016402')
    @decorators.idempotent_id('2e990c61-a2ea-4a01-a2dc-1f483c934e8d')
    def test_show_default_volume_type(self):
        self._show_default_volume_type(expected_status=200)

    @decorators.idempotent_id('6847c211-647b-4d02-910c-773e76b99fcd')
    def test_delete_volume_type(self):
        self._delete_volume_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('308f80c9-6342-45a1-8e6e-9e400b510013')
    def test_list_volume_types(self):
        self._list_volume_types(expected_status=200)

    @decorators.idempotent_id('81cebbb8-fa0d-4bd8-a433-e43c7b187456')
    def test_create_volume_type(self):
        self._create_volume_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('7c84b013-c5a8-434f-8ea7-23c5b2d46d5e')
    def test_show_encryption_type(self):
        self._show_encryption_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('387974ce-3544-48e3-81c0-3f86a5b60b93')
    def test_show_encryption_spec_item(self):
        self._show_encryption_spec_item(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('c0163522-524f-4dfb-a3d4-6648f58ce99c')
    def test_delete_encryption_type(self):
        self._delete_encryption_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('65d86181-905a-4aa6-a9e5-672415d819a0')
    def test_create_encryption_type(self):
        self._create_encryption_type(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('2633f1d3-e648-4d12-86b9-e7f72b41ec68')
    def test_update_encryption_type(self):
        self._update_encryption_type(expected_status=exceptions.Forbidden)


class VolumeTypesAdminTests(RbacV3VolumeTypesTests):
    """Test Volume types using 'admin' user"""
    credentials = ['project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_admin.volume_types_client_latest
        cls.encryption_types_client = \
            cls.os_project_admin.encryption_types_client_latest

    @decorators.idempotent_id('77d065ef-ffdd-4749-b326-d64fbf5d0432')
    def test_update_volume_type(self):
        self._update_volume_type(expected_status=200)

    @decorators.idempotent_id('422271a7-0128-4fd6-9f60-aeb4a1ce16ea')
    def test_create_or_update_extra_specs_for_volume_type(self):
        self._create_or_update_extra_specs_for_volume_type(
            expected_status=200
        )

    @decorators.idempotent_id('5c491d13-df15-4721-812e-2ed473b86a12')
    def test_list_all_extra_specs_for_volume_type(self):
        self._list_all_extra_specs_for_volume_type(
            expected_status=200
        )

    @decorators.skip_because(bug='2018467')
    @decorators.idempotent_id('a2cca7b6-0af9-47e5-b8c1-4e0f01822d4e')
    def test_show_extra_spec_for_volume_type(self):
        self._show_extra_spec_for_volume_type(expected_status=200)

    @decorators.idempotent_id('d0ff17d3-2c47-485f-b2f1-d53ec32c32e2')
    def test_update_extra_spec_for_volume_type(self):
        self._update_extra_spec_for_volume_type(
            expected_status=200
        )

    @decorators.idempotent_id('4661cc2f-8727-4998-a427-8cb1d512b68a')
    def test_delete_extra_spec_for_volume_type(self):
        self._delete_extra_spec_for_volume_type(
            expected_status=202
        )

    @decorators.idempotent_id('7f794e33-b5cf-4172-b39e-a56cd9c18a2e')
    def test_show_volume_type_detail(self):
        self._show_volume_type_detail(expected_status=200)

    @decorators.skip_because(bug='2016402')
    @decorators.idempotent_id('93886ad8-5cd0-4def-8b0e-40418e55050d')
    def test_show_default_volume_type(self):
        self._show_default_volume_type(expected_status=200)

    @decorators.idempotent_id('7486259d-5c40-4fb3-8a95-491c45a0a872')
    def test_delete_volume_type(self):
        self._delete_volume_type(expected_status=202)

    @decorators.idempotent_id('e075e8ff-bb05-4c84-b2ab-0205ef3e8dbd')
    def test_list_volume_types(self):
        self._list_volume_types(expected_status=200)

    @decorators.idempotent_id('57384db2-9408-4a31-8c15-022eea5f9b76')
    def test_create_volume_type(self):
        self._create_volume_type(expected_status=200)

    @decorators.idempotent_id('46fc49a3-f76f-4c22-ac83-8d1665437810')
    def test_show_encryption_type(self):
        self._show_encryption_type(expected_status=200)

    @decorators.idempotent_id('4ff57649-bfe1-48f4-aaac-4577affba8d7')
    def test_show_encryption_spec_item(self):
        self._show_encryption_spec_item(expected_status=200)

    @decorators.idempotent_id('e622af7d-a412-4903-9256-256d8e3cc560')
    def test_delete_encryption_type(self):
        self._delete_encryption_type(expected_status=202)

    @decorators.idempotent_id('e7c4e925-6ce6-439b-8be8-6df4cbc32cdc')
    def test_create_encryption_type(self):
        self._create_encryption_type(expected_status=200)

    @decorators.idempotent_id('90beb71d-93fa-4252-8566-192bdd517715')
    def test_update_encryption_type(self):
        self._update_encryption_type(expected_status=200)
