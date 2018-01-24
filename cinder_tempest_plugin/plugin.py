# Copyright 2015
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

import os

from tempest import config
from tempest.test_discover import plugins

from cinder_tempest_plugin import config as project_config


class CinderTempestPlugin(plugins.TempestPlugin):
    def load_tests(self):
        """Provides information to load the plugin tests.

        :return: A tuple with the first value being the test dir and the
                 second being the top level dir.
        """
        base_path = os.path.split(os.path.dirname(
            os.path.abspath(__file__)))[0]
        test_dir = "cinder_tempest_plugin"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf):
        """Adds additional configuration options to tempest.

        This method will be run for the plugin during the register_opts()
        function in tempest.config

        :param conf: The conf object that can be used to register additional
                     options.
        """
        config.register_opt_group(conf, config.volume_feature_group,
                                  project_config.cinder_option)

    def get_opt_lists(self):
        """Get a list of options for sample config generation.

        :return: A list of tuples with the group name and options in that
                 group.
        """
        return [
            (config.volume_feature_group.name, project_config.cinder_option),
        ]
