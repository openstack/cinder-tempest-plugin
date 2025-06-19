# Copyright 2025 Red Hat, Inc.
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

from tempest.common import compute
from tempest.common import utils
from tempest.common import waiters
from tempest import config
from tempest.lib import decorators
from tempest.scenario import manager as tempest_manager

from cinder_tempest_plugin.scenario import manager


CONF = config.CONF


class VolumeReplicationTest(manager.ScenarioTest,
                            tempest_manager.EncryptionScenarioTest):

    volume_min_microversion = '3.27'
    volume_max_microversion = 'latest'

    @classmethod
    def skip_checks(cls):
        super(VolumeReplicationTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.replication:
            raise cls.skipException("Volume replication feature disabled")
        if len(CONF.volume.backend_names) < 2:
            raise cls.skipException("Requires at least two different "
                                    "backend names")

    @classmethod
    def setup_clients(cls):
        super(VolumeReplicationTest, cls).setup_clients()
        cls.admin_volume_services_client = (
            cls.os_admin.volume_services_client_latest)
        cls.admin_stats_client = (
            cls.os_admin.volume_scheduler_stats_client_latest)
        cls.attachment = cls.os_admin.attachments_client_latest

    @classmethod
    def resource_setup(cls):
        super(VolumeReplicationTest, cls).resource_setup()
        pools = cls.admin_stats_client.list_pools(detail=True)['pools']
        replication_pools = [
            pool['name'] for pool in pools if
            pool['capabilities']['replication_enabled']
        ]
        if not replication_pools:
            raise cls.skipException(
                "No backend with replication_enabled=True found.")
        cls.replication_host, replication_backend = (
            replication_pools[0].split('#', 1))

        cls.replication_specs = {
            'replication_enabled': '<is> True',
            'volume_backend_name': replication_backend,
        }

    def _boot_instance(self, boot_from_volume=False, keypair=None,
                       security_groups=None):
        keypair = keypair or self.create_keypair()
        security_group = security_groups or self.create_security_group()
        volume = None
        if boot_from_volume:
            volume_type = self.create_volume_type(
                extra_specs=self.replication_specs
            )
            volume = self.create_volume_from_image(
                volume_type_id=volume_type['id']
            )
            volume_details = self.volumes_client.show_volume(
                volume['id'])['volume']
            self.assertEqual(volume_details['replication_status'], 'enabled')
            server = self.boot_instance_from_resource(
                source_id=volume['id'],
                source_type='volume',
                keypair=keypair,
                security_group=security_group
            )
        else:
            server = self.create_server(
                key_name=keypair['name'],
                security_groups=[{'name': security_group['name']}],
            )
        return server, volume

    def _detach_then_reattach_volume(self, server, volume):
        self.servers_client.detach_volume(server['id'], volume['id'])
        waiters.wait_for_volume_resource_status(
            self.volumes_client, volume['id'], 'available')
        waiters.wait_for_volume_attachment_remove_from_server(
            self.servers_client, server['id'], volume['id'])
        self.attach_volume(server, volume)

    def _shelve_then_unshelve_server(self, server):
        compute.shelve_server(self.servers_client, server['id'],
                              force_shelve_offload=True)
        self.servers_client.unshelve_server(server['id'])
        waiters.wait_for_server_status(
            self.servers_client, server['id'], 'ACTIVE')

    def _get_attachment_cluster_name(self, volume):
        volume_detail = self.volumes_client.show_volume(
            volume['id'])['volume']
        attachment_id = volume_detail['attachments'][0]['attachment_id']
        attachment = self.attachment.show_attachment(
            attachment_id)['attachment']
        return attachment['connection_info']['cluster_name']

    def _test_failover_scenario(self, boot_from_volume=False,
                                attach_after_boot=False):
        keypair = self.create_keypair()
        security_group = self.create_security_group()

        # Boot server with or without bootable volume
        server, volume = self._boot_instance(
            boot_from_volume=boot_from_volume,
            keypair=keypair,
            security_groups=security_group
        )
        server_ip = self.get_server_ip(server)

        # Create and attach replicated volume (attached-volume case only)
        volume_device_name = None
        if attach_after_boot:
            replication_volume_type = self.create_volume_type(
                extra_specs=self.replication_specs
            )
            volume = self.create_volume(
                volume_type=replication_volume_type['id'])
            volume_details = self.volumes_client.show_volume(
                volume['id'])['volume']
            self.assertEqual(volume_details['replication_status'], 'enabled')
            ssh_client = self.get_remote_client(
                server_ip, private_key=keypair['private_key'], server=server)
            disks_before_attach = ssh_client.list_disks()
            self.attach_volume(server, volume)
            waiters.wait_for_volume_resource_status(
                self.volumes_client, volume['id'], 'in-use')
            volume_device_name = self._attached_volume_name(
                disks_before_attach, server_ip, keypair['private_key'])

        # Record primary cluster and write timestamp before failover
        primary_cluster_name = self._get_attachment_cluster_name(volume)
        timestamp_on_primary = self.create_timestamp(
            server_ip, dev_name=volume_device_name,
            private_key=keypair['private_key'], server=server)

        # Failover to secondary
        self.admin_volume_services_client.failover_host(
            host=self.replication_host)
        waiters.wait_for_volume_replication_status(
            self.volumes_client, volume['id'], 'failed-over')

        # Reconnect volume to secondary backend
        if attach_after_boot:
            self._detach_then_reattach_volume(server, volume)
        else:
            self._shelve_then_unshelve_server(server)
            server_ip = self.get_server_ip(server)

        # Verify secondary cluster and data integrity after failover
        secondary_cluster_name = self._get_attachment_cluster_name(volume)
        self.assertNotEqual(primary_cluster_name, secondary_cluster_name)
        timestamp_after_failover = self.get_timestamp(
            server_ip, dev_name=volume_device_name,
            private_key=keypair['private_key'], server=server)
        self.assertEqual(timestamp_on_primary, timestamp_after_failover)

        # Skip the secondary write for the attached-volume case:
        # detach/reattach takes ~10s, which is too short for Ceph's async
        # rbd-mirror journal replay (ceph2 → ceph) to complete after failback.
        # Shelve/unshelve used for BFV takes ~60-120s, giving rbd-mirror
        # enough time to finish.
        timestamp_on_secondary = None
        if not attach_after_boot:
            timestamp_on_secondary = self.create_timestamp(
                server_ip, dev_name=volume_device_name,
                private_key=keypair['private_key'], server=server)

        # Failback to primary
        self.admin_volume_services_client.failover_host(
            host=self.replication_host, backend_id='default')
        waiters.wait_for_volume_replication_status(
            self.volumes_client, volume['id'], 'enabled')

        # Reconnect volume to primary backend
        if attach_after_boot:
            self._detach_then_reattach_volume(server, volume)
        else:
            self._shelve_then_unshelve_server(server)
            server_ip = self.get_server_ip(server)

        # Verify primary cluster and data integrity after failback
        self.assertEqual(
            primary_cluster_name, self._get_attachment_cluster_name(volume))
        timestamp_after_failback = self.get_timestamp(
            server_ip, dev_name=volume_device_name,
            private_key=keypair['private_key'], server=server)
        if attach_after_boot:
            self.assertEqual(timestamp_on_primary, timestamp_after_failback)
        else:
            self.assertEqual(timestamp_on_secondary, timestamp_after_failback)

    @decorators.idempotent_id('7df9ba86-1223-4d2b-a5ee-b16ed8cf1634')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_failover_bfv_server(self):
        """Test failover with bootable replicated volume."""
        self._test_failover_scenario(boot_from_volume=True)

    @decorators.idempotent_id('a32f4f96-6b2d-11ee-8c99-0242ac120002')
    @utils.services('compute', 'volume', 'image', 'network')
    def test_failover_attached_volume(self):
        """Test failover with volume attached after booting from image."""
        self._test_failover_scenario(attach_after_boot=True)
