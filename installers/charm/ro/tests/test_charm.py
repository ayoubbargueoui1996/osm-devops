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

import base64
from typing import NoReturn
import unittest

from charm import RoCharm
from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness


def encode(content: str):
    return base64.b64encode(content.encode("ascii")).decode("utf-8")


certificate_pem = encode(
    """
-----BEGIN CERTIFICATE-----
MIIDazCCAlOgAwIBAgIUf1b0s3UKtrxHXH2rge7UaQyfJAMwDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM
GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMTAzMjIxNzEyMjdaFw0zMTAz
MjAxNzEyMjdaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw
HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQCgCfCBgYAN6ON0yHDXuW407rFtJVRf0u46Jrp0Dk7J
kkSZ1e7Kq14r7yFHazEBWv78oOdwBocvWrd8leLuf3bYGcHR65hRy6A/fbYm5Aje
cKpwlFwaqfR4BLelwJl79jZ2rJX738cCBVrIk1nAVdOxGrXV4MTWUaKR2c+uKKvc
OKRT+5VqCeP4N5FWeATZ/KqGu8uV9E9WhFgwIZyStemLyLaDbn5PmAQ6S9oeR5jJ
o2gEEp/lDKvsqOWs76KFumSKa9hQs5Dw2lj0mb1UoyYK1gYc4ubzVChJadv44AU8
MYtIjlFn1X1P+RjaKZNUIAGXkoLwYn6SizF6y6LiuFS9AgMBAAGjUzBRMB0GA1Ud
DgQWBBRl+/23CB+FXczeAZRQyYcfOdy9YDAfBgNVHSMEGDAWgBRl+/23CB+FXcze
AZRQyYcfOdy9YDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAd
dkeDym6lRN8kWFtfu3IyiLF8G8sn91qNbH3Yr4TuTBhgcjYyW6PgisSbrNgA9ysE
GoaF7ohb8GeVfCsQdK23+NpAlj/+DZ3OnGcxwXj1RUAz4yr9kanV1yuEtr1q2xJI
UaECWr8HZlwGBAKNTGx2EXT2/2aFzgULpDcxzTKD+MRpKpMUrWhf9ULvVrclvHWe
POLYhobUFuBHuo6rt5Rcq16j67zCX9EVTlAE3o2OECIWByK22sXdeOidYMpTkl4q
8FrOqjNsx5d+SBPJBv/pqtBm4bA47Vx1P8tbWOQ4bXS0UmXgwpeBOU/O/ot30+KS
JnKEy+dYyvVBKg77sRHw
-----END CERTIFICATE-----
"""
)


class TestCharm(unittest.TestCase):
    """Prometheus Charm unit tests."""

    def setUp(self) -> NoReturn:
        """Test setup"""
        self.harness = Harness(RoCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        self.config = {
            "enable_ng_ro": True,
            "database_commonkey": "commonkey",
            "mongodb_uri": "",
            "log_level": "INFO",
            "vim_database": "db_name",
            "ro_database": "ro_db_name",
            "openmano_tenant": "mano",
            "certificates": f"cert1:{certificate_pem}",
        }
        self.harness.update_config(self.config)

    def test_config_changed_no_relations(
        self,
    ) -> NoReturn:
        """Test ingress resources without HTTP."""

        self.harness.charm.on.config_changed.emit()

        # Assertions
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
        self.assertTrue(
            all(
                relation in self.harness.charm.unit.status.message
                for relation in ["mongodb", "kafka"]
            )
        )

        # Disable ng-ro
        self.harness.update_config({"enable_ng_ro": False})
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
        self.assertTrue(
            all(
                relation in self.harness.charm.unit.status.message
                for relation in ["mysql"]
            )
        )

    def test_config_changed_non_leader(
        self,
    ) -> NoReturn:
        """Test ingress resources without HTTP."""
        self.harness.set_leader(is_leader=False)
        self.harness.charm.on.config_changed.emit()

        # Assertions
        self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)

    def test_with_relations_and_mongodb_config_ng(
        self,
    ) -> NoReturn:
        "Test with relations (ng-ro)"

        # Initializing the kafka relation
        kafka_relation_id = self.harness.add_relation("kafka", "kafka")
        self.harness.add_relation_unit(kafka_relation_id, "kafka/0")
        self.harness.update_relation_data(
            kafka_relation_id, "kafka/0", {"host": "kafka", "port": 9092}
        )

        # Initializing the mongodb config
        self.harness.update_config({"mongodb_uri": "mongodb://mongo:27017"})

        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_with_relations_ng(
        self,
    ) -> NoReturn:
        "Test with relations (ng-ro)"

        # Initializing the kafka relation
        kafka_relation_id = self.harness.add_relation("kafka", "kafka")
        self.harness.add_relation_unit(kafka_relation_id, "kafka/0")
        self.harness.update_relation_data(
            kafka_relation_id, "kafka/0", {"host": "kafka", "port": 9092}
        )

        # Initializing the mongo relation
        mongodb_relation_id = self.harness.add_relation("mongodb", "mongodb")
        self.harness.add_relation_unit(mongodb_relation_id, "mongodb/0")
        self.harness.update_relation_data(
            mongodb_relation_id,
            "mongodb/0",
            {"connection_string": "mongodb://mongo:27017"},
        )

        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_ng_exception_mongodb_relation_and_config(
        self,
    ) -> NoReturn:
        "Test NG-RO mongodb relation and config. Must fail"
        # Initializing the mongo relation
        mongodb_relation_id = self.harness.add_relation("mongodb", "mongodb")
        self.harness.add_relation_unit(mongodb_relation_id, "mongodb/0")
        self.harness.update_relation_data(
            mongodb_relation_id,
            "mongodb/0",
            {"connection_string": "mongodb://mongo:27017"},
        )

        # Initializing the mongodb config
        self.harness.update_config({"mongodb_uri": "mongodb://mongo:27017"})

        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)


if __name__ == "__main__":
    unittest.main()

# class TestCharm(unittest.TestCase):
#     """RO Charm unit tests."""

#     def setUp(self) -> NoReturn:
#         """Test setup"""
#         self.harness = Harness(RoCharm)
#         self.harness.set_leader(is_leader=True)
#         self.harness.begin()

#     def test_on_start_without_relations_ng_ro(self) -> NoReturn:
#         """Test installation without any relation."""
#         self.harness.charm.on.start.emit()

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("kafka", self.harness.charm.unit.status.message)
#         self.assertIn("mongodb", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))

#     def test_on_start_without_relations_no_ng_ro(self) -> NoReturn:
#         """Test installation without any relation."""
#         self.harness.update_config({"enable_ng_ro": False})

#         self.harness.charm.on.start.emit()

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("mysql", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relation"))

#     def test_on_start_with_relations_ng_ro(self) -> NoReturn:
#         """Test deployment with NG-RO."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "ro",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "ro",
#                             "containerPort": 9090,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {
#                         "OSMRO_LOG_LEVEL": "INFO",
#                         "OSMRO_MESSAGE_DRIVER": "kafka",
#                         "OSMRO_MESSAGE_HOST": "kafka",
#                         "OSMRO_MESSAGE_PORT": "9090",
#                         "OSMRO_DATABASE_DRIVER": "mongo",
#                         "OSMRO_DATABASE_URI": "mongodb://mongo",
#                         "OSMRO_DATABASE_COMMONKEY": "osm",
#                     },
#                     "kubernetes": {
#                         "startupProbe": {
#                             "exec": {"command": ["/usr/bin/pgrep", "python3"]},
#                             "initialDelaySeconds": 60,
#                             "timeoutSeconds": 5,
#                         },
#                         "readinessProbe": {
#                             "httpGet": {
#                                 "path": "/openmano/tenants",
#                                 "port": 9090,
#                             },
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                         "livenessProbe": {
#                             "httpGet": {
#                                 "path": "/openmano/tenants",
#                                 "port": 9090,
#                             },
#                             "initialDelaySeconds": 600,
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                     },
#                 }
#             ],
#             "kubernetesResources": {"ingressResources": []},
#         }

#         self.harness.charm.on.start.emit()

#         # Initializing the kafka relation
#         relation_id = self.harness.add_relation("kafka", "kafka")
#         self.harness.add_relation_unit(relation_id, "kafka/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "kafka/0",
#             {
#                 "host": "kafka",
#                 "port": "9090",
#             },
#         )

#         # Initializing the mongodb relation
#         relation_id = self.harness.add_relation("mongodb", "mongodb")
#         self.harness.add_relation_unit(relation_id, "mongodb/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mongodb/0",
#             {
#                 "connection_string": "mongodb://mongo",
#             },
#         )

#         # Verifying status
#         self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         pod_spec, _ = self.harness.get_pod_spec()

#         self.assertDictEqual(expected_result, pod_spec)

#     def test_on_start_with_relations_no_ng_ro(self) -> NoReturn:
#         """Test deployment with old RO."""
#         self.harness.update_config({"enable_ng_ro": False})

#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "ro",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "ro",
#                             "containerPort": 9090,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {
#                         "OSMRO_LOG_LEVEL": "INFO",
#                         "RO_DB_HOST": "mysql",
#                         "RO_DB_OVIM_HOST": "mysql",
#                         "RO_DB_PORT": 3306,
#                         "RO_DB_OVIM_PORT": 3306,
#                         "RO_DB_USER": "mano",
#                         "RO_DB_OVIM_USER": "mano",
#                         "RO_DB_PASSWORD": "manopw",
#                         "RO_DB_OVIM_PASSWORD": "manopw",
#                         "RO_DB_ROOT_PASSWORD": "rootmanopw",
#                         "RO_DB_OVIM_ROOT_PASSWORD": "rootmanopw",
#                         "RO_DB_NAME": "mano_db",
#                         "RO_DB_OVIM_NAME": "mano_vim_db",
#                         "OPENMANO_TENANT": "osm",
#                     },
#                     "kubernetes": {
#                         "startupProbe": {
#                             "exec": {"command": ["/usr/bin/pgrep", "python3"]},
#                             "initialDelaySeconds": 60,
#                             "timeoutSeconds": 5,
#                         },
#                         "readinessProbe": {
#                             "httpGet": {
#                                 "path": "/openmano/tenants",
#                                 "port": 9090,
#                             },
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                         "livenessProbe": {
#                             "httpGet": {
#                                 "path": "/openmano/tenants",
#                                 "port": 9090,
#                             },
#                             "initialDelaySeconds": 600,
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                     },
#                 }
#             ],
#             "kubernetesResources": {"ingressResources": []},
#         }

#         self.harness.charm.on.start.emit()

#         # Initializing the mysql relation
#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": 3306,
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootmanopw",
#             },
#         )

#         # Verifying status
#         self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         pod_spec, _ = self.harness.get_pod_spec()

#         self.assertDictEqual(expected_result, pod_spec)

#     def test_on_kafka_unit_relation_changed(self) -> NoReturn:
#         """Test to see if kafka relation is updated."""
#         self.harness.charm.on.start.emit()

#         relation_id = self.harness.add_relation("kafka", "kafka")
#         self.harness.add_relation_unit(relation_id, "kafka/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "kafka/0",
#             {
#                 "host": "kafka",
#                 "port": 9090,
#             },
#         )

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("mongodb", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relation"))

#     def test_on_mongodb_unit_relation_changed(self) -> NoReturn:
#         """Test to see if mongodb relation is updated."""
#         self.harness.charm.on.start.emit()

#         relation_id = self.harness.add_relation("mongodb", "mongodb")
#         self.harness.add_relation_unit(relation_id, "mongodb/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mongodb/0",
#             {
#                 "connection_string": "mongodb://mongo",
#             },
#         )

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("kafka", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relation"))

#     def test_on_mysql_unit_relation_changed(self) -> NoReturn:
#         """Test to see if mysql relation is updated."""
#         self.harness.charm.on.start.emit()

#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": 3306,
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootmanopw",
#             },
#         )

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("kafka", self.harness.charm.unit.status.message)
#         self.assertIn("mongodb", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))

#     def test_publish_ro_info(self) -> NoReturn:
#         """Test to see if ro relation is updated."""
#         expected_result = {
#             "host": "ro",
#             "port": "9090",
#         }

#         self.harness.charm.on.start.emit()

#         relation_id = self.harness.add_relation("ro", "lcm")
#         self.harness.add_relation_unit(relation_id, "lcm/0")
#         relation_data = self.harness.get_relation_data(relation_id, "ro")

#         self.assertDictEqual(expected_result, relation_data)


if __name__ == "__main__":
    unittest.main()
