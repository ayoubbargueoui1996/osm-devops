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


class KeystoneProvides(Endpoint):
    @when("endpoint.{endpoint_name}.joined")
    def _joined(self):
        set_flag(self.expand_name("{endpoint_name}.joined"))

    @when("endpoint.{endpoint_name}.changed")
    def _changed(self):
        set_flag(self.expand_name("{endpoint_name}.ready"))

    @when("endpoint.{endpoint_name}.departed")
    def _departed(self):
        set_flag(self.expand_name("{endpoint_name}.departed"))
        clear_flag(self.expand_name("{endpoint_name}.joined"))

    def publish_info(
        self,
        host,
        port,
        keystone_db_password,
        region_id,
        user_domain_name,
        project_domain_name,
        admin_username,
        admin_password,
        admin_project_name,
        username,
        password,
        service,
    ):
        for relation in self.relations:
            relation.to_publish["host"] = host
            relation.to_publish["port"] = port
            relation.to_publish["keystone_db_password"] = keystone_db_password
            relation.to_publish["region_id"] = region_id
            relation.to_publish["user_domain_name"] = user_domain_name
            relation.to_publish["project_domain_name"] = project_domain_name
            relation.to_publish["admin_username"] = admin_username
            relation.to_publish["admin_password"] = admin_password
            relation.to_publish["admin_project_name"] = admin_project_name
            relation.to_publish["username"] = username
            relation.to_publish["password"] = password
            relation.to_publish["service"] = service

    def mark_complete(self):
        clear_flag(self.expand_name("{endpoint_name}.joined"))
