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
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import multiprocessing

from tempest import config

CONF = config.CONF


def run_concurrent_tasks(target, **kwargs):
    """Run a target function concurrently using multiprocessing."""
    manager = multiprocessing.Manager()
    resource_ids = manager.list()
    # To capture exceptions
    errors = manager.list()
    resource_count = CONF.volume.concurrent_resource_count

    def wrapped_target(index, resource_ids, **kwargs):
        try:
            target(index, resource_ids, **kwargs)
        except Exception as e:
            errors.append(f"Worker {index} failed: {str(e)}")

    processes = []
    for i in range(resource_count):
        p = multiprocessing.Process(
            target=wrapped_target,
            args=(i, resource_ids),
            kwargs=kwargs
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    if errors:
        error_msg = "\n".join(errors)
        raise RuntimeError(
            f"One or more concurrent tasks failed:\n{error_msg}")

    return list(resource_ids)
