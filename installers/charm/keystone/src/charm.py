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

# pylint: disable=E0213


from datetime import datetime
from ipaddress import ip_network
import json
import logging
from typing import List, NoReturn, Optional, Tuple
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from ops.main import main
from opslib.osm.charm import CharmedOsmBase, RelationsMissing
from opslib.osm.interfaces.keystone import KeystoneServer
from opslib.osm.interfaces.mysql import MysqlClient
from opslib.osm.pod import (
    ContainerV3Builder,
    FilesV3Builder,
    IngressResourceV3Builder,
    PodSpecV3Builder,
)
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)


REQUIRED_SETTINGS = ["token_expiration"]

# This is hardcoded in the keystone container script
DATABASE_NAME = "keystone"

# We expect the keystone container to use the default port
PORT = 5000

# Number of keys need might need to be adjusted in the future
NUMBER_FERNET_KEYS = 2
NUMBER_CREDENTIAL_KEYS = 2

# Path for keys
CREDENTIAL_KEYS_PATH = "/etc/keystone/credential-keys"
FERNET_KEYS_PATH = "/etc/keystone/fernet-keys"


class ConfigModel(ModelValidator):
    region_id: str
    keystone_db_password: str
    admin_username: str
    admin_password: str
    admin_project: str
    service_username: str
    service_password: str
    service_project: str
    user_domain_name: str
    project_domain_name: str
    token_expiration: int
    max_file_size: int
    site_url: Optional[str]
    ingress_whitelist_source_range: Optional[str]
    tls_secret_name: Optional[str]
    mysql_host: Optional[str]
    mysql_port: Optional[int]
    mysql_root_password: Optional[str]

    @validator("max_file_size")
    def validate_max_file_size(cls, v):
        if v < 0:
            raise ValueError("value must be equal or greater than 0")
        return v

    @validator("site_url")
    def validate_site_url(cls, v):
        if v:
            parsed = urlparse(v)
            if not parsed.scheme.startswith("http"):
                raise ValueError("value must start with http")
        return v

    @validator("ingress_whitelist_source_range")
    def validate_ingress_whitelist_source_range(cls, v):
        if v:
            ip_network(v)
        return v

    @validator("mysql_port")
    def validate_mysql_port(cls, v):
        if v and (v <= 0 or v >= 65535):
            raise ValueError("Mysql port out of range")
        return v


class ConfigLdapModel(ModelValidator):
    ldap_enabled: bool
    ldap_authentication_domain_name: Optional[str]
    ldap_url: Optional[str]
    ldap_bind_user: Optional[str]
    ldap_bind_password: Optional[str]
    ldap_chase_referrals: Optional[str]
    ldap_page_size: Optional[int]
    ldap_user_tree_dn: Optional[str]
    ldap_user_objectclass: Optional[str]
    ldap_user_id_attribute: Optional[str]
    ldap_user_name_attribute: Optional[str]
    ldap_user_pass_attribute: Optional[str]
    ldap_user_filter: Optional[str]
    ldap_user_enabled_attribute: Optional[str]
    ldap_user_enabled_mask: Optional[int]
    ldap_user_enabled_default: Optional[str]
    ldap_user_enabled_invert: Optional[bool]
    ldap_group_objectclass: Optional[str]
    ldap_group_tree_dn: Optional[str]
    ldap_use_starttls: Optional[bool]
    ldap_tls_cacert_base64: Optional[str]
    ldap_tls_req_cert: Optional[str]

    @validator
    def validate_ldap_user_enabled_default(cls, v):
        if v:
            if v not in ["true", "false"]:
                raise ValueError('must be equal to "true" or "false"')
        return v


class KeystoneCharm(CharmedOsmBase):
    def __init__(self, *args) -> NoReturn:
        super().__init__(*args, oci_image="image")
        self.state.set_default(fernet_keys=None)
        self.state.set_default(credential_keys=None)
        self.state.set_default(keys_timestamp=0)

        self.keystone_server = KeystoneServer(self, "keystone")
        self.mysql_client = MysqlClient(self, "db")
        self.framework.observe(self.on["db"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["db"].relation_broken, self.configure_pod)

        self.framework.observe(
            self.on["keystone"].relation_joined, self._publish_keystone_info
        )

    def _publish_keystone_info(self, event):
        if self.unit.is_leader():
            config = ConfigModel(**dict(self.config))
            self.keystone_server.publish_info(
                host=f"http://{self.app.name}:{PORT}/v3",
                port=PORT,
                user_domain_name=config.user_domain_name,
                project_domain_name=config.project_domain_name,
                username=config.service_username,
                password=config.service_password,
                service=config.service_project,
                keystone_db_password=config.keystone_db_password,
                region_id=config.region_id,
                admin_username=config.admin_username,
                admin_password=config.admin_password,
                admin_project_name=config.admin_project,
            )

    def _check_missing_dependencies(self, config: ConfigModel):
        missing_relations = []
        if not config.mysql_host and self.mysql_client.is_missing_data_in_unit():
            missing_relations.append("mysql")
        if missing_relations:
            raise RelationsMissing(missing_relations)

    def _validate_mysql_config(self, config: ConfigModel):
        invalid_values = []
        if not config.mysql_root_password:
            invalid_values.append("Mysql root password must be provided")

        if invalid_values:
            raise ValueError("Invalid values: " + ", ".join(invalid_values))

    def _generate_keys(self) -> Tuple[List[str], List[str]]:
        """Generating new fernet tokens.

        Returns:
            Tuple[List[str], List[str]]: contains two lists of strings. First
                                         list contains strings that represent
                                         the keys for fernet and the second
                                         list contains strins that represent
                                         the keys for credentials.
        """
        fernet_keys = [
            Fernet.generate_key().decode() for _ in range(NUMBER_FERNET_KEYS)
        ]
        credential_keys = [
            Fernet.generate_key().decode() for _ in range(NUMBER_CREDENTIAL_KEYS)
        ]

        return (fernet_keys, credential_keys)

    def _get_keys(self):
        keys_timestamp = self.state.keys_timestamp
        if fernet_keys := self.state.fernet_keys:
            fernet_keys = json.loads(fernet_keys)

        if credential_keys := self.state.credential_keys:
            credential_keys = json.loads(credential_keys)

        now = datetime.now().timestamp()
        token_expiration = self.config["token_expiration"]

        valid_keys = (now - keys_timestamp) < token_expiration
        if not credential_keys or not fernet_keys or not valid_keys:
            fernet_keys, credential_keys = self._generate_keys()
            self.state.fernet_keys = json.dumps(fernet_keys)
            self.state.credential_keys = json.dumps(credential_keys)
            self.state.keys_timestamp = now
        return credential_keys, fernet_keys

    def _build_files(self, config: ConfigModel):
        credentials_files_builder = FilesV3Builder()
        fernet_files_builder = FilesV3Builder()

        credential_keys, fernet_keys = self._get_keys()

        for (key_id, value) in enumerate(credential_keys):
            credentials_files_builder.add_file(str(key_id), value)
        for (key_id, value) in enumerate(fernet_keys):
            fernet_files_builder.add_file(str(key_id), value)
        return credentials_files_builder.build(), fernet_files_builder.build()

    def build_pod_spec(self, image_info):
        # Validate config
        config = ConfigModel(**dict(self.config))
        config_ldap = ConfigLdapModel(**dict(self.config))

        if config.mysql_host and not self.mysql_client.is_missing_data_in_unit():
            raise Exception("Mysql data cannot be provided via config and relation")

        if config.mysql_host:
            self._validate_mysql_config(config)

        # Check relations
        self._check_missing_dependencies(config)

        # Create Builder for the PodSpec
        pod_spec_builder = PodSpecV3Builder()

        # Build Container
        container_builder = ContainerV3Builder(self.app.name, image_info)
        container_builder.add_port(name=self.app.name, port=PORT)

        # Build files
        credential_files, fernet_files = self._build_files(config)
        container_builder.add_volume_config(
            "credential-keys", CREDENTIAL_KEYS_PATH, credential_files
        )
        container_builder.add_volume_config(
            "fernet-keys", FERNET_KEYS_PATH, fernet_files
        )
        container_builder.add_envs(
            {
                "DB_HOST": config.mysql_host or self.mysql_client.host,
                "DB_PORT": config.mysql_port or self.mysql_client.port,
                "ROOT_DB_USER": "root",
                "ROOT_DB_PASSWORD": config.mysql_root_password
                or self.mysql_client.root_password,
                "KEYSTONE_DB_PASSWORD": config.keystone_db_password,
                "REGION_ID": config.region_id,
                "KEYSTONE_HOST": self.app.name,
                "ADMIN_USERNAME": config.admin_username,
                "ADMIN_PASSWORD": config.admin_password,
                "ADMIN_PROJECT": config.admin_project,
                "SERVICE_USERNAME": config.service_username,
                "SERVICE_PASSWORD": config.service_password,
                "SERVICE_PROJECT": config.service_project,
            }
        )

        if config_ldap.ldap_enabled:
            container_builder.add_envs(
                {
                    "LDAP_AUTHENTICATION_DOMAIN_NAME": config_ldap.ldap_authentication_domain_name,
                    "LDAP_URL": config_ldap.ldap_url,
                    "LDAP_PAGE_SIZE": config_ldap.ldap_page_size,
                    "LDAP_USER_OBJECTCLASS": config_ldap.ldap_user_objectclass,
                    "LDAP_USER_ID_ATTRIBUTE": config_ldap.ldap_user_id_attribute,
                    "LDAP_USER_NAME_ATTRIBUTE": config_ldap.ldap_user_name_attribute,
                    "LDAP_USER_PASS_ATTRIBUTE": config_ldap.ldap_user_pass_attribute,
                    "LDAP_USER_ENABLED_MASK": config_ldap.ldap_user_enabled_mask,
                    "LDAP_USER_ENABLED_DEFAULT": config_ldap.ldap_user_enabled_default,
                    "LDAP_USER_ENABLED_INVERT": config_ldap.ldap_user_enabled_invert,
                    "LDAP_GROUP_OBJECTCLASS": config_ldap.ldap_group_objectclass,
                }
            )
            if config_ldap.ldap_bind_user:
                container_builder.add_envs(
                    {"LDAP_BIND_USER": config_ldap.ldap_bind_user}
                )

            if config_ldap.ldap_bind_password:
                container_builder.add_envs(
                    {"LDAP_BIND_PASSWORD": config_ldap.ldap_bind_password}
                )

            if config_ldap.ldap_user_tree_dn:
                container_builder.add_envs(
                    {"LDAP_USER_TREE_DN": config_ldap.ldap_user_tree_dn}
                )

            if config_ldap.ldap_user_filter:
                container_builder.add_envs(
                    {"LDAP_USER_FILTER": config_ldap.ldap_user_filter}
                )

            if config_ldap.ldap_user_enabled_attribute:
                container_builder.add_envs(
                    {
                        "LDAP_USER_ENABLED_ATTRIBUTE": config_ldap.ldap_user_enabled_attribute
                    }
                )

            if config_ldap.ldap_chase_referrals:
                container_builder.add_envs(
                    {"LDAP_CHASE_REFERRALS": config_ldap.ldap_chase_referrals}
                )

            if config_ldap.ldap_group_tree_dn:
                container_builder.add_envs(
                    {"LDAP_GROUP_TREE_DN": config_ldap.ldap_group_tree_dn}
                )

            if config_ldap.ldap_use_starttls:
                container_builder.add_envs(
                    {
                        "LDAP_USE_STARTTLS": config_ldap.ldap_use_starttls,
                        "LDAP_TLS_CACERT_BASE64": config_ldap.ldap_tls_cacert_base64,
                        "LDAP_TLS_REQ_CERT": config_ldap.ldap_tls_req_cert,
                    }
                )
        container = container_builder.build()

        # Add container to pod spec
        pod_spec_builder.add_container(container)

        # Add ingress resources to pod spec if site url exists
        if config.site_url:
            parsed = urlparse(config.site_url)
            annotations = {
                "nginx.ingress.kubernetes.io/proxy-body-size": "{}".format(
                    str(config.max_file_size) + "m"
                    if config.max_file_size > 0
                    else config.max_file_size
                ),
            }
            ingress_resource_builder = IngressResourceV3Builder(
                f"{self.app.name}-ingress", annotations
            )

            if config.ingress_whitelist_source_range:
                annotations[
                    "nginx.ingress.kubernetes.io/whitelist-source-range"
                ] = config.ingress_whitelist_source_range

            if parsed.scheme == "https":
                ingress_resource_builder.add_tls(
                    [parsed.hostname], config.tls_secret_name
                )
            else:
                annotations["nginx.ingress.kubernetes.io/ssl-redirect"] = "false"

            ingress_resource_builder.add_rule(parsed.hostname, self.app.name, PORT)
            ingress_resource = ingress_resource_builder.build()
            pod_spec_builder.add_ingress_resource(ingress_resource)
        return pod_spec_builder.build()


if __name__ == "__main__":
    main(KeystoneCharm)

# LOGGER = logging.getLogger(__name__)


# class ConfigurePodEvent(EventBase):
#     """Configure Pod event"""

#     pass


# class KeystoneEvents(CharmEvents):
#     """Keystone Events"""

#     configure_pod = EventSource(ConfigurePodEvent)

# class KeystoneCharm(CharmBase):
#     """Keystone K8s Charm"""

#     state = StoredState()
#     on = KeystoneEvents()

#     def __init__(self, *args) -> NoReturn:
#         """Constructor of the Charm object.
#         Initializes internal state and register events it can handle.
#         """
#         super().__init__(*args)
#         self.state.set_default(db_host=None)
#         self.state.set_default(db_port=None)
#         self.state.set_default(db_user=None)
#         self.state.set_default(db_password=None)
#         self.state.set_default(pod_spec=None)
#         self.state.set_default(fernet_keys=None)
#         self.state.set_default(credential_keys=None)
#         self.state.set_default(keys_timestamp=0)

#         # Register all of the events we want to observe
#         self.framework.observe(self.on.config_changed, self.configure_pod)
#         self.framework.observe(self.on.start, self.configure_pod)
#         self.framework.observe(self.on.upgrade_charm, self.configure_pod)
#         self.framework.observe(self.on.leader_elected, self.configure_pod)
#         self.framework.observe(self.on.update_status, self.configure_pod)

#         # Registering custom internal events
#         self.framework.observe(self.on.configure_pod, self.configure_pod)

#         # Register relation events
#         self.framework.observe(
#             self.on.db_relation_changed, self._on_db_relation_changed
#         )
#         self.framework.observe(
#             self.on.db_relation_broken, self._on_db_relation_broken
#         )
#         self.framework.observe(
#             self.on.keystone_relation_joined, self._publish_keystone_info
#         )

#     def _publish_keystone_info(self, event: EventBase) -> NoReturn:
#         """Publishes keystone information for NBI usage through the keystone
#            relation.

#         Args:
#             event (EventBase): Keystone relation event to update NBI.
#         """
#         config = self.model.config
#         rel_data = {
#             "host": f"http://{self.app.name}:{KEYSTONE_PORT}/v3",
#             "port": str(KEYSTONE_PORT),
#             "keystone_db_password": config["keystone_db_password"],
#             "region_id": config["region_id"],
#             "user_domain_name": config["user_domain_name"],
#             "project_domain_name": config["project_domain_name"],
#             "admin_username": config["admin_username"],
#             "admin_password": config["admin_password"],
#             "admin_project_name": config["admin_project"],
#             "username": config["service_username"],
#             "password": config["service_password"],
#             "service": config["service_project"],
#         }
#         for k, v in rel_data.items():
#             event.relation.data[self.model.unit][k] = v

#     def _on_db_relation_changed(self, event: EventBase) -> NoReturn:
#         """Reads information about the DB relation, in order for keystone to
#            access it.

#         Args:
#             event (EventBase): DB relation event to access database
#                                information.
#         """
#         if not event.unit in event.relation.data:
#             return
#         relation_data = event.relation.data[event.unit]
#         db_host = relation_data.get("host")
#         db_port = int(relation_data.get("port", 3306))
#         db_user = "root"
#         db_password = relation_data.get("root_password")

#         if (
#             db_host
#             and db_port
#             and db_user
#             and db_password
#             and (
#                 self.state.db_host != db_host
#                 or self.state.db_port != db_port
#                 or self.state.db_user != db_user
#                 or self.state.db_password != db_password
#             )
#         ):
#             self.state.db_host = db_host
#             self.state.db_port = db_port
#             self.state.db_user = db_user
#             self.state.db_password = db_password
#             self.on.configure_pod.emit()


#     def _on_db_relation_broken(self, event: EventBase) -> NoReturn:
#         """Clears data from db relation.

#         Args:
#             event (EventBase): DB relation event.

#         """
#         self.state.db_host = None
#         self.state.db_port = None
#         self.state.db_user = None
#         self.state.db_password = None
#         self.on.configure_pod.emit()

#     def _check_settings(self) -> str:
#         """Check if there any settings missing from Keystone configuration.

#         Returns:
#             str: Information about the problems found (if any).
#         """
#         problems = []
#         config = self.model.config

#         for setting in REQUIRED_SETTINGS:
#             if not config.get(setting):
#                 problem = f"missing config {setting}"
#                 problems.append(problem)

#         return ";".join(problems)

#     def _make_pod_image_details(self) -> Dict[str, str]:
#         """Generate the pod image details.

#         Returns:
#             Dict[str, str]: pod image details.
#         """
#         config = self.model.config
#         image_details = {
#             "imagePath": config["image"],
#         }
#         if config["image_username"]:
#             image_details.update(
#                 {
#                     "username": config["image_username"],
#                     "password": config["image_password"],
#                 }
#             )
#         return image_details

#     def _make_pod_ports(self) -> List[Dict[str, Any]]:
#         """Generate the pod ports details.

#         Returns:
#             List[Dict[str, Any]]: pod ports details.
#         """
#         return [
#             {"name": "keystone", "containerPort": KEYSTONE_PORT, "protocol": "TCP"},
#         ]

#     def _make_pod_envconfig(self) -> Dict[str, Any]:
#         """Generate pod environment configuraiton.

#         Returns:
#             Dict[str, Any]: pod environment configuration.
#         """
#         config = self.model.config

#         envconfig = {
#             "DB_HOST": self.state.db_host,
#             "DB_PORT": self.state.db_port,
#             "ROOT_DB_USER": self.state.db_user,
#             "ROOT_DB_PASSWORD": self.state.db_password,
#             "KEYSTONE_DB_PASSWORD": config["keystone_db_password"],
#             "REGION_ID": config["region_id"],
#             "KEYSTONE_HOST": self.app.name,
#             "ADMIN_USERNAME": config["admin_username"],
#             "ADMIN_PASSWORD": config["admin_password"],
#             "ADMIN_PROJECT": config["admin_project"],
#             "SERVICE_USERNAME": config["service_username"],
#             "SERVICE_PASSWORD": config["service_password"],
#             "SERVICE_PROJECT": config["service_project"],
#         }

#         if config.get("ldap_enabled"):
#             envconfig["LDAP_AUTHENTICATION_DOMAIN_NAME"] = config[
#                 "ldap_authentication_domain_name"
#             ]
#             envconfig["LDAP_URL"] = config["ldap_url"]
#             envconfig["LDAP_PAGE_SIZE"] = config["ldap_page_size"]
#             envconfig["LDAP_USER_OBJECTCLASS"] = config["ldap_user_objectclass"]
#             envconfig["LDAP_USER_ID_ATTRIBUTE"] = config["ldap_user_id_attribute"]
#             envconfig["LDAP_USER_NAME_ATTRIBUTE"] = config["ldap_user_name_attribute"]
#             envconfig["LDAP_USER_PASS_ATTRIBUTE"] = config["ldap_user_pass_attribute"]
#             envconfig["LDAP_USER_ENABLED_MASK"] = config["ldap_user_enabled_mask"]
#             envconfig["LDAP_USER_ENABLED_DEFAULT"] = config["ldap_user_enabled_default"]
#             envconfig["LDAP_USER_ENABLED_INVERT"] = config["ldap_user_enabled_invert"]
#             envconfig["LDAP_GROUP_OBJECTCLASS"] = config["ldap_group_objectclass"]

#             if config["ldap_bind_user"]:
#                 envconfig["LDAP_BIND_USER"] = config["ldap_bind_user"]

#             if config["ldap_bind_password"]:
#                 envconfig["LDAP_BIND_PASSWORD"] = config["ldap_bind_password"]

#             if config["ldap_user_tree_dn"]:
#                 envconfig["LDAP_USER_TREE_DN"] = config["ldap_user_tree_dn"]

#             if config["ldap_user_filter"]:
#                 envconfig["LDAP_USER_FILTER"] = config["ldap_user_filter"]

#             if config["ldap_user_enabled_attribute"]:
#                 envconfig["LDAP_USER_ENABLED_ATTRIBUTE"] = config[
#                     "ldap_user_enabled_attribute"
#                 ]

#             if config["ldap_chase_referrals"]:
#                 envconfig["LDAP_CHASE_REFERRALS"] = config["ldap_chase_referrals"]

#             if config["ldap_group_tree_dn"]:
#                 envconfig["LDAP_GROUP_TREE_DN"] = config["ldap_group_tree_dn"]

#             if config["ldap_use_starttls"]:
#                 envconfig["LDAP_USE_STARTTLS"] = config["ldap_use_starttls"]
#                 envconfig["LDAP_TLS_CACERT_BASE64"] = config["ldap_tls_cacert_base64"]
#                 envconfig["LDAP_TLS_REQ_CERT"] = config["ldap_tls_req_cert"]

#         return envconfig

#     def _make_pod_ingress_resources(self) -> List[Dict[str, Any]]:
#         """Generate pod ingress resources.

#         Returns:
#             List[Dict[str, Any]]: pod ingress resources.
#         """
#         site_url = self.model.config["site_url"]

#         if not site_url:
#             return

#         parsed = urlparse(site_url)

#         if not parsed.scheme.startswith("http"):
#             return

#         max_file_size = self.model.config["max_file_size"]
#         ingress_whitelist_source_range = self.model.config[
#             "ingress_whitelist_source_range"
#         ]

#         annotations = {
#             "nginx.ingress.kubernetes.io/proxy-body-size": "{}m".format(max_file_size)
#         }

#         if ingress_whitelist_source_range:
#             annotations[
#                 "nginx.ingress.kubernetes.io/whitelist-source-range"
#             ] = ingress_whitelist_source_range

#         ingress_spec_tls = None

#         if parsed.scheme == "https":
#             ingress_spec_tls = [{"hosts": [parsed.hostname]}]
#             tls_secret_name = self.model.config["tls_secret_name"]
#             if tls_secret_name:
#                 ingress_spec_tls[0]["secretName"] = tls_secret_name
#         else:
#             annotations["nginx.ingress.kubernetes.io/ssl-redirect"] = "false"

#         ingress = {
#             "name": "{}-ingress".format(self.app.name),
#             "annotations": annotations,
#             "spec": {
#                 "rules": [
#                     {
#                         "host": parsed.hostname,
#                         "http": {
#                             "paths": [
#                                 {
#                                     "path": "/",
#                                     "backend": {
#                                         "serviceName": self.app.name,
#                                         "servicePort": KEYSTONE_PORT,
#                                     },
#                                 }
#                             ]
#                         },
#                     }
#                 ],
#             },
#         }
#         if ingress_spec_tls:
#             ingress["spec"]["tls"] = ingress_spec_tls

#         return [ingress]

#     def _generate_keys(self) -> Tuple[List[str], List[str]]:
#         """Generating new fernet tokens.

#         Returns:
#             Tuple[List[str], List[str]]: contains two lists of strings. First
#                                          list contains strings that represent
#                                          the keys for fernet and the second
#                                          list contains strins that represent
#                                          the keys for credentials.
#         """
#         fernet_keys = [
#             Fernet.generate_key().decode() for _ in range(NUMBER_FERNET_KEYS)
#         ]
#         credential_keys = [
#             Fernet.generate_key().decode() for _ in range(NUMBER_CREDENTIAL_KEYS)
#         ]

#         return (fernet_keys, credential_keys)

#     def configure_pod(self, event: EventBase) -> NoReturn:
#         """Assemble the pod spec and apply it, if possible.

#         Args:
#             event (EventBase): Hook or Relation event that started the
#                                function.
#         """
#         if not self.state.db_host:
#             self.unit.status = WaitingStatus("Waiting for database relation")
#             event.defer()
#             return

#         if not self.unit.is_leader():
#             self.unit.status = ActiveStatus("ready")
#             return

#         if fernet_keys := self.state.fernet_keys:
#             fernet_keys = json.loads(fernet_keys)

#         if credential_keys := self.state.credential_keys:
#             credential_keys = json.loads(credential_keys)

#         now = datetime.now().timestamp()
#         keys_timestamp = self.state.keys_timestamp
#         token_expiration = self.model.config["token_expiration"]

#         valid_keys = (now - keys_timestamp) < token_expiration
#         if not credential_keys or not fernet_keys or not valid_keys:
#             fernet_keys, credential_keys = self._generate_keys()
#             self.state.fernet_keys = json.dumps(fernet_keys)
#             self.state.credential_keys = json.dumps(credential_keys)
#             self.state.keys_timestamp = now

#         # Check problems in the settings
#         problems = self._check_settings()
#         if problems:
#             self.unit.status = BlockedStatus(problems)
#             return

#         self.unit.status = BlockedStatus("Assembling pod spec")
#         image_details = self._make_pod_image_details()
#         ports = self._make_pod_ports()
#         env_config = self._make_pod_envconfig()
#         ingress_resources = self._make_pod_ingress_resources()
#         files = self._make_pod_files(fernet_keys, credential_keys)

#         pod_spec = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": self.framework.model.app.name,
#                     "imageDetails": image_details,
#                     "ports": ports,
#                     "envConfig": env_config,
#                     "volumeConfig": files,
#                 }
#             ],
#             "kubernetesResources": {"ingressResources": ingress_resources or []},
#         }

#         if self.state.pod_spec != (
#             pod_spec_json := json.dumps(pod_spec, sort_keys=True)
#         ):
#             self.state.pod_spec = pod_spec_json
#             self.model.pod.set_spec(pod_spec)

#         self.unit.status = ActiveStatus("ready")


# if __name__ == "__main__":
#     main(KeystoneCharm)
