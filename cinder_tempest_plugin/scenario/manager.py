# Copyright 2021 Red Hat, Inc.
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

import contextlib

from oslo_log import log

from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc

from tempest.scenario import manager

CONF = config.CONF

LOG = log.getLogger(__name__)


class ScenarioTest(manager.ScenarioTest):

    credentials = ['primary', 'admin']

    @classmethod
    def setup_clients(cls):
        super(ScenarioTest, cls).setup_clients()
        cls.admin_volume_types_client = cls.os_admin.volume_types_client_latest

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

    @contextlib.contextmanager
    def mount_dev_path(self, ssh_client, dev_name, mount_path):
        if dev_name is not None:
            ssh_client.exec_command('sudo mount /dev/%s %s' % (dev_name,
                                                               mount_path))
            yield
            ssh_client.exec_command('sudo umount %s' % mount_path)
        else:
            yield

    def _get_file_md5(self, ip_address, filename, dev_name=None,
                      mount_path='/mnt', private_key=None, server=None):

        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)
        with self.mount_dev_path(ssh_client, dev_name, mount_path):
            md5_sum = ssh_client.exec_command(
                'sudo md5sum %s/%s|cut -c 1-32' % (mount_path, filename))
        return md5_sum

    def _count_files(self, ip_address, dev_name=None, mount_path='/mnt',
                     private_key=None, server=None):
        ssh_client = self.get_remote_client(ip_address,
                                            private_key=private_key,
                                            server=server)
        with self.mount_dev_path(ssh_client, dev_name, mount_path):
            count = ssh_client.exec_command(
                'sudo ls -l %s | wc -l' % mount_path)
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

        with self.mount_dev_path(ssh_client, dev_name, mount_path):
            ssh_client.exec_command(
                'sudo dd bs=1024 count=100 if=/dev/urandom of=/%s/%s' %
                (mount_path, filename))
            md5 = ssh_client.exec_command(
                'sudo md5sum -b %s/%s|cut -c 1-32' % (mount_path, filename))
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

    def write_data_to_device(self, ip_address, out_dev, in_dev='/dev/urandom',
                             bs=1024, count=100, private_key=None,
                             server=None, sha_sum=False):
        ssh_client = self.get_remote_client(
            ip_address, private_key=private_key, server=server)

        # Write data to device
        write_command = (
            'sudo dd bs=%(bs)s count=%(count)s if=%(in_dev)s of=%(out_dev)s '
            '&& sudo dd bs=%(bs)s count=%(count)s if=%(out_dev)s' %
            {'bs': str(bs), 'count': str(count), 'in_dev': in_dev,
             'out_dev': out_dev})
        if sha_sum:
            # If we want to read sha1sum instead of the device data
            write_command += ' | sha1sum | head -c 40'
        data = ssh_client.exec_command(write_command)

        return data

    def read_data_from_device(self, ip_address, in_dev, bs=1024, count=100,
                              private_key=None, server=None, sha_sum=False):
        ssh_client = self.get_remote_client(
            ip_address, private_key=private_key, server=server)

        # Read data from device
        read_command = ('sudo dd bs=%(bs)s count=%(count)s if=%(in_dev)s' %
                        {'bs': bs, 'count': count, 'in_dev': in_dev})
        if sha_sum:
            # If we want to read sha1sum instead of the device data
            read_command += ' | sha1sum  | head -c 40'
        data = ssh_client.exec_command(read_command)

        return data

    def _attach_and_get_volume_device_name(self, server, volume, instance_ip,
                                           private_key):
        ssh_client = self.get_remote_client(
            instance_ip, private_key=private_key,
            server=server)
        # List disks before volume attachment
        disks_list_before_attach = ssh_client.list_disks()
        # Attach volume
        attachment = self.attach_volume(server, volume)
        # Find the difference between disks before and after attachment that
        # gives us the volume device name
        volume_device_name = self._attached_volume_name(
            disks_list_before_attach, instance_ip, private_key)
        return volume_device_name, attachment

    def create_volume_type(self, client=None, name=None, extra_specs=None):
        if not client:
            client = self.os_admin.volume_types_client_latest
        if not name:
            class_name = self.__class__.__name__
            name = data_utils.rand_name(class_name + '-volume-type')
        randomized_name = data_utils.rand_name('scenario-type-' + name)

        LOG.debug("Creating a volume type: %s with extra_specs %s",
                  randomized_name, extra_specs)
        if extra_specs is None:
            extra_specs = {}
        volume_type = self.admin_volume_types_client.create_volume_type(
            name=randomized_name, extra_specs=extra_specs)['volume_type']
        self.addCleanup(self.cleanup_volume_type, volume_type)
        return volume_type

    def attach_volume(self, server, volume, device=None, tag=None):
        """Attaches volume to server and waits for 'in-use' volume status.

        The volume will be detached when the test tears down.

        :param server: The server to which the volume will be attached.
        :param volume: The volume to attach.
        :param device: Optional mountpoint for the attached volume. Note that
            this is not guaranteed for all hypervisors and is not recommended.
        :param tag: Optional device role tag to apply to the volume.
        """
        attach_kwargs = dict(volumeId=volume['id'])
        if device:
            attach_kwargs['device'] = device
        if tag:
            attach_kwargs['tag'] = tag

        attachment = self.servers_client.attach_volume(
            server['id'], **attach_kwargs)['volumeAttachment']
        # On teardown detach the volume and for multiattach volumes wait for
        # the attachment to be removed. For non-multiattach volumes wait for
        # the state of the volume to change to available. This is so we don't
        # error out when trying to delete the volume during teardown.
        if volume['multiattach']:
            att = waiters.wait_for_volume_attachment_create(
                self.volumes_client, volume['id'], server['id'])
            self.addCleanup(waiters.wait_for_volume_attachment_remove,
                            self.volumes_client, volume['id'],
                            att['attachment_id'])
        else:
            self.addCleanup(waiters.wait_for_volume_resource_status,
                            self.volumes_client, volume['id'], 'available')
            waiters.wait_for_volume_resource_status(self.volumes_client,
                                                    volume['id'], 'in-use')
        # Ignore 404s on detach in case the server is deleted or the volume
        # is already detached.
        self.addCleanup(self._detach_volume, server, volume)
        return attachment

    def _detach_volume(self, server, volume):
        """Helper method to detach a volume.

        Ignores 404 responses if the volume or server do not exist, or the
        volume is already detached from the server.
        """
        try:
            volume = self.volumes_client.show_volume(volume['id'])['volume']
            # Check the status. You can only detach an in-use volume, otherwise
            # the compute API will return a 400 response.
            if volume['status'] == 'in-use':
                self.servers_client.detach_volume(server['id'], volume['id'])
        except lib_exc.NotFound:
            # Ignore 404s on detach in case the server is deleted or the volume
            # is already detached.
            pass
