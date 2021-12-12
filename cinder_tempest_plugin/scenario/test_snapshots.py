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
        self.security_group = self.create_security_group()

    @decorators.idempotent_id('ff10644e-5a70-4a9f-9801-8204bb81fb61')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_snapshot_data_integrity(self):
        """This test checks the data integrity after creating and restoring

        snapshots. The procedure is as follows:

        1) Create an instance with ephemeral disk
        2) Create a volume, attach it to the instance and create a filesystem
           on it and mount it
        3) Create a file and write data into it, Unmount it
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
        volume_device_name, __ = self._attach_and_get_volume_device_name(
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

        snap_map = {1: snapshot1, 2: snapshot2, 3: snapshot3}
        file_map = {1: file1_md5, 2: file2_md5, 3: file3_md5}

        # Loop over 3 times to check the data integrity of all 3 snapshots
        for i in range(1, 4):
            # Create volume from snapshot, attach it to instance and check file
            # and contents for snap
            volume_snap = self.create_volume(snapshot_id=snap_map[i]['id'])
            volume_device_name, __ = self._attach_and_get_volume_device_name(
                server, volume_snap, instance_ip, self.keypair['private_key'])
            count_snap, md5_file = self.get_md5_from_file(
                server, instance_ip, 'file' + str(i),
                dev_name=volume_device_name)
            # Detach the volume
            self.nova_volume_detach(server, volume_snap)

            self.assertEqual(count_snap, i)
            self.assertEqual(file_map[i], md5_file)
