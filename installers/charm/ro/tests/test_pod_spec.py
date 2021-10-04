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
        port = 9090

        expected_result = [
            {
                "name": "ro",
                "containerPort": port,
                "protocol": "TCP",
            }
        ]

        pod_ports = pod_spec._make_pod_ports(port)

        self.assertListEqual(expected_result, pod_ports)

    def test_make_pod_envconfig_ng_ro(self) -> NoReturn:
        """Teting make pod envconfig."""
        config = {
            "enable_ng_ro": True,
            "database_commonkey": "osm",
            "log_level": "INFO",
        }
        relation_state = {
            "kafka_host": "kafka",
            "kafka_port": "9090",
            "mongodb_connection_string": "mongodb://mongo",
        }

        expected_result = {
            "OSMRO_LOG_LEVEL": config["log_level"],
            "OSMRO_MESSAGE_DRIVER": "kafka",
            "OSMRO_MESSAGE_HOST": relation_state["kafka_host"],
            "OSMRO_MESSAGE_PORT": relation_state["kafka_port"],
            "OSMRO_DATABASE_DRIVER": "mongo",
            "OSMRO_DATABASE_URI": relation_state["mongodb_connection_string"],
            "OSMRO_DATABASE_COMMONKEY": config["database_commonkey"],
        }

        pod_envconfig = pod_spec._make_pod_envconfig(config, relation_state)

        self.assertDictEqual(expected_result, pod_envconfig)

    def test_make_pod_envconfig_no_ng_ro(self) -> NoReturn:
        """Teting make pod envconfig."""
        config = {
            "log_level": "INFO",
            "enable_ng_ro": False,
            "vim_database": "mano_vim_db",
            "ro_database": "mano_db",
            "openmano_tenant": "osm",
        }
        relation_state = {
            "mysql_host": "mysql",
            "mysql_port": 3306,
            "mysql_user": "mano",
            "mysql_password": "manopw",
            "mysql_root_password": "rootmanopw",
        }

        expected_result = {
            "OSMRO_LOG_LEVEL": config["log_level"],
            "RO_DB_HOST": relation_state["mysql_host"],
            "RO_DB_OVIM_HOST": relation_state["mysql_host"],
            "RO_DB_PORT": relation_state["mysql_port"],
            "RO_DB_OVIM_PORT": relation_state["mysql_port"],
            "RO_DB_USER": relation_state["mysql_user"],
            "RO_DB_OVIM_USER": relation_state["mysql_user"],
            "RO_DB_PASSWORD": relation_state["mysql_password"],
            "RO_DB_OVIM_PASSWORD": relation_state["mysql_password"],
            "RO_DB_ROOT_PASSWORD": relation_state["mysql_root_password"],
            "RO_DB_OVIM_ROOT_PASSWORD": relation_state["mysql_root_password"],
            "RO_DB_NAME": config["ro_database"],
            "RO_DB_OVIM_NAME": config["vim_database"],
            "OPENMANO_TENANT": config["openmano_tenant"],
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
        port = 9090

        expected_result = {
            "httpGet": {
                "path": "/openmano/tenants",
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
        port = 9090

        expected_result = {
            "httpGet": {
                "path": "/openmano/tenants",
                "port": port,
            },
            "initialDelaySeconds": 600,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

        liveness_probe = pod_spec._make_liveness_probe(port)

        self.assertDictEqual(expected_result, liveness_probe)

    def test_make_pod_spec_ng_ro(self) -> NoReturn:
        """Testing make pod spec."""
        image_info = {"upstream-source": "opensourcemano/ro:8"}
        config = {
            "database_commonkey": "osm",
            "log_level": "INFO",
            "enable_ng_ro": True,
        }
        relation_state = {
            "kafka_host": "kafka",
            "kafka_port": "9090",
            "mongodb_connection_string": "mongodb://mongo",
        }
        app_name = "ro"
        port = 9090

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
                        "OSMRO_LOG_LEVEL": config["log_level"],
                        "OSMRO_MESSAGE_DRIVER": "kafka",
                        "OSMRO_MESSAGE_HOST": relation_state["kafka_host"],
                        "OSMRO_MESSAGE_PORT": relation_state["kafka_port"],
                        "OSMRO_DATABASE_DRIVER": "mongo",
                        "OSMRO_DATABASE_URI": relation_state[
                            "mongodb_connection_string"
                        ],
                        "OSMRO_DATABASE_COMMONKEY": config["database_commonkey"],
                    },
                    "kubernetes": {
                        "startupProbe": {
                            "exec": {"command": ["/usr/bin/pgrep", "python3"]},
                            "initialDelaySeconds": 60,
                            "timeoutSeconds": 5,
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/openmano/tenants",
                                "port": port,
                            },
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "successThreshold": 1,
                            "failureThreshold": 3,
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/openmano/tenants",
                                "port": port,
                            },
                            "initialDelaySeconds": 600,
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "successThreshold": 1,
                            "failureThreshold": 3,
                        },
                    },
                }
            ],
            "kubernetesResources": {"ingressResources": []},
        }

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertDictEqual(expected_result, spec)

    def test_make_pod_spec_no_ng_ro(self) -> NoReturn:
        """Testing make pod spec."""
        image_info = {"upstream-source": "opensourcemano/ro:8"}
        config = {
            "log_level": "INFO",
            "enable_ng_ro": False,
            "vim_database": "mano_vim_db",
            "ro_database": "mano_db",
            "openmano_tenant": "osm",
        }
        relation_state = {
            "mysql_host": "mysql",
            "mysql_port": 3306,
            "mysql_user": "mano",
            "mysql_password": "manopw",
            "mysql_root_password": "rootmanopw",
        }
        app_name = "ro"
        port = 9090

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
                        "OSMRO_LOG_LEVEL": config["log_level"],
                        "RO_DB_HOST": relation_state["mysql_host"],
                        "RO_DB_OVIM_HOST": relation_state["mysql_host"],
                        "RO_DB_PORT": relation_state["mysql_port"],
                        "RO_DB_OVIM_PORT": relation_state["mysql_port"],
                        "RO_DB_USER": relation_state["mysql_user"],
                        "RO_DB_OVIM_USER": relation_state["mysql_user"],
                        "RO_DB_PASSWORD": relation_state["mysql_password"],
                        "RO_DB_OVIM_PASSWORD": relation_state["mysql_password"],
                        "RO_DB_ROOT_PASSWORD": relation_state["mysql_root_password"],
                        "RO_DB_OVIM_ROOT_PASSWORD": relation_state[
                            "mysql_root_password"
                        ],
                        "RO_DB_NAME": config["ro_database"],
                        "RO_DB_OVIM_NAME": config["vim_database"],
                        "OPENMANO_TENANT": config["openmano_tenant"],
                    },
                    "kubernetes": {
                        "startupProbe": {
                            "exec": {"command": ["/usr/bin/pgrep", "python3"]},
                            "initialDelaySeconds": 60,
                            "timeoutSeconds": 5,
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/openmano/tenants",
                                "port": port,
                            },
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "successThreshold": 1,
                            "failureThreshold": 3,
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/openmano/tenants",
                                "port": port,
                            },
                            "initialDelaySeconds": 600,
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "successThreshold": 1,
                            "failureThreshold": 3,
                        },
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
            "enable_ng_ro": True,
            "database_commonkey": "osm",
            "log_level": "INFO",
        }
        relation_state = {
            "kafka_host": "kafka",
            "kafka_port": 9090,
            "mongodb_connection_string": "mongodb://mongo",
        }
        app_name = "ro"
        port = 9090

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertIsNone(spec)

    def test_make_pod_spec_without_config(self) -> NoReturn:
        """Testing make pod spec without config."""
        image_info = {"upstream-source": "opensourcemano/ro:8"}
        config = {}
        relation_state = {
            "kafka_host": "kafka",
            "kafka_port": 9090,
            "mongodb_connection_string": "mongodb://mongo",
        }
        app_name = "ro"
        port = 9090

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)

    def test_make_pod_spec_without_relation_state(self) -> NoReturn:
        """Testing make pod spec without relation_state."""
        image_info = {"upstream-source": "opensourcemano/ro:8"}
        config = {
            "enable_ng_ro": True,
            "database_commonkey": "osm",
            "log_level": "INFO",
        }
        relation_state = {}
        app_name = "ro"
        port = 9090

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)


if __name__ == "__main__":
    unittest.main()
