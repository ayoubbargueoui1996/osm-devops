#!/usr/bin/python3
# Copyright 2021 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: legal@canonical.com
#
# To get in touch with the maintainers, please contact:
# osm-charmers@lists.launchpad.net
##

import unittest
import zaza.model as model
import requests as http
import time


def get_grafana_uri():
    ip = model.get_status().applications["grafana-k8s"]["public-address"]
    port = 3000
    return "http://{}:{}".format(ip, port)


class BasicDeployment(unittest.TestCase):
    def setUp(self):
        ready = False
        num_retries = 0
        while not ready and num_retries < 5:
            if (
                model.get_status().applications["grafana-k8s"]["status"]["status"]
                == "active"
            ):
                ready = True
            else:
                num_retries += 1
                time.sleep(5)

    def test_get_grafana_uri(self):
        get_grafana_uri()

    def test_grafana_get_home(self):
        grafana_uri = get_grafana_uri()
        body = http.get("{}/api/dashboards/home".format(grafana_uri))
        self.assertEqual(body.status_code, 401)  # TODO: Get API Token

    def test_grafana_get_tags(self):
        grafana_uri = get_grafana_uri()
        body = http.get("{}/api/dashboards/tags".format(grafana_uri))
        self.assertEqual(body.status_code, 401)  # TODO: Get API Token
