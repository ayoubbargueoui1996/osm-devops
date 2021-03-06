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


def get_prometheus_uri():
    ip = model.get_status().applications["prometheus-k8s"]["public-address"]
    port = 9090
    return "http://{}:{}".format(ip, port)


class BasicDeployment(unittest.TestCase):
    def test_get_prometheus_uri(self):
        get_prometheus_uri()

    def test_prometheus_get_series(self):
        prometheus_uri = get_prometheus_uri()
        body = http.get("{}/api/v1/series?match[]=up".format(prometheus_uri))
        self.assertEqual(body.status_code, 200)

    def test_prometheus_get_labels(self):
        prometheus_uri = get_prometheus_uri()
        body = http.get("{}/api/v1/labels".format(prometheus_uri))
        self.assertEqual(body.status_code, 200)

    def test_prometheus_get_targets(self):
        prometheus_uri = get_prometheus_uri()
        body = http.get("{}/api/v1/targets".format(prometheus_uri))
        self.assertEqual(body.status_code, 200)

    def test_prometheus_get_alerts(self):
        prometheus_uri = get_prometheus_uri()
        body = http.get("{}/api/v1/alerts".format(prometheus_uri))
        self.assertEqual(body.status_code, 200)

    def test_prometheus_get_status_config(self):
        prometheus_uri = get_prometheus_uri()
        body = http.get("{}/api/v1/status/config".format(prometheus_uri))
        self.assertEqual(body.status_code, 200)
