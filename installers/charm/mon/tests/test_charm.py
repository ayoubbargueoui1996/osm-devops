#!/usr/bin/env python3
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

import base64
import sys
from typing import NoReturn
import unittest

from charm import MonCharm
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
        self.image_info = sys.modules["oci_image"].OCIImageResource().fetch()
        self.harness = Harness(MonCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        self.config = {
            "vca_host": "192.168.0.13",
            "vca_user": "admin",
            "vca_secret": "admin",
            "vca_cacert": "cacert",
            "database_commonkey": "commonkey",
            "mongodb_uri": "",
            "log_level": "INFO",
            "openstack_default_granularity": 10,
            "global_request_timeout": 10,
            "collector_interval": 30,
            "evaluator_interval": 30,
            "keystone_enabled": True,
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
                for relation in ["mongodb", "kafka", "prometheus", "keystone"]
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

    def test_with_relations_and_mongodb_config(
        self,
    ) -> NoReturn:
        "Test with relations (internal)"
        self.initialize_kafka_relation()
        self.initialize_mongo_config()
        self.initialize_prometheus_relation()
        self.initialize_keystone_relation()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_with_relations(
        self,
    ) -> NoReturn:
        "Test with relations (internal)"
        self.initialize_kafka_relation()
        self.initialize_mongo_relation()
        self.initialize_prometheus_relation()
        self.initialize_keystone_relation()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_exception_mongodb_relation_and_config(
        self,
    ) -> NoReturn:
        "Test with relations and config for mongodb. Must fail"
        self.initialize_mongo_relation()
        self.initialize_mongo_config()
        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def initialize_kafka_relation(self):
        kafka_relation_id = self.harness.add_relation("kafka", "kafka")
        self.harness.add_relation_unit(kafka_relation_id, "kafka/0")
        self.harness.update_relation_data(
            kafka_relation_id, "kafka/0", {"host": "kafka", "port": 9092}
        )

    def initialize_mongo_config(self):
        self.harness.update_config({"mongodb_uri": "mongodb://mongo:27017"})

    def initialize_mongo_relation(self):
        mongodb_relation_id = self.harness.add_relation("mongodb", "mongodb")
        self.harness.add_relation_unit(mongodb_relation_id, "mongodb/0")
        self.harness.update_relation_data(
            mongodb_relation_id,
            "mongodb/0",
            {"connection_string": "mongodb://mongo:27017"},
        )

    def initialize_prometheus_relation(self):
        prometheus_relation_id = self.harness.add_relation("prometheus", "prometheus")
        self.harness.add_relation_unit(prometheus_relation_id, "prometheus/0")
        self.harness.update_relation_data(
            prometheus_relation_id,
            "prometheus",
            {"hostname": "prometheus", "port": 9090},
        )

    def initialize_keystone_relation(self):
        keystone_relation_id = self.harness.add_relation("keystone", "keystone")
        self.harness.add_relation_unit(keystone_relation_id, "keystone/0")
        self.harness.update_relation_data(
            keystone_relation_id,
            "keystone",
            {
                "host": "host",
                "port": 5000,
                "user_domain_name": "ud",
                "project_domain_name": "pd",
                "username": "u",
                "password": "p",
                "service": "s",
                "keystone_db_password": "something",
                "region_id": "something",
                "admin_username": "something",
                "admin_password": "something",
                "admin_project_name": "something",
            },
        )


if __name__ == "__main__":
    unittest.main()


# class TestCharm(unittest.TestCase):
#     """MON Charm unit tests."""

#     def setUp(self) -> NoReturn:
#         """Test setup"""
#         self.harness = Harness(MonCharm)
#         self.harness.set_leader(is_leader=True)
#         self.harness.begin()

#     def test_on_start_without_relations(self) -> NoReturn:
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
#         self.assertIn("prometheus", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))

#     def test_on_start_with_relations(self) -> NoReturn:
#         """Test deployment without keystone."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "mon",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "mon",
#                             "containerPort": 8000,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {
#                         "ALLOW_ANONYMOUS_LOGIN": "yes",
#                         "OSMMON_OPENSTACK_DEFAULT_GRANULARITY": 300,
#                         "OSMMON_GLOBAL_REQUEST_TIMEOUT": 10,
#                         "OSMMON_GLOBAL_LOGLEVEL": "INFO",
#                         "OSMMON_COLLECTOR_INTERVAL": 30,
#                         "OSMMON_EVALUATOR_INTERVAL": 30,
#                         "OSMMON_MESSAGE_DRIVER": "kafka",
#                         "OSMMON_MESSAGE_HOST": "kafka",
#                         "OSMMON_MESSAGE_PORT": 9092,
#                         "OSMMON_DATABASE_DRIVER": "mongo",
#                         "OSMMON_DATABASE_URI": "mongodb://mongo:27017",
#                         "OSMMON_DATABASE_COMMONKEY": "osm",
#                         "OSMMON_PROMETHEUS_URL": "http://prometheus:9090",
#                         "OSMMON_VCA_HOST": "admin",
#                         "OSMMON_VCA_USER": "admin",
#                         "OSMMON_VCA_SECRET": "secret",
#                         "OSMMON_VCA_CACERT": "",
#                     },
#                 }
#             ],
#             "kubernetesResources": {"ingressResources": []},
#         }

#         self.harness.charm.on.start.emit()

#         # Check if kafka datastore is initialized
#         self.assertIsNone(self.harness.charm.state.message_host)
#         self.assertIsNone(self.harness.charm.state.message_port)

#         # Check if mongodb datastore is initialized
#         self.assertIsNone(self.harness.charm.state.database_uri)

#         # Check if prometheus datastore is initialized
#         self.assertIsNone(self.harness.charm.state.prometheus_host)
#         self.assertIsNone(self.harness.charm.state.prometheus_port)

#         # Initializing the kafka relation
#         kafka_relation_id = self.harness.add_relation("kafka", "kafka")
#         self.harness.add_relation_unit(kafka_relation_id, "kafka/0")
#         self.harness.update_relation_data(
#             kafka_relation_id, "kafka/0", {"host": "kafka", "port": 9092}
#         )

#         # Initializing the mongo relation
#         mongodb_relation_id = self.harness.add_relation("mongodb", "mongodb")
#         self.harness.add_relation_unit(mongodb_relation_id, "mongodb/0")
#         self.harness.update_relation_data(
#             mongodb_relation_id,
#             "mongodb/0",
#             {"connection_string": "mongodb://mongo:27017"},
#         )

#         # Initializing the prometheus relation
#         prometheus_relation_id = self.harness.add_relation("prometheus", "prometheus")
#         self.harness.add_relation_unit(prometheus_relation_id, "prometheus/0")
#         self.harness.update_relation_data(
#             prometheus_relation_id,
#             "prometheus",
#             {"hostname": "prometheus", "port": 9090},
#         )

#         # Checking if kafka data is stored
#         self.assertEqual(self.harness.charm.state.message_host, "kafka")
#         self.assertEqual(self.harness.charm.state.message_port, 9092)

#         # Checking if mongodb data is stored
#         self.assertEqual(self.harness.charm.state.database_uri, "mongodb://mongo:27017")

#         # Checking if prometheus data is stored
#         self.assertEqual(self.harness.charm.state.prometheus_host, "prometheus")
#         self.assertEqual(self.harness.charm.state.prometheus_port, 9090)

#         # Verifying status
#         self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         pod_spec, _ = self.harness.get_pod_spec()

#         self.assertDictEqual(expected_result, pod_spec)

#     def test_on_kafka_unit_relation_changed(self) -> NoReturn:
#         """Test to see if kafka relation is updated."""
#         self.harness.charm.on.start.emit()

#         self.assertIsNone(self.harness.charm.state.message_host)
#         self.assertIsNone(self.harness.charm.state.message_port)

#         relation_id = self.harness.add_relation("kafka", "kafka")
#         self.harness.add_relation_unit(relation_id, "kafka/0")
#         self.harness.update_relation_data(
#             relation_id, "kafka/0", {"host": "kafka", "port": 9092}
#         )

#         self.assertEqual(self.harness.charm.state.message_host, "kafka")
#         self.assertEqual(self.harness.charm.state.message_port, 9092)

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertNotIn("kafka", self.harness.charm.unit.status.message)
#         self.assertIn("mongodb", self.harness.charm.unit.status.message)
#         self.assertIn("prometheus", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))

#     def test_on_mongodb_unit_relation_changed(self) -> NoReturn:
#         """Test to see if mongodb relation is updated."""
#         self.harness.charm.on.start.emit()

#         self.assertIsNone(self.harness.charm.state.database_uri)

#         relation_id = self.harness.add_relation("mongodb", "mongodb")
#         self.harness.add_relation_unit(relation_id, "mongodb/0")
#         self.harness.update_relation_data(
#             relation_id, "mongodb/0", {"connection_string": "mongodb://mongo:27017"}
#         )

#         self.assertEqual(self.harness.charm.state.database_uri, "mongodb://mongo:27017")

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("kafka", self.harness.charm.unit.status.message)
#         self.assertNotIn("mongodb", self.harness.charm.unit.status.message)
#         self.assertIn("prometheus", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))

#     def test_on_prometheus_unit_relation_changed(self) -> NoReturn:
#         """Test to see if prometheus relation is updated."""
#         self.harness.charm.on.start.emit()

#         self.assertIsNone(self.harness.charm.state.prometheus_host)
#         self.assertIsNone(self.harness.charm.state.prometheus_port)

#         relation_id = self.harness.add_relation("prometheus", "prometheus")
#         self.harness.add_relation_unit(relation_id, "prometheus/0")
#         self.harness.update_relation_data(
#             relation_id, "prometheus", {"hostname": "prometheus", "port": 9090}
#         )

#         self.assertEqual(self.harness.charm.state.prometheus_host, "prometheus")
#         self.assertEqual(self.harness.charm.state.prometheus_port, 9090)

#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("kafka", self.harness.charm.unit.status.message)
#         self.assertIn("mongodb", self.harness.charm.unit.status.message)
#         self.assertNotIn("prometheus", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))


# if __name__ == "__main__":
#     unittest.main()
