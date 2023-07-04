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

from oslo_serialization import base64
from oslo_serialization import jsonutils as json

from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions

from cinder_tempest_plugin.rbac.v3 import base as rbac_base

CONF = config.CONF


class RbacV3BackupsTests(rbac_base.VolumeV3RbacBaseTests):
    @classmethod
    def skip_checks(cls):
        super(RbacV3BackupsTests, cls).skip_checks()
        if not CONF.volume_feature_enabled.backup:
            raise cls.skipException("Cinder backup feature disabled")

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        admin_client = cls.os_project_admin
        cls.admin_backups_client = admin_client.backups_client_latest
        cls.admin_volumes_client = admin_client.volumes_client_latest

    @classmethod
    def resource_setup(cls):
        super(RbacV3BackupsTests, cls).resource_setup()
        cls.volume_id = cls.create_volume(client=cls.admin_volumes_client)
        backup = cls.create_backup(
            volume_id=cls.volume_id, backup_client=cls.admin_backups_client
        )
        cls.backup_id = backup['id']
        cls.backup_name = backup['name']


class RbacV3BackupsTests33(RbacV3BackupsTests):
    """Test API with microversion greater than 3.3"""
    min_microversion = '3.3'

    def _encode_backup(self, backup):
        retval = json.dumps(backup)
        return base64.encode_as_text(retval)

    def _decode_url(self, backup_url):
        return json.loads(base64.decode_as_text(backup_url))

    def _modify_backup_url(self, backup_url, changes):
        backup = self._decode_url(backup_url)
        backup.update(changes)
        return self._encode_backup(backup)

    def _list_backups(self, expected_status):
        """List all backups"""
        backups = self.do_request(
            method='list_backups', expected_status=expected_status
        )['backups']
        backup_list = [
            b['id'] for b in backups if b['name'] == self.backup_name
        ]

        self.assertNotEmpty(
            backup_list, f"Backup {self.backup_name} not found"
        )

    def _list_project_backups(self, expected_status):
        """List all backups for a project"""
        backups = self.do_request(
            method='list_backups',
            expected_status=expected_status,
            project_id=self.client.project_id
        )['backups']
        backup_list = [
            b['id'] for b in backups if b['name'] == self.backup_name
        ]

        self.assertNotEmpty(
            backup_list, f"Backup {self.backup_name} not found"
        )

    def _show_backup(self, expected_status):
        """Show backup details"""
        backup = self.do_request(
            method='show_backup',
            expected_status=expected_status,
            backup_id=self.backup_id
        )['backup']
        self.assertNotEmpty(backup, f"Backup {self.backup_name} not found")

    def _delete_backup(self, expected_status):
        """Delete a backup"""
        add_cleanup = True if expected_status == exceptions.Forbidden\
            else False
        volume_id = self.create_volume(client=self.admin_volumes_client)
        backup = self.create_backup(
            volume_id=volume_id,
            backup_client=self.admin_backups_client,
            add_cleanup=add_cleanup
        )

        self.do_request(
            method='delete_backup',
            expected_status=expected_status,
            backup_id=backup['id']
        )

    def _restore_backup(self, expected_status):
        """Restore a backup"""
        res = self.do_request(
            method='restore_backup',
            expected_status=expected_status,
            backup_id=self.backup_id,
            name='new-backup-vol'
        )
        if expected_status != exceptions.Forbidden:
            waiters.wait_for_volume_resource_status(
                self.admin_backups_client,
                self.backup_id, 'available'
            )
            self.delete_resource(
                client=self.admin_volumes_client,
                volume_id=res['restore']['volume_id']
            )

    def _create_backup(self, expected_status):
        """Create a backup"""
        res = self.do_request(
            method='create_backup',
            expected_status=expected_status,
            volume_id=self.volume_id
        )
        if expected_status != exceptions.Forbidden:
            backup = res['backup']
            waiters.wait_for_volume_resource_status(
                self.admin_backups_client, backup['id'], 'available'
            )
            self.admin_backups_client.delete_backup(backup_id=backup['id'])

    def _export_backup(self, expected_status):
        """Export a backup"""
        self.do_request(
            method='export_backup',
            expected_status=expected_status,
            backup_id=self.backup_id
        )

    def _import_backup(self, expected_status):
        """Import a backup"""
        volume_id = self.create_volume(client=self.admin_volumes_client)
        backup = self.create_backup(
            volume_id=volume_id,
            backup_client=self.admin_backups_client
        )

        export_backup = (
            self.admin_backups_client.export_backup(
                backup['id']
            )['backup-record']
        )
        waiters.wait_for_volume_resource_status(
            self.admin_backups_client, backup['id'], 'available'
        )
        self.assertTrue(
            export_backup['backup_service'].startswith('cinder.backup.drivers')
        )
        # NOTE(ybenshim): Backups are imported with the same backup id
        # (important for incremental backups among other things), so we cannot
        # import the exported backup information as it is, because that Backup
        # ID already exists.  So we'll fake the data by changing the backup id
        # in the exported backup DB info we have retrieved before importing it
        # back.

        new_id = data_utils.rand_uuid()
        new_url = self._modify_backup_url(
            export_backup['backup_url'], {'id': new_id})

        res = self.do_request(
            method='import_backup',
            expected_status=expected_status,
            backup_service=export_backup['backup_service'],
            backup_url=new_url
        )
        if expected_status != exceptions.Forbidden:
            new_backup = res['backup']
            waiters.wait_for_volume_resource_status(
                self.client, new_backup['id'], 'available'
            )
            self.delete_resource(
                client=self.admin_backups_client,
                backup_id=new_backup['id']
            )

    def _reset_backup_status(self, expected_status):
        """Reset a backup status"""
        new_status = 'error'
        volume_id = self.create_volume(client=self.admin_volumes_client)
        backup = self.create_backup(
            volume_id=volume_id,
            backup_client=self.admin_backups_client
        )

        self.do_request(
            method='reset_backup_status',
            expected_status=expected_status,
            backup_id=backup['id'],
            status=new_status
        )


class ProjectReaderTests33(RbacV3BackupsTests33):
    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.backups_client_latest

    @decorators.idempotent_id('9dd02d4b-d6f8-45ca-a95e-534dbd586aab')
    def test_list_backups(self):
        """List all backups"""
        self._list_backups(expected_status=200)

    @decorators.idempotent_id('9ba2e970-c08b-4c1c-b912-2f3b1373ae6e')
    def test_list_project_backups(self):
        """List all backups for a project"""
        self._list_project_backups(expected_status=200)

    @decorators.idempotent_id('e88f8971-2892-4a54-80bb-dd21b18f19e9')
    def test_show_backup(self):
        """Show backup details"""
        self._show_backup(expected_status=200)

    @decorators.skip_because(bug='2017110')
    @decorators.idempotent_id('a9ab3279-aa5e-4ad8-b740-b80a7769d3f9')
    def test_delete_backup(self):
        """Delete a backup"""
        self._delete_backup(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug='2017110')
    @decorators.idempotent_id('0566fa4a-4e03-4cca-822f-d5a4922da2ab')
    def test_restore_backup(self):
        """Restore a backup"""
        self._restore_backup(expected_status=exceptions.Forbidden)

    @decorators.skip_because(bug='2017110')
    @decorators.idempotent_id('bad2514e-18c0-4fa0-9e35-221182ee24cf')
    def test_create_backup(self):
        """Create a backup"""
        self._create_backup(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('ab74b8cc-5005-49b4-94f4-994567171b07')
    def test_export_backup(self):
        """Export a backup"""
        self._export_backup(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('caaa5756-261a-4d9c-bfc2-788719630a06')
    def test_import_backup(self):
        """Import a backup"""
        self._import_backup(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('c832ff77-8f22-499f-a7a3-0834972a1507')
    def test_reset_backup_status(self):
        """Reset a backup status"""
        self._reset_backup_status(expected_status=exceptions.Forbidden)


class ProjectMemberTests33(RbacV3BackupsTests33):
    credentials = ['project_member', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_member.backups_client_latest

    @decorators.idempotent_id('5a23c53c-924b-47f6-a5d1-ab6327391c12')
    def test_list_backups(self):
        """List all backups"""
        self._list_backups(expected_status=200)

    @decorators.idempotent_id('c737bd7b-293c-4d8f-ada9-3b00f7e1adce')
    def test_list_project_backups(self):
        """List all backups for a project"""
        self._list_project_backups(expected_status=200)

    @decorators.idempotent_id('9944bb15-02fa-4321-97a4-ef8cb5b5fec2')
    def test_show_backup(self):
        """Show backup details"""
        self._show_backup(expected_status=200)

    @decorators.idempotent_id('c98dfea8-b9f2-4a84-947b-1d857c707789')
    def test_delete_backup(self):
        """Delete a backup"""
        self._delete_backup(expected_status=202)

    @decorators.idempotent_id('7a6fd066-00e7-4140-866c-8195fbd71e87')
    def test_restore_backup(self):
        """Restore a backup"""
        self._restore_backup(expected_status=202)

    @decorators.idempotent_id('44644140-4d05-4725-9a4b-6d1a71eda9b7')
    def test_create_backup(self):
        """Create a backup"""
        self._create_backup(expected_status=202)

    @decorators.idempotent_id('71c7cfaf-7809-4872-b1b2-3feb90b939d4')
    def test_export_backup(self):
        """Export a backup"""
        self._export_backup(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('f1c03c1b-2b48-4be0-8b6a-81df8a75f78c')
    def test_import_backup(self):
        """Import a backup"""
        self._import_backup(expected_status=exceptions.Forbidden)

    @decorators.idempotent_id('307f6fe9-81ed-444a-9aae-99a571d24bf5')
    def test_reset_backup_status(self):
        """Reset a backup status"""
        self._reset_backup_status(expected_status=exceptions.Forbidden)


class ProjectAdminTests33(RbacV3BackupsTests33):
    credentials = ['project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_admin.backups_client_latest

    @decorators.idempotent_id('81c579bc-db98-4773-9590-b742d0b00b89')
    def test_list_backups(self):
        """List all backups"""
        self._list_backups(expected_status=200)

    @decorators.idempotent_id('602dd42d-10df-4eb2-9664-3c9c44e3b35e')
    def test_list_project_backups(self):
        """List all backups for a project"""
        self._list_project_backups(expected_status=200)

    @decorators.idempotent_id('2094dcee-9585-4745-b045-a0f8c79fbe52')
    def test_show_backup(self):
        """Show backup details"""
        self._show_backup(expected_status=200)

    @decorators.idempotent_id('b77a8d69-1d12-480d-a83e-5f712d7c2b74')
    def test_delete_backup(self):
        """Delete a backup"""
        self._delete_backup(expected_status=202)

    @decorators.idempotent_id('7221d2df-338c-4932-be40-ad7166c03db1')
    def test_restore_backup(self):
        """Restore a backup"""
        self._restore_backup(expected_status=202)

    @decorators.idempotent_id('d347fa21-a5bf-4ce5-ab6b-246c3a06a735')
    def test_create_backup(self):
        """Create a backup"""
        self._create_backup(expected_status=202)

    @decorators.idempotent_id('e179a062-47d5-4fa8-b359-dedab2afddd8')
    def test_export_backup(self):
        """Export a backup"""
        self._export_backup(expected_status=200)

    @decorators.idempotent_id('1be80834-2463-49fb-a763-906e8c672fd5')
    def test_import_backup(self):
        """Import a backup"""
        self._import_backup(expected_status=201)

    @decorators.idempotent_id('88db5943-0053-489a-af30-12b139a38a0b')
    def test_reset_backup_status(self):
        """Reset a backup status"""
        self._reset_backup_status(expected_status=202)


class RbacV3BackupsTests39(RbacV3BackupsTests):
    """Test API with microversion greater than 3.3"""
    min_microversion = '3.9'

    def _update_backup(self, expected_status):
        """Update a backup"""
        new_description = "Updated backup description"
        update_kwargs = {"description": new_description}
        self.do_request(
            method='update_backup',
            expected_status=expected_status,
            backup_id=self.backup_id,
            **update_kwargs
        )
        if expected_status != exceptions.Forbidden:
            backup = self.admin_backups_client.show_backup(
                backup_id=self.backup_id
            )['backup']
            self.assertEqual(
                backup['description'], new_description,
                f"Backup {backup['name']} description should be "
                f"{new_description}"
            )


class ProjectReaderTests39(RbacV3BackupsTests39):
    credentials = ['project_reader', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_reader.backups_client_latest

    @decorators.idempotent_id('50ccc892-6ed0-4015-b181-9f64ffa45f33')
    @decorators.skip_because(bug='2017110')
    def test_update_backup(self):
        """Update a backup"""
        self._update_backup(expected_status=exceptions.Forbidden)


class ProjectMemberTests39(RbacV3BackupsTests39):
    credentials = ['project_member', 'project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_member.backups_client_latest

    @decorators.idempotent_id('a1cdd6f2-e9bc-4f6a-a0e6-2493ac6f9f27')
    def test_update_backup(self):
        """Update a backup"""
        self._update_backup(expected_status=200)


class ProjectAdminTests39(RbacV3BackupsTests39):
    credentials = ['project_admin']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_project_admin.backups_client_latest

    @decorators.idempotent_id('2686eecf-e3cd-4f23-8771-aa040ed9be4b')
    def test_update_backup(self):
        """Update a backup"""
        self._update_backup(expected_status=200)
