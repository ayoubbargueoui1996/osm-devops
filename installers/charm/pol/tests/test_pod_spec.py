#!/usr/bin/env python3
# Copyright 2020 Canonical Ltd.
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

from typing import NoReturn
import unittest

import pod_spec


class TestPodSpec(unittest.TestCase):
    """Pod spec unit tests."""

    def test_make_pod_ports(self) -> NoReturn:
        """Testing make pod ports."""
        port = 80

        expected_result = [
            {
                "name": "pol",
                "containerPort": port,
                "protocol": "TCP",
            }
        ]

        pod_ports = pod_spec._make_pod_ports(port)

        self.assertListEqual(expected_result, pod_ports)

    def test_make_pod_envconfig(self) -> NoReturn:
        """Teting make pod envconfig."""
        config = {
            "log_level": "INFO",
        }
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
        }

        expected_result = {
            "ALLOW_ANONYMOUS_LOGIN": "yes",
            "OSMPOL_GLOBAL_LOGLEVEL": config["log_level"],
            "OSMPOL_MESSAGE_HOST": relation_state["message_host"],
            "OSMPOL_MESSAGE_DRIVER": "kafka",
            "OSMPOL_MESSAGE_PORT": relation_state["message_port"],
            "OSMPOL_DATABASE_DRIVER": "mongo",
            "OSMPOL_DATABASE_URI": relation_state["database_uri"],
        }

        pod_envconfig = pod_spec._make_pod_envconfig(config, relation_state)

        self.assertDictEqual(expected_result, pod_envconfig)

    def test_make_startup_probe(self) -> NoReturn:
        """Testing make startup probe."""
        expected_result = {
            "exec": {"command": ["/usr/bin/pgrep", "python3"]},
            "initialDelaySeconds": 60,
            "timeoutSeconds": 5,
        }

        startup_probe = pod_spec._make_startup_probe()

        self.assertDictEqual(expected_result, startup_probe)

    def test_make_readiness_probe(self) -> NoReturn:
        """Testing make readiness probe."""
        expected_result = {
            "exec": {
                "command": ["sh", "-c", "osm-pol-healthcheck || exit 1"],
            },
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

        readiness_probe = pod_spec._make_readiness_probe()

        self.assertDictEqual(expected_result, readiness_probe)

    def test_make_liveness_probe(self) -> NoReturn:
        """Testing make liveness probe."""
        expected_result = {
            "exec": {
                "command": ["sh", "-c", "osm-pol-healthcheck || exit 1"],
            },
            "initialDelaySeconds": 45,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

        liveness_probe = pod_spec._make_liveness_probe()

        self.assertDictEqual(expected_result, liveness_probe)

    def test_make_pod_spec(self) -> NoReturn:
        """Testing make pod spec."""
        image_info = {"upstream-source": "opensourcemano/pol:8"}
        config = {
            "log_level": "INFO",
        }
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
        }
        app_name = "pol"
        port = 80

        expected_result = {
            "version": 3,
            "containers": [
                {
                    "name": app_name,
                    "imageDetails": image_info,
                    "imagePullPolicy": "Always",
                    "ports": [
                        {
                            "name": app_name,
                            "containerPort": port,
                            "protocol": "TCP",
                        }
                    ],
                    "envConfig": {
                        "ALLOW_ANONYMOUS_LOGIN": "yes",
                        "OSMPOL_GLOBAL_LOGLEVEL": config["log_level"],
                        "OSMPOL_MESSAGE_HOST": relation_state["message_host"],
                        "OSMPOL_MESSAGE_DRIVER": "kafka",
                        "OSMPOL_MESSAGE_PORT": relation_state["message_port"],
                        "OSMPOL_DATABASE_DRIVER": "mongo",
                        "OSMPOL_DATABASE_URI": relation_state["database_uri"],
                    },
                }
            ],
            "kubernetesResources": {"ingressResources": []},
        }

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertDictEqual(expected_result, spec)

    def test_make_pod_spec_without_image_info(self) -> NoReturn:
        """Testing make pod spec without image_info."""
        image_info = None
        config = {
            "log_level": "INFO",
        }
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
        }
        app_name = "pol"
        port = 80

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertIsNone(spec)

    def test_make_pod_spec_without_config(self) -> NoReturn:
        """Testing make pod spec without config."""
        image_info = {"upstream-source": "opensourcemano/pol:8"}
        config = {}
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
        }
        app_name = "pol"
        port = 80

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)

    def test_make_pod_spec_without_relation_state(self) -> NoReturn:
        """Testing make pod spec without relation_state."""
        image_info = {"upstream-source": "opensourcemano/pol:8"}
        config = {
            "log_level": "INFO",
        }
        relation_state = {}
        app_name = "pol"
        port = 80

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)


if __name__ == "__main__":
    unittest.main()
