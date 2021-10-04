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

import sys
from typing import NoReturn
import unittest

from charm import PolCharm
from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    """Pol Charm unit tests."""

    def setUp(self) -> NoReturn:
        """Test setup"""
        self.image_info = sys.modules["oci_image"].OCIImageResource().fetch()
        self.harness = Harness(PolCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        self.config = {
            "log_level": "INFO",
            "mongodb_uri": "",
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
        "Test with relations and mongodb config (internal)"
        self.initialize_mysql_relation()
        self.initialize_kafka_relation()
        self.initialize_mongo_config()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_with_relations(
        self,
    ) -> NoReturn:
        "Test with relations (internal)"
        self.initialize_kafka_relation()
        self.initialize_mongo_relation()
        self.initialize_mysql_relation()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_exception_mongodb_relation_and_config(
        self,
    ) -> NoReturn:
        "Test with relation and config for Mongodb. Must fail"
        self.initialize_mongo_relation()
        self.initialize_mongo_config()
        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_mysql_config_success(self):
        self.initialize_kafka_relation()
        self.initialize_mongo_relation()
        self.initialize_mysql_config()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_mysql_config_wrong_value(self):
        self.initialize_kafka_relation()
        self.initialize_mongo_relation()
        self.initialize_mysql_config(uri="wrong_uri")
        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
        self.assertIn(
            "mysql_uri is not properly formed",
            self.harness.charm.unit.status.message,
        )

    def test_mysql_config_and_relation(self):
        self.initialize_mysql_relation()
        self.initialize_mysql_config()
        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
        # import pdb; pdb.set_trace()
        self.assertIn(
            "Mysql data cannot be provided via config and relation",
            self.harness.charm.unit.status.message,
        )

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

    def initialize_mysql_config(self, uri=None):
        self.harness.update_config(
            {"mysql_uri": uri or "mysql://user:pass@mysql-host:3306/database"}
        )

    def initialize_mysql_relation(self):
        mongodb_relation_id = self.harness.add_relation("mysql", "mysql")
        self.harness.add_relation_unit(mongodb_relation_id, "mysql/0")
        self.harness.update_relation_data(
            mongodb_relation_id,
            "mysql/0",
            {
                "user": "user",
                "password": "pass",
                "host": "host",
                "port": "1234",
                "database": "pol",
                "root_password": "root_password",
            },
        )


if __name__ == "__main__":
    unittest.main()


# class TestCharm(unittest.TestCase):
#     """POL Charm unit tests."""

#     def setUp(self) -> NoReturn:
#         """Test setup"""
#         self.harness = Harness(PolCharm)
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
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relations"))

#     def test_on_start_with_relations(self) -> NoReturn:
#         """Test deployment without keystone."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "pol",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "pol",
#                             "containerPort": 80,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {
#                         "ALLOW_ANONYMOUS_LOGIN": "yes",
#                         "OSMPOL_GLOBAL_LOGLEVEL": "INFO",
#                         "OSMPOL_MESSAGE_HOST": "kafka",
#                         "OSMPOL_MESSAGE_DRIVER": "kafka",
#                         "OSMPOL_MESSAGE_PORT": 9092,
#                         "OSMPOL_DATABASE_DRIVER": "mongo",
#                         "OSMPOL_DATABASE_URI": "mongodb://mongo:27017",
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

#         # Checking if kafka data is stored
#         self.assertEqual(self.harness.charm.state.message_host, "kafka")
#         self.assertEqual(self.harness.charm.state.message_port, 9092)

#         # Checking if mongodb data is stored
#         self.assertEqual(self.harness.charm.state.database_uri, "mongodb://mongo:27017")

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
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relation"))

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
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relation"))


# if __name__ == "__main__":
#     unittest.main()
