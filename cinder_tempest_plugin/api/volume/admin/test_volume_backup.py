# Copyright (C) 2020 Canonical Ltd.
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

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions

from cinder_tempest_plugin.api.volume import base

CONF = config.CONF


class VolumesBackupsTest(base.BaseVolumeAdminTest):
    @classmethod
    def skip_checks(cls):
        super(VolumesBackupsTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.backup:
            raise cls.skipException("Cinder backup feature disabled")

    @decorators.idempotent_id('2daadb2e-409a-4ede-a6ce-6002ec324372')
    def test_backup_crossproject_admin_negative(self):

        # create vol as user
        volume = self.create_volume(size=CONF.volume.volume_size)

        # create backup as user
        self.create_backup(volume_id=volume['id'])
        # try to create incremental backup as admin
        self.assertRaises(
            exceptions.BadRequest, self.admin_backups_client.create_backup,
            volume_id=volume['id'], incremental=True)

    @decorators.idempotent_id('b9feb593-5809-4207-90d3-28e627730f13')
    def test_backup_crossproject_user_negative(self):

        # create vol as user
        volume = self.create_volume(size=CONF.volume.volume_size)

        # create backup as admin

        self.create_backup(volume_id=volume['id'],
                           backup_client=self.admin_backups_client)

        # try to create incremental backup as user
        self.assertRaises(
            exceptions.BadRequest, self.backups_client.create_backup,
            volume_id=volume['id'], incremental=True)

    @decorators.idempotent_id('ce15f528-bfc1-492d-81db-b6168b631587')
    def test_incremental_backup_respective_parents(self):

        # create vol as user
        volume = self.create_volume(size=CONF.volume.volume_size)

        # create backup as admin
        backup_adm = self.create_backup(
            volume_id=volume['id'], backup_client=self.admin_backups_client)

        # create backup as user
        backup_usr = self.create_backup(volume_id=volume['id'])

        # refresh admin backup and assert no child backups
        backup_adm = self.admin_backups_client.show_backup(
            backup_adm['id'])['backup']
        self.assertFalse(backup_adm['has_dependent_backups'])

        # create incremental backup as admin
        self.create_backup(volume_id=volume['id'], incremental=True,
                           backup_client=self.admin_backups_client)

        # refresh user backup and assert no child backups
        backup_usr = self.backups_client.show_backup(
            backup_usr['id'])['backup']
        self.assertFalse(backup_usr['has_dependent_backups'])

        # refresh admin backup and assert it has childs
        backup_adm = self.admin_backups_client.show_backup(
            backup_adm['id'])['backup']
        self.assertTrue(backup_adm['has_dependent_backups'])

        # create incremental backup as user
        self.create_backup(volume_id=volume['id'],
                           incremental=True)

        # refresh user backup and assert it has childs
        backup_usr = self.backups_client.show_backup(
            backup_usr['id'])['backup']
        self.assertTrue(backup_usr['has_dependent_backups'])
