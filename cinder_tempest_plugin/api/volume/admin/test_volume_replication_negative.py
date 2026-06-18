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

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from cinder_tempest_plugin.api.volume import base


CONF = config.CONF


class VolumeReplicationNegativeTest(base.BaseVolumeAdminTest):

    volume_min_microversion = '3.26'
    volume_max_microversion = 'latest'

    @classmethod
    def skip_checks(cls):
        super(VolumeReplicationNegativeTest, cls).skip_checks()
        if not CONF.volume_feature_enabled.replication:
            raise cls.skipException("Volume replication feature disabled")
        if len(CONF.volume.backend_names) < 2:
            raise cls.skipException("Requires at least two different "
                                    "backend names")

    @classmethod
    def setup_clients(cls):
        super(VolumeReplicationNegativeTest, cls).setup_clients()
        cls.admin_volume_services_client = (
            cls.os_admin.volume_services_client_latest)
        cls.admin_stats_client = (
            cls.os_admin.volume_scheduler_stats_client_latest)

    @classmethod
    def resource_setup(cls):
        super(VolumeReplicationNegativeTest, cls).resource_setup()

        pools = cls.admin_stats_client.list_pools(detail=True)['pools']

        replication_pools = []
        non_replication_pools = []

        for pool in pools:
            name = pool['name']
            if pool['capabilities']['replication_enabled']:
                replication_pools.append(name)
            else:
                non_replication_pools.append(name)

        if not replication_pools:
            raise cls.skipException(
                "No backend with replication_enabled=True found.")
        if not non_replication_pools:
            raise cls.skipException(
                "No backend with replication_enabled=False found.")

        # Select the first matching backend from each category
        cls.replication_host, cls.replication_backend = replication_pools[
            0].split('#')
        cls.non_replication_host, cls.non_replication_backend = (
            non_replication_pools[0].split('#'))

    @decorators.attr(type='negative')
    @decorators.idempotent_id('7a5eeb4f-c441-4c88-88c7-77ac82c5e3aa')
    def test_create_replicated_volume_on_non_replication_backend(self):
        """Fail to create a replicated volume on non-replication backend."""
        replicated_specs = {
            'replication_enabled': '<is> True',
            'volume_backend_name': self.non_replication_backend,
        }
        replicated_type = self.create_volume_type(extra_specs=replicated_specs)

        self.assertRaises(
            lib_exc.BadRequest,
            self.volumes_client.create_volume,
            volume_type=replicated_type['id']
        )

    @decorators.attr(type='negative')
    @decorators.idempotent_id('6a7611d3-30f6-4d58-9b0e-4b248c552c8d')
    def test_failover_non_replicated_volume(self):
        """Attempting to failover a non-replicated volume should fail."""
        non_replication_specs = {
            'volume_backend_name': self.non_replication_backend,
        }
        non_rep_type = self.create_volume_type(
            extra_specs=non_replication_specs)
        self.create_volume(volume_type=non_rep_type['id'])

        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_volume_services_client.failover_host,
            host=self.non_replication_host
        )

    @decorators.attr(type='negative')
    @decorators.idempotent_id('8990d3f3-e151-4b5f-9580-20171c8b7153')
    def test_snapshot_replicated_volume_error_state(self):
        """Snapshot creation should fail when volume is in error state."""
        replicated_specs = {
            'replication_enabled': '<is> True',
            'volume_backend_name': self.replication_backend,
        }
        replication_volume_type = self.create_volume_type(
            extra_specs=replicated_specs
        )
        volume = self.create_volume(
            volume_type=replication_volume_type['id'])
        # Simulate volume error state
        self.admin_volume_client.reset_volume_status(
            volume['id'], status='error')

        self.assertRaises(
            lib_exc.BadRequest,
            self.create_snapshot,
            volume['id']
        )
