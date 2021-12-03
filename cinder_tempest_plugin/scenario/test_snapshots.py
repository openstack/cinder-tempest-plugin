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
from tempest import config
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from cinder_tempest_plugin.scenario import manager

CONF = config.CONF


class SnapshotDataIntegrityTests(manager.ScenarioTest):

    def setUp(self):
        super(SnapshotDataIntegrityTests, self).setUp()
        self.keypair = self.create_keypair()
        self.security_group = self._create_security_group()

    def _attached_volume_name(
            self, disks_list_before_attach, ip_address, private_key):
        ssh = self.get_remote_client(ip_address, private_key=private_key)

        def _wait_for_volume_available_on_system():
            disks_list_after_attach = ssh.list_disks()
            return len(disks_list_after_attach) > len(disks_list_before_attach)

        if not test_utils.call_until_true(_wait_for_volume_available_on_system,
                                          CONF.compute.build_timeout,
                                          CONF.compute.build_interval):
            raise lib_exc.TimeoutException

        disks_list_after_attach = ssh.list_disks()
        volume_name = [item for item in disks_list_after_attach
                       if item not in disks_list_before_attach][0]
        return volume_name

    def _get_file_md5(self, ip_address, filename, dev_name=None,
                      mount_path='/mnt', private_key=None, server=None):

        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)
        if dev_name is not None:
            ssh_client.exec_command('sudo mount /dev/%s %s' % (dev_name,
                                                               mount_path))

        md5_sum = ssh_client.exec_command(
            'sudo md5sum %s/%s|cut -c 1-32' % (mount_path, filename))
        if dev_name is not None:
            ssh_client.exec_command('sudo umount %s' % mount_path)
        return md5_sum

    def _count_files(self, ip_address, dev_name=None, mount_path='/mnt',
                     private_key=None, server=None):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)
        if dev_name is not None:
            ssh_client.exec_command('sudo mount /dev/%s %s' % (dev_name,
                                                               mount_path))
        count = ssh_client.exec_command('sudo ls -l %s | wc -l' % mount_path)
        if dev_name is not None:
            ssh_client.exec_command('sudo umount %s' % mount_path)
        # We subtract 2 from the count since `wc -l` also includes the count
        # of new line character and while creating the filesystem, a
        # lost+found folder is also created
        return int(count) - 2

    def _make_fs(self, ip_address, private_key, server, dev_name, fs='ext4'):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)

        ssh_client.make_fs(dev_name, fs=fs)

    def create_md5_new_file(self, ip_address, filename, dev_name=None,
                            mount_path='/mnt', private_key=None, server=None):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)

        if dev_name is not None:
            ssh_client.exec_command('sudo mount /dev/%s %s' % (dev_name,
                                                               mount_path))
        ssh_client.exec_command(
            'sudo dd bs=1024 count=100 if=/dev/urandom of=/%s/%s' %
            (mount_path, filename))
        md5 = ssh_client.exec_command(
            'sudo md5sum -b %s/%s|cut -c 1-32' % (mount_path, filename))
        ssh_client.exec_command('sudo sync')
        if dev_name is not None:
            ssh_client.exec_command('sudo umount %s' % mount_path)
        return md5

    def get_md5_from_file(self, instance, instance_ip, filename,
                          dev_name=None):

        md5_sum = self._get_file_md5(instance_ip, filename=filename,
                                     dev_name=dev_name,
                                     private_key=self.keypair['private_key'],
                                     server=instance)
        count = self._count_files(instance_ip, dev_name=dev_name,
                                  private_key=self.keypair['private_key'],
                                  server=instance)
        return count, md5_sum

    def _attach_and_get_volume_device_name(self, server, volume, instance_ip,
                                           private_key):
        ssh_client = self.get_remote_client(
            instance_ip, private_key=private_key,
            server=server)
        # List disks before volume attachment
        disks_list_before_attach = ssh_client.list_disks()
        # Attach volume
        volume = self.nova_volume_attach(server, volume)
        # Find the difference between disks before and after attachment that
        # gives us the volume device name
        volume_device_name = self._attached_volume_name(
            disks_list_before_attach, instance_ip, private_key)
        return volume_device_name

    @decorators.idempotent_id('ff10644e-5a70-4a9f-9801-8204bb81fb61')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_snapshot_data_integrity(self):
        """This test checks the data integrity after creating and restoring

        snapshots. The procedure is as follows:

        1) Create an instance with ephemeral disk
        2) Create a volume, attach it to the instance and create a filesystem
           on it and mount it
        3) Mount the volume, create a file and write data into it, Unmount it
        4) create snapshot
        5) repeat 3 and 4 two more times (simply creating 3 snapshots)

        Now create volume from the snapshots one by one, attach it to the
        instance and check the number of files and file content at each
        point when snapshot was created.
        """

        # Create an instance
        server = self.create_server(
            key_name=self.keypair['name'],
            security_groups=[{'name': self.security_group['name']}])

        # Create an empty volume
        volume = self.create_volume()

        instance_ip = self.get_server_ip(server)

        # Attach volume to instance and find it's device name (eg: /dev/vdb)
        volume_device_name = self._attach_and_get_volume_device_name(
            server, volume, instance_ip, self.keypair['private_key'])

        # Create filesystem on the volume
        self._make_fs(instance_ip, self.keypair['private_key'], server,
                      volume_device_name)

        # Write data to volume
        file1_md5 = self.create_md5_new_file(
            instance_ip, dev_name=volume_device_name, filename="file1",
            private_key=self.keypair['private_key'],
            server=instance_ip)

        # Create first snapshot
        snapshot1 = self.create_volume_snapshot(volume['id'], force=True)

        # Write data to volume
        file2_md5 = self.create_md5_new_file(
            instance_ip, dev_name=volume_device_name, filename="file2",
            private_key=self.keypair['private_key'],
            server=instance_ip)

        # Create second snapshot
        snapshot2 = self.create_volume_snapshot(volume['id'], force=True)

        # Write data to volume
        file3_md5 = self.create_md5_new_file(
            instance_ip, dev_name=volume_device_name, filename="file3",
            private_key=self.keypair['private_key'],
            server=instance_ip)

        # Create third snapshot
        snapshot3 = self.create_volume_snapshot(volume['id'], force=True)

        # Detach the volume
        self.nova_volume_detach(server, volume)

        # Create volume from snapshot, attach it to instance and check file
        # and contents for snap1
        volume_snap_1 = self.create_volume(snapshot_id=snapshot1['id'])
        volume_device_name = self._attach_and_get_volume_device_name(
            server, volume_snap_1, instance_ip, self.keypair['private_key'])
        count_snap_1, md5_file_1 = self.get_md5_from_file(
            server, instance_ip, 'file1', dev_name=volume_device_name)
        # Detach the volume
        self.nova_volume_detach(server, volume_snap_1)

        self.assertEqual(count_snap_1, 1)
        self.assertEqual(file1_md5, md5_file_1)

        # Create volume from snapshot, attach it to instance and check file
        # and contents for snap2
        volume_snap_2 = self.create_volume(snapshot_id=snapshot2['id'])
        volume_device_name = self._attach_and_get_volume_device_name(
            server, volume_snap_2, instance_ip, self.keypair['private_key'])
        count_snap_2, md5_file_2 = self.get_md5_from_file(
            server, instance_ip, 'file2', dev_name=volume_device_name)
        # Detach the volume
        self.nova_volume_detach(server, volume_snap_2)

        self.assertEqual(count_snap_2, 2)
        self.assertEqual(file2_md5, md5_file_2)

        # Create volume from snapshot, attach it to instance and check file
        # and contents for snap3
        volume_snap_3 = self.create_volume(snapshot_id=snapshot3['id'])
        volume_device_name = self._attach_and_get_volume_device_name(
            server, volume_snap_3, instance_ip, self.keypair['private_key'])
        count_snap_3, md5_file_3 = self.get_md5_from_file(
            server, instance_ip, 'file3', dev_name=volume_device_name)
        # Detach the volume
        self.nova_volume_detach(server, volume_snap_3)

        self.assertEqual(count_snap_3, 3)
        self.assertEqual(file3_md5, md5_file_3)
