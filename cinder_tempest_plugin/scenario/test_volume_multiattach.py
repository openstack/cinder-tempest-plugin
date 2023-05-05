# Copyright 2022 Red Hat, Inc.
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
from tempest.lib import exceptions as lib_exc

from cinder_tempest_plugin.scenario import manager
from tempest.scenario import manager as tempest_manager

CONF = config.CONF


class VolumeMultiattachTests(manager.ScenarioTest,
                             tempest_manager.EncryptionScenarioTest):

    compute_min_microversion = '2.60'
    compute_max_microversion = 'latest'

    def setUp(self):
        super(VolumeMultiattachTests, self).setUp()
        self.validation_resources = self.get_test_validation_resources(
            self.os_primary)
        # NOTE(danms): If validation is enabled, we will have a keypair to use,
        # otherwise we need to create our own.
        if 'keypair' in self.validation_resources:
            self.keypair = self.validation_resources['keypair']
        else:
            self.keypair = self.create_keypair()
        self.security_group = self.create_security_group()

    @classmethod
    def skip_checks(cls):
        super(VolumeMultiattachTests, cls).skip_checks()
        if not CONF.compute_feature_enabled.volume_multiattach:
            raise cls.skipException('Volume multi-attach is not available.')

    def _verify_attachment(self, volume_id, server_id):
        volume = self.volumes_client.show_volume(volume_id)['volume']
        server_ids = (
            [attachment['server_id'] for attachment in volume['attachments']])
        self.assertIn(server_id, server_ids)

    @decorators.idempotent_id('e6604b85-5280-4f7e-90b5-186248fd3423')
    def test_multiattach_data_integrity(self):

        # Create an instance
        server_1 = self.create_server(
            key_name=self.keypair['name'],
            wait_until='SSHABLE',
            validatable=True,
            validation_resources=self.validation_resources,
            security_groups=[{'name': self.security_group['name']}])

        # Create multiattach type
        multiattach_vol_type = self.create_volume_type(
            extra_specs={'multiattach': "<is> True"})

        # Create a multiattach volume
        volume = self.create_volume(volume_type=multiattach_vol_type['id'])

        # Create encrypted volume
        encrypted_volume = self.create_encrypted_volume(
            'luks', volume_type='luks')

        # Create a normal volume
        simple_volume = self.create_volume()

        # Attach normal and encrypted volumes (These volumes are not used in
        # the current test but is used to emulate a real world scenario
        # where different types of volumes will be attached to the server)
        self.attach_volume(server_1, simple_volume)
        self.attach_volume(server_1, encrypted_volume)

        instance_ip = self.get_server_ip(server_1)

        # Attach volume to instance and find it's device name (eg: /dev/vdb)
        volume_device_name_inst_1, __ = (
            self._attach_and_get_volume_device_name(
                server_1, volume, instance_ip, self.keypair['private_key']))

        out_device = '/dev/' + volume_device_name_inst_1

        # This data is written from the first server and will be used to
        # verify when reading data from second server
        device_data_inst_1 = self.write_data_to_device(
            instance_ip, out_device, private_key=self.keypair['private_key'],
            server=server_1, sha_sum=True)

        # Create another instance
        server_2 = self.create_server(
            key_name=self.keypair['name'],
            validatable=True,
            validation_resources=self.validation_resources,
            wait_until='SSHABLE',
            security_groups=[{'name': self.security_group['name']}])

        instance_2_ip = self.get_server_ip(server_2)

        # Attach volume to instance and find it's device name (eg: /dev/vdc)
        volume_device_name_inst_2, __ = (
            self._attach_and_get_volume_device_name(
                server_2, volume, instance_2_ip, self.keypair['private_key']))

        in_device = '/dev/' + volume_device_name_inst_2

        # Read data from volume device
        device_data_inst_2 = self.read_data_from_device(
            instance_2_ip, in_device, private_key=self.keypair['private_key'],
            server=server_2, sha_sum=True)

        self._verify_attachment(volume['id'], server_1['id'])
        self._verify_attachment(volume['id'], server_2['id'])
        self.assertEqual(device_data_inst_1, device_data_inst_2)

    @decorators.idempotent_id('53514da8-f49c-4cda-8792-ff4a2fa69977')
    def test_volume_multiattach_same_host_negative(self):
        # Create an instance
        server = self.create_server(
            key_name=self.keypair['name'],
            validatable=True,
            validation_resources=self.validation_resources,
            wait_until='SSHABLE',
            security_groups=[{'name': self.security_group['name']}])

        # Create multiattach type
        multiattach_vol_type = self.create_volume_type(
            extra_specs={'multiattach': "<is> True"})

        # Create an empty volume
        volume = self.create_volume(volume_type=multiattach_vol_type['id'])

        # Attach volume to instance
        attachment = self.attach_volume(server, volume)

        self.assertEqual(server['id'], attachment['serverId'])

        # Try attaching the volume to the same instance
        self.assertRaises(lib_exc.BadRequest, self.attach_volume, server,
                          volume)
