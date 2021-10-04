# Copyright 2020 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
from charms.reactive import Endpoint
from charms.reactive import when
from charms.reactive import set_flag, clear_flag


class KeystoneRequires(Endpoint):
    @when("endpoint.{endpoint_name}.joined")
    def _joined(self):
        set_flag(self.expand_name("{endpoint_name}.joined"))

    @when("endpoint.{endpoint_name}.changed")
    def _changed(self):
        if len(self.keystones()) > 0:
            set_flag(self.expand_name("{endpoint_name}.ready"))
        else:
            clear_flag(self.expand_name("{endpoint_name}.ready"))

    @when("endpoint.{endpoint_name}.departed")
    def _departed(self):
        set_flag(self.expand_name("{endpoint_name}.departed"))
        clear_flag(self.expand_name("{endpoint_name}.joined"))
        clear_flag(self.expand_name("{endpoint_name}.ready"))

    def keystones(self):
        """
        Return Keystone Data:
        [{
            'host': <host>,
            'port': <port>,
            'keystone_db_password: <keystone_db_password>,
            'region_id: <region_id>,
            'admin_username: <admin_username>,
            'admin_password: <admin_password>,
            'admin_project_name: <admin_project_name>,
            'username: <username>,
            'password: <password>,
            'service: <service>
        }]
        """
        keystones = []
        for relation in self.relations:
            for unit in relation.units:
                data = {
                    "host": unit.received["host"],
                    "port": unit.received["port"],
                    "keystone_db_password": unit.received["keystone_db_password"],
                    "region_id": unit.received["region_id"],
                    "user_domain_name": unit.received["user_domain_name"],
                    "project_domain_name": unit.received["project_domain_name"],
                    "admin_username": unit.received["admin_username"],
                    "admin_password": unit.received["admin_password"],
                    "admin_project_name": unit.received["admin_project_name"],
                    "username": unit.received["username"],
                    "password": unit.received["password"],
                    "service": unit.received["service"],
                }
                if all(data.values()):
                    keystones.append(data)
        return keystones
