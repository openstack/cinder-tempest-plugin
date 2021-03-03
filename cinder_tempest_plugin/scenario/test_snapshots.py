# Copyright 2020 Red Hat, Inc.
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

from tempest.common import utils
from tempest.lib import decorators

from cinder_tempest_plugin.scenario import manager


class SnapshotDataIntegrityTests(manager.ScenarioTest):

    def setUp(self):
        super(SnapshotDataIntegrityTests, self).setUp()
        self.keypair = self.create_keypair()
        self.security_group = self._create_security_group()

    def _get_file_md5(self, ip_address, filename, mount_path='/mnt',
                      private_key=None, server=None):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)

        md5_sum = ssh_client.exec_command(
            'sudo md5sum %s/%s|cut -c 1-32' % (mount_path, filename))
        return md5_sum

    def _count_files(self, ip_address, mount_path='/mnt', private_key=None,
                     server=None):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)
        count = ssh_client.exec_command('sudo ls -l %s | wc -l' % mount_path)
        return int(count) - 1

    def _launch_instance_from_snapshot(self, snap):
        volume_snap = self.create_volume(snapshot_id=snap['id'],
                                         size=snap['size'])

        server_snap = self.boot_instance_from_resource(
            source_id=volume_snap['id'],
            source_type='volume',
            keypair=self.keypair,
            security_group=self.security_group)

        return server_snap

    def create_md5_new_file(self, ip_address, filename, mount_path='/mnt',
                            private_key=None, server=None):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)

        ssh_client.exec_command(
            'sudo dd bs=1024 count=100 if=/dev/urandom of=/%s/%s' %
            (mount_path, filename))
        md5 = ssh_client.exec_command(
            'sudo md5sum -b %s/%s|cut -c 1-32' % (mount_path, filename))
        ssh_client.exec_command('sudo sync')
        return md5

    def get_md5_from_file(self, instance, filename):

        instance_ip = self.get_server_ip(instance)

        md5_sum = self._get_file_md5(instance_ip, filename=filename,
                                     private_key=self.keypair['private_key'],
                                     server=instance)
        count = self._count_files(instance_ip,
                                  private_key=self.keypair['private_key'],
                                  server=instance)
        return count, md5_sum

    @decorators.idempotent_id('ff10644e-5a70-4a9f-9801-8204bb81fb61')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_snapshot_data_integrity(self):
        """This test checks the data integrity after creating and restoring

        snapshots. The procedure is as follows:

        1) create a volume from image
        2) Boot an instance from the volume
        3) create file on vm and write data into it
        4) create snapshot
        5) repeat 3 and 4 two more times (simply creating 3 snapshots)

        Now restore the snapshots one by one into volume, create instances
        from it and check the number of files and file content at each
        point when snapshot was created.
        """

        # Create a volume from image
        volume = self.create_volume_from_image()

        # create an instance from bootable volume
        server = self.boot_instance_from_resource(
            source_id=volume['id'],
            source_type='volume',
            keypair=self.keypair,
            security_group=self.security_group)

        instance_ip = self.get_server_ip(server)

        # Write data to volume
        file1_md5 = self.create_md5_new_file(
            instance_ip, filename="file1",
            private_key=self.keypair['private_key'],
            server=instance_ip)

        # Create first snapshot
        snapshot1 = self.create_volume_snapshot(volume['id'], force=True)

        # Write data to volume
        file2_md5 = self.create_md5_new_file(
            instance_ip, filename="file2",
            private_key=self.keypair['private_key'],
            server=instance_ip)

        # Create second snapshot
        snapshot2 = self.create_volume_snapshot(volume['id'], force=True)

        # Write data to volume
        file3_md5 = self.create_md5_new_file(
            instance_ip, filename="file3",
            private_key=self.keypair['private_key'],
            server=instance_ip)

        # Create third snapshot
        snapshot3 = self.create_volume_snapshot(volume['id'], force=True)

        # Create volume, instance and check file and contents for snap1
        instance_1 = self._launch_instance_from_snapshot(snapshot1)
        count_snap_1, md5_file_1 = self.get_md5_from_file(instance_1,
                                                          'file1')

        self.assertEqual(count_snap_1, 1)
        self.assertEqual(file1_md5, md5_file_1)

        # Create volume, instance and check file and contents for snap2
        instance_2 = self._launch_instance_from_snapshot(snapshot2)
        count_snap_2, md5_file_2 = self.get_md5_from_file(instance_2,
                                                          'file2')

        self.assertEqual(count_snap_2, 2)
        self.assertEqual(file2_md5, md5_file_2)

        # Create volume, instance and check file and contents for snap3
        instance_3 = self._launch_instance_from_snapshot(snapshot3)
        count_snap_3, md5_file_3 = self.get_md5_from_file(instance_3,
                                                          'file3')

        self.assertEqual(count_snap_3, 3)
        self.assertEqual(file3_md5, md5_file_3)
