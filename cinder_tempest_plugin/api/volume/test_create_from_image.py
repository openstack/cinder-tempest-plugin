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

import io

from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators

from cinder_tempest_plugin.api.volume import base

CONF = config.CONF


class VolumeAndVolumeTypeFromImageTest(base.BaseVolumeAdminTest):
    # needs AdminTest as superclass to manipulate volume_types

    @classmethod
    def skip_checks(cls):
        super(VolumeAndVolumeTypeFromImageTest, cls).skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException("Glance service is disabled")

    @classmethod
    def create_image_with_data(cls, **kwargs):
        # we do this as a class method so we can use the
        # addClassResourceCleanup functionality of tempest.test.BaseTestCase
        images_client = cls.os_primary.image_client_v2
        if 'min_disk' not in kwargs:
            kwargs['min_disk'] = 1
        response = images_client.create_image(**kwargs)
        image_id = response['id']
        cls.addClassResourceCleanup(
            images_client.wait_for_resource_deletion, image_id)
        cls.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            images_client.delete_image, image_id)

        # upload "data" to image
        image_file = io.BytesIO(data_utils.random_bytes(size=1024))
        images_client.store_image_file(image_id, image_file)

        waiters.wait_for_image_status(images_client, image_id, 'active')
        image = images_client.show_image(image_id)
        return image

    @decorators.idempotent_id('6e9266ff-a917-4dd5-aa4a-c36e59e7a2a6')
    def test_create_from_image_with_volume_type_image_property(self):
        """Verify that the cinder_img_volume_type image property works.

        When a volume is created from an image containing the
        cinder_img_volume_type property and no volume_type is specified
        in the volume-create request, the volume_type of the resulting
        volume should be the one specified by the image property.
        """

        volume_type_meta = 'cinder_img_volume_type'
        volume_type_name = 'vol-type-for-6e9266ff-a917-4dd5-aa4a-c36e59e7a2a6'
        description = ('Generic volume_type for test '
                       '6e9266ff-a917-4dd5-aa4a-c36e59e7a2a6')
        proto = CONF.volume.storage_protocol
        vendor = CONF.volume.vendor_name
        extra_specs = {"storage_protocol": proto,
                       "vendor_name": vendor}
        kwargs = {'description': description,
                  'extra_specs': extra_specs,
                  'os-volume-type-access:is_public': True}
        volume_type = self.create_volume_type(name=volume_type_name,
                                              **kwargs)
        # quick sanity check
        self.assertEqual(volume_type_name, volume_type['name'])

        # create an image in glance
        kwargs = {'disk_format': 'raw',
                  'container_format': 'bare',
                  'name': ('image-for-test-'
                           '6e9266ff-a917-4dd5-aa4a-c36e59e7a2a6'),
                  'visibility': 'private',
                  volume_type_meta: volume_type_name}
        image = self.create_image_with_data(**kwargs)
        # quick sanity check
        self.assertEqual(volume_type_name, image[volume_type_meta])

        # create volume from image
        kwargs = {'name': ('volume-for-test-'
                           '6e9266ff-a917-4dd5-aa4a-c36e59e7a2a6'),
                  'imageRef': image['id']}
        # this is the whole point of the test, so make sure this is true
        self.assertNotIn('volume_type', kwargs)
        volume = self.create_volume(**kwargs)

        found_volume_type = volume['volume_type']
        self.assertEqual(volume_type_name, found_volume_type)
