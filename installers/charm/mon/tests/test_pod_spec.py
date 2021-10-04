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
        port = 8000

        expected_result = [
            {
                "name": "mon",
                "containerPort": port,
                "protocol": "TCP",
            }
        ]

        pod_ports = pod_spec._make_pod_ports(port)

        self.assertListEqual(expected_result, pod_ports)

    def test_make_pod_envconfig(self) -> NoReturn:
        """Testing make pod envconfig."""
        config = {
            "openstack_default_granularity": 300,
            "global_request_timeout": 10,
            "log_level": "INFO",
            "database_commonkey": "osm",
            "collector_interval": 30,
            "evaluator_interval": 30,
            "vca_host": "admin",
            "vca_user": "admin",
            "vca_password": "secret",
            "vca_cacert": "",
        }
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
            "prometheus_host": "prometheus",
            "prometheus_port": 9082,
        }

        expected_result = {
            "ALLOW_ANONYMOUS_LOGIN": "yes",
            "OSMMON_OPENSTACK_DEFAULT_GRANULARITY": config[
                "openstack_default_granularity"
            ],
            "OSMMON_GLOBAL_REQUEST_TIMEOUT": config["global_request_timeout"],
            "OSMMON_GLOBAL_LOGLEVEL": config["log_level"],
            "OSMMON_COLLECTOR_INTERVAL": config["collector_interval"],
            "OSMMON_EVALUATOR_INTERVAL": config["evaluator_interval"],
            "OSMMON_MESSAGE_DRIVER": "kafka",
            "OSMMON_MESSAGE_HOST": relation_state["message_host"],
            "OSMMON_MESSAGE_PORT": relation_state["message_port"],
            "OSMMON_DATABASE_DRIVER": "mongo",
            "OSMMON_DATABASE_URI": relation_state["database_uri"],
            "OSMMON_DATABASE_COMMONKEY": config["database_commonkey"],
            "OSMMON_PROMETHEUS_URL": f"http://{relation_state['prometheus_host']}:{relation_state['prometheus_port']}",
            "OSMMON_VCA_HOST": config["vca_host"],
            "OSMMON_VCA_USER": config["vca_user"],
            "OSMMON_VCA_SECRET": config["vca_password"],
            "OSMMON_VCA_CACERT": config["vca_cacert"],
        }

        pod_envconfig = pod_spec._make_pod_envconfig(config, relation_state)

        self.assertDictEqual(expected_result, pod_envconfig)

    def test_make_startup_probe(self) -> NoReturn:
        """Testing make startup probe."""
        expected_result = {
            "exec": {"command": ["/usr/bin/pgrep python3"]},
            "initialDelaySeconds": 60,
            "timeoutSeconds": 5,
        }

        startup_probe = pod_spec._make_startup_probe()

        self.assertDictEqual(expected_result, startup_probe)

    def test_make_readiness_probe(self) -> NoReturn:
        """Testing make readiness probe."""
        port = 8000

        expected_result = {
            "tcpSocket": {
                "port": port,
            },
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

        readiness_probe = pod_spec._make_readiness_probe(port)

        self.assertDictEqual(expected_result, readiness_probe)

    def test_make_liveness_probe(self) -> NoReturn:
        """Testing make liveness probe."""
        port = 8000

        expected_result = {
            "tcpSocket": {
                "port": port,
            },
            "initialDelaySeconds": 45,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

        liveness_probe = pod_spec._make_liveness_probe(port)

        self.assertDictEqual(expected_result, liveness_probe)

    def test_make_pod_spec(self) -> NoReturn:
        """Testing make pod spec."""
        image_info = {"upstream-source": "opensourcemano/mon:8"}
        config = {
            "site_url": "",
            "openstack_default_granularity": 300,
            "global_request_timeout": 10,
            "log_level": "INFO",
            "database_commonkey": "osm",
            "collector_interval": 30,
            "evaluator_interval": 30,
            "vca_host": "admin",
            "vca_user": "admin",
            "vca_password": "secret",
            "vca_cacert": "",
        }
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
            "prometheus_host": "prometheus",
            "prometheus_port": 9082,
        }
        app_name = "mon"
        port = 8000

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
                        "OSMMON_OPENSTACK_DEFAULT_GRANULARITY": config[
                            "openstack_default_granularity"
                        ],
                        "OSMMON_GLOBAL_REQUEST_TIMEOUT": config[
                            "global_request_timeout"
                        ],
                        "OSMMON_GLOBAL_LOGLEVEL": config["log_level"],
                        "OSMMON_COLLECTOR_INTERVAL": config["collector_interval"],
                        "OSMMON_EVALUATOR_INTERVAL": config["evaluator_interval"],
                        "OSMMON_MESSAGE_DRIVER": "kafka",
                        "OSMMON_MESSAGE_HOST": relation_state["message_host"],
                        "OSMMON_MESSAGE_PORT": relation_state["message_port"],
                        "OSMMON_DATABASE_DRIVER": "mongo",
                        "OSMMON_DATABASE_URI": relation_state["database_uri"],
                        "OSMMON_DATABASE_COMMONKEY": config["database_commonkey"],
                        "OSMMON_PROMETHEUS_URL": (
                            f"http://{relation_state['prometheus_host']}:{relation_state['prometheus_port']}"
                        ),
                        "OSMMON_VCA_HOST": config["vca_host"],
                        "OSMMON_VCA_USER": config["vca_user"],
                        "OSMMON_VCA_SECRET": config["vca_password"],
                        "OSMMON_VCA_CACERT": config["vca_cacert"],
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
            "site_url": "",
            "openstack_default_granularity": 300,
            "global_request_timeout": 10,
            "log_level": "INFO",
            "database_commonkey": "osm",
            "collector_interval": 30,
            "evaluator_interval": 30,
            "vca_host": "admin",
            "vca_user": "admin",
            "vca_password": "secret",
            "vca_cacert": "",
        }
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
            "prometheus_host": "prometheus",
            "prometheus_port": 9082,
        }
        app_name = "mon"
        port = 8000

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertIsNone(spec)

    def test_make_pod_spec_without_config(self) -> NoReturn:
        """Testing make pod spec without config."""
        image_info = {"upstream-source": "opensourcemano/mon:8"}
        config = {}
        relation_state = {
            "message_host": "kafka",
            "message_port": 9090,
            "database_uri": "mongodb://mongo",
            "prometheus_host": "prometheus",
            "prometheus_port": 9082,
        }
        app_name = "mon"
        port = 8000

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)

    def test_make_pod_spec_without_relation_state(self) -> NoReturn:
        """Testing make pod spec without relation_state."""
        image_info = {"upstream-source": "opensourcemano/mon:8"}
        config = {
            "site_url": "",
            "openstack_default_granularity": 300,
            "global_request_timeout": 10,
            "log_level": "INFO",
            "database_commonkey": "osm",
            "collector_interval": 30,
            "evaluator_interval": 30,
            "vca_host": "admin",
            "vca_user": "admin",
            "vca_password": "secret",
            "vca_cacert": "",
        }
        relation_state = {}
        app_name = "mon"
        port = 8000

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)


if __name__ == "__main__":
    unittest.main()
