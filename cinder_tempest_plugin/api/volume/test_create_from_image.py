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
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators

from cinder_tempest_plugin.api.volume import base

CONF = config.CONF


class VolumeFromImageTest(base.BaseVolumeTest):

    @classmethod
    def skip_checks(cls):
        super(VolumeFromImageTest, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException("Glance service is disabled")

    @classmethod
    def create_volume_no_wait(cls, **kwargs):
        """Returns a test volume.

        This does not wait for volume creation to finish,
        so that multiple operations can happen on the
        Cinder server in parallel.
        """
        if 'size' not in kwargs:
            kwargs['size'] = CONF.volume.volume_size

        if 'imageRef' in kwargs:
            image = cls.os_primary.image_client_v2.show_image(
                kwargs['imageRef'])
            min_disk = image['min_disk']
            kwargs['size'] = max(kwargs['size'], min_disk)

        if 'name' not in kwargs:
            name = data_utils.rand_name(cls.__name__ + '-Volume')
            kwargs['name'] = name

        volume = cls.volumes_client.create_volume(**kwargs)['volume']
        cls.addClassResourceCleanup(
            cls.volumes_client.wait_for_resource_deletion, volume['id'])
        cls.addClassResourceCleanup(test_utils.call_and_ignore_notfound_exc,
                                    cls.volumes_client.delete_volume,
                                    volume['id'])

        return volume

    @decorators.idempotent_id('8976a11b-1ddc-49b6-b66f-8c26adf3fa9e')
    def test_create_from_image_multiple(self):
        """Create a handful of volumes from the same image at once.

        The purpose of this test is to stress volume drivers,
        image download, the image cache, etc., within Cinder.
        """

        img_uuid = CONF.compute.image_ref

        vols = []
        for v in range(0, 5):
            vols.append(self.create_volume_no_wait(imageRef=img_uuid))

        for v in vols:
            waiters.wait_for_volume_resource_status(self.volumes_client,
                                                    v['id'],
                                                    'available')
