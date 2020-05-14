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

from tempest.common import waiters
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions

from cinder_tempest_plugin.api.volume import base

CONF = config.CONF


class VolumesBackupsTest(base.BaseVolumeAdminTest):
    @classmethod
    def setup_clients(cls):
        super(VolumesBackupsTest, cls).setup_clients()
        cls.admin_volume_client = cls.os_admin.volumes_client_latest
        cls.backups_client = cls.os_primary.backups_client_latest
        cls.volumes_client = cls.os_primary.volumes_client_latest

    @classmethod
    def skip_checks(cls):
        super(VolumesBackupsTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.backup:
            raise cls.skipException("Cinder backup feature disabled")

    @decorators.idempotent_id('2daadb2e-409a-4ede-a6ce-6002ec324372')
    def test_backup_crossproject_admin_negative(self):

        # create vol as user
        volume = self.volumes_client.create_volume(
            size=CONF.volume.volume_size)['volume']
        waiters.wait_for_volume_resource_status(
            self.volumes_client,
            volume['id'], 'available')

        # create backup as user
        backup = self.backups_client.create_backup(
            volume_id=volume['id'])['backup']
        waiters.wait_for_volume_resource_status(
            self.backups_client,
            backup['id'], 'available')

        # try to create incremental backup as admin
        self.assertRaises(
            exceptions.BadRequest, self.admin_backups_client.create_backup,
            volume_id=volume['id'], incremental=True)

    @decorators.idempotent_id('b9feb593-5809-4207-90d3-28e627730f13')
    def test_backup_crossproject_user_negative(self):

        # create vol as user
        volume = self.volumes_client.create_volume(
            size=CONF.volume.volume_size)['volume']
        waiters.wait_for_volume_resource_status(
            self.volumes_client,
            volume['id'], 'available')

        # create backup as admin
        backup = self.admin_backups_client.create_backup(
            volume_id=volume['id'])['backup']
        waiters.wait_for_volume_resource_status(
            self.admin_backups_client,
            backup['id'], 'available')

        # try to create incremental backup as user
        self.assertRaises(
            exceptions.BadRequest, self.backups_client.create_backup,
            volume_id=volume['id'], incremental=True)

    @decorators.idempotent_id('ce15f528-bfc1-492d-81db-b6168b631587')
    def test_incremental_backup_respective_parents(self):

        # create vol as user
        volume = self.volumes_client.create_volume(
            size=CONF.volume.volume_size)['volume']
        waiters.wait_for_volume_resource_status(
            self.volumes_client,
            volume['id'], 'available')

        # create backup as admin
        backup_adm = self.admin_backups_client.create_backup(
            volume_id=volume['id'])['backup']
        waiters.wait_for_volume_resource_status(
            self.admin_backups_client,
            backup_adm['id'], 'available')

        # create backup as user
        backup_usr = self.backups_client.create_backup(
            volume_id=volume['id'])['backup']
        waiters.wait_for_volume_resource_status(
            self.backups_client,
            backup_usr['id'], 'available')

        # refresh admin backup and assert no child backups
        backup_adm = self.admin_backups_client.show_backup(
            backup_adm['id'])['backup']
        self.assertFalse(backup_adm['has_dependent_backups'])

        # create incremental backup as admin
        backup_adm_inc = self.admin_backups_client.create_backup(
            volume_id=volume['id'], incremental=True)['backup']
        waiters.wait_for_volume_resource_status(
            self.admin_backups_client,
            backup_adm_inc['id'], 'available')

        # refresh user backup and assert no child backups
        backup_usr = self.backups_client.show_backup(
            backup_usr['id'])['backup']
        self.assertFalse(backup_usr['has_dependent_backups'])

        # refresh admin backup and assert it has childs
        backup_adm = self.admin_backups_client.show_backup(
            backup_adm['id'])['backup']
        self.assertTrue(backup_adm['has_dependent_backups'])

        # create incremental backup as user
        backup_usr_inc = self.backups_client.create_backup(
            volume_id=volume['id'], incremental=True)['backup']
        waiters.wait_for_volume_resource_status(
            self.backups_client,
            backup_usr_inc['id'], 'available')

        # refresh user backup and assert it has childs
        backup_usr = self.backups_client.show_backup(
            backup_usr['id'])['backup']
        self.assertTrue(backup_usr['has_dependent_backups'])
