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

CONF = config.CONF


class VolumeV3RbacBaseTests(object):

    identity_version = 'v3'

    @classmethod
    def skip_checks(cls):
        super(VolumeV3RbacBaseTests, cls).skip_checks()
        if not CONF.enforce_scope.cinder:
            raise cls.skipException(
                "Tempest is not configured to enforce_scope for cinder, "
                "skipping RBAC tests. To enable these tests set "
                "`tempest.conf [enforce_scope] cinder=True`."
            )

    def do_request(self, method, expected_status=200, client=None, **payload):
        if not client:
            client = self.client
        if isinstance(expected_status, type(Exception)):
            self.assertRaises(expected_status,
                              getattr(client, method),
                              **payload)
        else:
            response = getattr(client, method)(**payload)
            self.assertEqual(response.response.status, expected_status)
            return response
