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


from charm import KeystoneCharm
from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    """Keystone Charm unit tests."""

    def setUp(self) -> NoReturn:
        """Test setup"""
        self.image_info = sys.modules["oci_image"].OCIImageResource().fetch()
        self.harness = Harness(KeystoneCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        self.config = {
            "region_id": "str",
            "keystone_db_password": "str",
            "mysql_host": "",
            "mysql_port": 3306,
            "mysql_root_password": "manopw",
            "admin_username": "str",
            "admin_password": "str",
            "admin_project": "str",
            "service_username": "str",
            "service_password": "str",
            "service_project": "str",
            "user_domain_name": "str",
            "project_domain_name": "str",
            "token_expiration": 10,
            "max_file_size": 1,
            "site_url": "http://keystone.com",
            "ldap_enabled": False,
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

    def test_with_config(self) -> NoReturn:
        "Test with mysql config"
        self.initialize_mysql_config()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_with_relations(
        self,
    ) -> NoReturn:
        "Test with relations"
        self.initialize_mysql_relation()
        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_exception_mysql_relation_and_config(
        self,
    ) -> NoReturn:
        "Test with relations and config. Must throw exception"
        self.initialize_mysql_config()
        self.initialize_mysql_relation()
        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def initialize_mysql_config(self):
        self.harness.update_config(
            {
                "mysql_host": "mysql",
                "mysql_port": 3306,
                "mysql_root_password": "manopw",
            }
        )

    def initialize_mysql_relation(self):
        relation_id = self.harness.add_relation("db", "mysql")
        self.harness.add_relation_unit(relation_id, "mysql/0")
        self.harness.update_relation_data(
            relation_id,
            "mysql/0",
            {
                "host": "mysql",
                "port": 3306,
                "user": "mano",
                "password": "manopw",
                "root_password": "rootmanopw",
            },
        )


if __name__ == "__main__":
    unittest.main()


# class TestCharm(unittest.TestCase):
#     """Prometheus Charm unit tests."""

#     def setUp(self) -> NoReturn:
#         """Test setup"""
#         self.image_info = sys.modules["oci_image"].OCIImageResource().fetch()
#         self.harness = Harness(KeystoneCharm)
#         self.harness.set_leader(is_leader=True)
#         self.harness.begin()
#         self.config = {
#             "enable_ng_ro": True,
#             "database_commonkey": "commonkey",
#             "log_level": "INFO",
#             "vim_database": "db_name",
#             "ro_database": "ro_db_name",
#             "openmano_tenant": "mano",
#         }

#     def test_config_changed_no_relations(
#         self,
#     ) -> NoReturn:
#         """Test ingress resources without HTTP."""

#         self.harness.charm.on.config_changed.emit()

#         # Assertions
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
#         self.assertTrue(
#             all(
#                 relation in self.harness.charm.unit.status.message
#                 for relation in ["mongodb", "kafka"]
#             )
#         )

#         # Disable ng-ro
#         self.harness.update_config({"enable_ng_ro": False})
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
#         self.assertTrue(
#             all(
#                 relation in self.harness.charm.unit.status.message
#                 for relation in ["mysql"]
#             )
#         )

#     def test_config_changed_non_leader(
#         self,
#     ) -> NoReturn:
#         """Test ingress resources without HTTP."""
#         self.harness.set_leader(is_leader=False)
#         self.harness.charm.on.config_changed.emit()

#         # Assertions
#         self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)

#     def test_with_relations_ng(
#         self,
#     ) -> NoReturn:
#         "Test with relations (ng-ro)"

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

#         self.harness.charm.on.config_changed.emit()

#         # Verifying status
#         self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)


# if __name__ == "__main__":
#     unittest.main()
