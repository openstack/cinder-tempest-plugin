# Copyright 2016
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

from oslo_config import cfg

cinder_option = [
    cfg.BoolOpt('consistency_group',
                default=False,
                help='Enable to run Cinder volume consistency group tests'),
    cfg.BoolOpt('volume_revert',
                default=False,
                help='Enable to run Cinder volume revert tests'),
    cfg.BoolOpt('volume_image_dep_tests',
                default=True,
                help='Run tests for dependencies between images and volumes')
]

# The barbican service is discovered by config_tempest [1], and will appear
# in the [service_available] group in tempest.conf. However, the 'barbican'
# option isn't registered by tempest itself, and so we may need to do it.
# This adds the ability to test CONF.service_available.barbican.
#
# [1] I96800a95f844ce7675d266e456e01620e63e347a
barbican_service_option = [
    cfg.BoolOpt('barbican',
                default=False,
                help="Whether or not barbican is expected to be available"),
]
