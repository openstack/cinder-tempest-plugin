# Copyright 2022 Red Hat, Inc.
# All rights reserved.
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

from tempest.common import utils
from tempest.common import waiters
from tempest import config
from tempest.lib import decorators
from tempest.scenario import manager

CONF = config.CONF


class TransferEncryptedVolumeTest(manager.EncryptionScenarioTest):

    volume_min_microversion = '3.70'
    volume_max_microversion = 'latest'

    credentials = ['primary', 'alt', 'admin']

    @classmethod
    def setup_clients(cls):
        super(TransferEncryptedVolumeTest, cls).setup_clients()

        # We need the "mv355" volume transfers client
        cls.client = cls.os_primary.volume_transfers_mv355_client_latest
        cls.alt_client = cls.os_alt.volume_transfers_mv355_client_latest
        cls.alt_volumes_client = cls.os_alt.volumes_client_latest

    @classmethod
    def skip_checks(cls):
        super(TransferEncryptedVolumeTest, cls).skip_checks()
        if not CONF.service_available.barbican:
            raise cls.skipException('Barbican is required')

    def setUp(self):
        super(TransferEncryptedVolumeTest, self).setUp()
        self.keypair = self.create_keypair()
        self.security_group = self.create_security_group()

    def _create_encrypted_volume_from_image(self):
        volume_type = self.create_volume_type()
        self.create_encryption_type(type_id=volume_type['id'],
                                    provider='luks',
                                    key_size=256,
                                    cipher='aes-xts-plain64',
                                    control_location='front-end')
        return self.create_volume_from_image(volume_type=volume_type['id'])

    def _create_or_get_timestamp(self, volume, timestamp_fn):
        server = self.boot_instance_from_resource(
            source_id=volume['id'],
            source_type='volume',
            keypair=self.keypair,
            security_group=self.security_group)
        server_ip = self.get_server_ip(server)
        timestamp = timestamp_fn(server_ip,
                                 private_key=self.keypair['private_key'],
                                 server=server)
        self.servers_client.delete_server(server['id'])
        waiters.wait_for_server_termination(self.servers_client, server['id'])
        return timestamp

    def _create_transfer(self, volume, transfer_client, volumes_client):
        body = transfer_client.create_volume_transfer(volume_id=volume['id'])
        transfer = body['transfer']
        waiters.wait_for_volume_resource_status(volumes_client,
                                                volume['id'],
                                                'awaiting-transfer')
        return transfer

    def _accept_transfer(self, transfer, transfer_client, volumes_client):
        _ = transfer_client.accept_volume_transfer(
            transfer['id'], auth_key=transfer['auth_key'])
        waiters.wait_for_volume_resource_status(volumes_client,
                                                transfer['volume_id'],
                                                'available')

    def _delete_transfer(self, transfer, transfer_client, volumes_client):
        _ = transfer_client.delete_volume_transfer(transfer['id'])
        waiters.wait_for_volume_resource_status(volumes_client,
                                                transfer['volume_id'],
                                                'available')

    @decorators.idempotent_id('a694dc4d-d11b-45cb-b268-62e76cc1b4f4')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_create_accept_volume_transfer(self):
        """Verify the ability to transfer an encrypted volume:

        * Create an encrypted volume from image
        * Boot an instance from the volume and write a timestamp
        * Transfer the volume to another project, then transfer it back
          again to the original project (see comments in the code for why
          this is done).
        * Boot annother instance from the volume and read the timestamp
        * Verify the timestamps match, and the volume has a new
          encryption_key_id.
        """

        # Create a bootable encrypted volume.
        volume = self._create_encrypted_volume_from_image()

        # Create an instance from the volume and write a timestamp.
        timestamp_1 = self._create_or_get_timestamp(volume,
                                                    self.create_timestamp)

        # Transfer the volume to another project.
        transfer = self._create_transfer(volume,
                                         self.client,
                                         self.volumes_client)
        self._accept_transfer(transfer,
                              self.alt_client,
                              self.alt_volumes_client)

        # Transfer the volume back to the original project. This is done
        # only because it's awkward in tempest to boot an instance and
        # access it (to read the timestamp) in another project without
        # setting up another security group and group rules.
        transfer = self._create_transfer(volume,
                                         self.alt_client,
                                         self.alt_volumes_client)
        self._accept_transfer(transfer, self.client, self.volumes_client)

        # Create another instance from the volume and read the timestamp.
        timestamp_2 = self._create_or_get_timestamp(volume,
                                                    self.get_timestamp)

        self.assertEqual(timestamp_1, timestamp_2)

        # Verify the volume has a new encryption_key_id.
        encryption_key_id_1 = volume['encryption_key_id']
        volume = self.volumes_client.show_volume(volume['id'])['volume']
        encryption_key_id_2 = volume['encryption_key_id']

        self.assertNotEqual(encryption_key_id_1, encryption_key_id_2)

    @decorators.idempotent_id('00c04d27-b3c6-454c-a0b4-223a195c4a89')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_create_delete_volume_transfer(self):
        """Verify the ability to cancel an encrypted volume transfer:

        * Create an encrypted volume from image
        * Boot an instance from the volume and write a timestamp
        * Create and delete a volume transfer
        * Boot annother instance from the volume and read the timestamp
        * Verify the timestamps match, and the volume has a new
          encryption_key_id.
        """

        # Create a bootable encrypted volume.
        volume = self._create_encrypted_volume_from_image()

        # Create an instance from the volume and write a timestamp.
        timestamp_1 = self._create_or_get_timestamp(volume,
                                                    self.create_timestamp)

        # Create and then delete a transfer of the volume
        transfer = self._create_transfer(volume,
                                         self.client,
                                         self.volumes_client)
        self._delete_transfer(transfer, self.client, self.volumes_client)

        # Create another instance from the volume and read the timestamp.
        timestamp_2 = self._create_or_get_timestamp(volume,
                                                    self.get_timestamp)

        self.assertEqual(timestamp_1, timestamp_2)

        # Verify the volume has a new encryption_key_id.
        encryption_key_id_1 = volume['encryption_key_id']
        volume = self.volumes_client.show_volume(volume['id'])['volume']
        encryption_key_id_2 = volume['encryption_key_id']

        self.assertNotEqual(encryption_key_id_1, encryption_key_id_2)
