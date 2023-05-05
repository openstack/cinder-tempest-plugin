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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from tempest.scenario import manager

CONF = config.CONF


class TestEncryptedCinderVolumes(manager.EncryptionScenarioTest,
                                 manager.ScenarioTest):

    @classmethod
    def skip_checks(cls):
        super(TestEncryptedCinderVolumes, cls).skip_checks()
        if not CONF.compute_feature_enabled.attach_encrypted_volume:
            raise cls.skipException('Encrypted volume attach is not supported')

    @classmethod
    def resource_setup(cls):
        super(TestEncryptedCinderVolumes, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(TestEncryptedCinderVolumes, cls).resource_cleanup()

    def attach_detach_volume(self, server, volume):
        attached_volume = self.nova_volume_attach(server, volume)
        self.nova_volume_detach(server, attached_volume)

    def _delete_server(self, server):
        self.servers_client.delete_server(server['id'])
        waiters.wait_for_server_termination(self.servers_client, server['id'])

    def create_encrypted_volume_from_image(self, encryption_provider,
                                           volume_type='luks',
                                           key_size=256,
                                           cipher='aes-xts-plain64',
                                           control_location='front-end',
                                           **kwargs):
        """Create an encrypted volume from image.

        :param image_id: ID of the image to create volume from,
            CONF.compute.image_ref by default
        :param name: name of the volume,
            '$classname-volume-origin' by default
        :param **kwargs: additional parameters
        """
        volume_type = self.create_volume_type(name=volume_type)
        self.create_encryption_type(type_id=volume_type['id'],
                                    provider=encryption_provider,
                                    key_size=key_size,
                                    cipher=cipher,
                                    control_location=control_location)
        image_id = kwargs.pop('image_id', CONF.compute.image_ref)
        name = kwargs.pop('name', None)
        if not name:
            namestart = self.__class__.__name__ + '-volume-origin'
            name = data_utils.rand_name(namestart)
        return self.create_volume(volume_type=volume_type['name'],
                                  name=name, imageRef=image_id,
                                  **kwargs)

    @decorators.idempotent_id('5bb622ab-5060-48a8-8840-d589a548b9e4')
    @utils.services('volume')
    @utils.services('compute')
    def test_attach_cloned_encrypted_volume(self):

        """This test case attempts to reproduce the following steps:

        * Create an encrypted volume
        * Create clone from volume
        * Boot an instance and attach/dettach cloned volume

        """

        volume = self.create_encrypted_volume('luks', volume_type='luks')
        kwargs = {
            'display_name': data_utils.rand_name(self.__class__.__name__),
            'source_volid': volume['id'],
            'volume_type': volume['volume_type'],
            'size': volume['size']
        }
        volume_s = self.volumes_client.create_volume(**kwargs)['volume']
        self.addCleanup(self.volumes_client.wait_for_resource_deletion,
                        volume_s['id'])
        self.addCleanup(self.volumes_client.delete_volume, volume_s['id'])
        waiters.wait_for_volume_resource_status(
            self.volumes_client, volume_s['id'], 'available')
        volume_source = self.volumes_client.show_volume(
            volume_s['id'])['volume']
        validation_resources = self.get_test_validation_resources(
            self.os_primary)
        server = self.create_server(wait_until='SSHABLE',
                                    validatable=True,
                                    validation_resources=validation_resources)
        self.attach_detach_volume(server, volume_source)

    @decorators.idempotent_id('5bb622ab-5060-48a8-8840-d589a548b7e4')
    @utils.services('volume')
    @utils.services('compute')
    @utils.services('image')
    def test_boot_cloned_encrypted_volume(self):

        """This test case attempts to reproduce the following steps:

        * Create an encrypted volume from image
        * Boot an instance from the volume
        * Write data to the volume
        * Destroy the instance
        * Create a clone of the encrypted volume
        * Boot an instance from cloned volume
        * Verify the data
        """

        keypair = self.create_keypair()
        security_group = self.create_security_group()

        volume = self.create_encrypted_volume_from_image('luks')

        # create an instance from volume
        instance_1st = self.boot_instance_from_resource(
            source_id=volume['id'],
            source_type='volume',
            keypair=keypair,
            security_group=security_group)

        # write content to volume on instance
        ip_instance_1st = self.get_server_ip(instance_1st)
        timestamp = self.create_timestamp(ip_instance_1st,
                                          private_key=keypair['private_key'],
                                          server=instance_1st)
        # delete instance
        self._delete_server(instance_1st)

        # create clone
        kwargs = {
            'display_name': data_utils.rand_name(self.__class__.__name__),
            'source_volid': volume['id'],
            'volume_type': volume['volume_type'],
            'size': volume['size']
        }
        volume_s = self.volumes_client.create_volume(**kwargs)['volume']

        self.addCleanup(self.volumes_client.wait_for_resource_deletion,
                        volume_s['id'])
        self.addCleanup(self.volumes_client.delete_volume, volume_s['id'])
        waiters.wait_for_volume_resource_status(
            self.volumes_client, volume_s['id'], 'available')

        # create an instance from volume
        instance_2nd = self.boot_instance_from_resource(
            source_id=volume_s['id'],
            source_type='volume',
            keypair=keypair,
            security_group=security_group)

        # check the content of written file
        ip_instance_2nd = self.get_server_ip(instance_2nd)
        timestamp2 = self.get_timestamp(ip_instance_2nd,
                                        private_key=keypair['private_key'],
                                        server=instance_2nd)

        self.assertEqual(timestamp, timestamp2)

        # delete instance
        self._delete_server(instance_2nd)
