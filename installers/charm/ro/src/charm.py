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

import base64
import logging
from typing import NoReturn, Optional

from ops.main import main
from opslib.osm.charm import CharmedOsmBase, RelationsMissing
from opslib.osm.interfaces.kafka import KafkaClient
from opslib.osm.interfaces.mongo import MongoClient
from opslib.osm.interfaces.mysql import MysqlClient
from opslib.osm.pod import ContainerV3Builder, FilesV3Builder, PodSpecV3Builder
from opslib.osm.validator import ModelValidator, validator

logger = logging.getLogger(__name__)

PORT = 9090


def _check_certificate_data(name: str, content: str):
    if not name or not content:
        raise ValueError("certificate name and content must be a non-empty string")


def _extract_certificates(certs_config: str):
    certificates = {}
    if certs_config:
        cert_list = certs_config.split(",")
        for cert in cert_list:
            name, content = cert.split(":")
            _check_certificate_data(name, content)
            certificates[name] = content
    return certificates


def decode(content: str):
    return base64.b64decode(content.encode("utf-8")).decode("utf-8")


class ConfigModel(ModelValidator):
    enable_ng_ro: bool
    database_commonkey: str
    mongodb_uri: Optional[str]
    log_level: str
    mysql_host: Optional[str]
    mysql_port: Optional[int]
    mysql_user: Optional[str]
    mysql_password: Optional[str]
    mysql_root_password: Optional[str]
    vim_database: str
    ro_database: str
    openmano_tenant: str
    certificates: Optional[str]

    @validator("log_level")
    def validate_log_level(cls, v):
        if v not in {"INFO", "DEBUG"}:
            raise ValueError("value must be INFO or DEBUG")
        return v

    @validator("certificates")
    def validate_certificates(cls, v):
        # Raises an exception if it cannot extract the certificates
        _extract_certificates(v)
        return v

    @validator("mongodb_uri")
    def validate_mongodb_uri(cls, v):
        if v and not v.startswith("mongodb://"):
            raise ValueError("mongodb_uri is not properly formed")
        return v

    @validator("mysql_port")
    def validate_mysql_port(cls, v):
        if v and (v <= 0 or v >= 65535):
            raise ValueError("Mysql port out of range")
        return v

    @property
    def certificates_dict(cls):
        return _extract_certificates(cls.certificates) if cls.certificates else {}


class RoCharm(CharmedOsmBase):
    """GrafanaCharm Charm."""

    def __init__(self, *args) -> NoReturn:
        """Prometheus Charm constructor."""
        super().__init__(*args, oci_image="image")

        self.kafka_client = KafkaClient(self, "kafka")
        self.framework.observe(self.on["kafka"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["kafka"].relation_broken, self.configure_pod)

        self.mysql_client = MysqlClient(self, "mysql")
        self.framework.observe(self.on["mysql"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["mysql"].relation_broken, self.configure_pod)

        self.mongodb_client = MongoClient(self, "mongodb")
        self.framework.observe(self.on["mongodb"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["mongodb"].relation_broken, self.configure_pod)

        self.framework.observe(self.on["ro"].relation_joined, self._publish_ro_info)

    def _publish_ro_info(self, event):
        """Publishes RO information.

        Args:
            event (EventBase): RO relation event.
        """
        if self.unit.is_leader():
            rel_data = {
                "host": self.model.app.name,
                "port": str(PORT),
            }
            for k, v in rel_data.items():
                event.relation.data[self.app][k] = v

    def _check_missing_dependencies(self, config: ConfigModel):
        missing_relations = []

        if config.enable_ng_ro:
            if self.kafka_client.is_missing_data_in_unit():
                missing_relations.append("kafka")
            if not config.mongodb_uri and self.mongodb_client.is_missing_data_in_unit():
                missing_relations.append("mongodb")
        else:
            if not config.mysql_host and self.mysql_client.is_missing_data_in_unit():
                missing_relations.append("mysql")
        if missing_relations:
            raise RelationsMissing(missing_relations)

    def _validate_mysql_config(self, config: ConfigModel):
        invalid_values = []
        if not config.mysql_user:
            invalid_values.append("Mysql user is empty")
        if not config.mysql_password:
            invalid_values.append("Mysql password is empty")
        if not config.mysql_root_password:
            invalid_values.append("Mysql root password empty")

        if invalid_values:
            raise ValueError("Invalid values: " + ", ".join(invalid_values))

    def _build_cert_files(
        self,
        config: ConfigModel,
    ):
        cert_files_builder = FilesV3Builder()
        for name, content in config.certificates_dict.items():
            cert_files_builder.add_file(name, decode(content), mode=0o600)
        return cert_files_builder.build()

    def build_pod_spec(self, image_info):
        # Validate config
        config = ConfigModel(**dict(self.config))

        if config.enable_ng_ro:
            if config.mongodb_uri and not self.mongodb_client.is_missing_data_in_unit():
                raise Exception(
                    "Mongodb data cannot be provided via config and relation"
                )
        else:
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
        certs_files = self._build_cert_files(config)

        if certs_files:
            container_builder.add_volume_config("certs", "/certs", certs_files)

        container_builder.add_port(name=self.app.name, port=PORT)
        container_builder.add_http_readiness_probe(
            "/ro/" if config.enable_ng_ro else "/openmano/tenants",
            PORT,
            initial_delay_seconds=10,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=3,
        )
        container_builder.add_http_liveness_probe(
            "/ro/" if config.enable_ng_ro else "/openmano/tenants",
            PORT,
            initial_delay_seconds=600,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=3,
        )
        container_builder.add_envs(
            {
                "OSMRO_LOG_LEVEL": config.log_level,
            }
        )

        if config.enable_ng_ro:
            container_builder.add_envs(
                {
                    "OSMRO_MESSAGE_DRIVER": "kafka",
                    "OSMRO_MESSAGE_HOST": self.kafka_client.host,
                    "OSMRO_MESSAGE_PORT": self.kafka_client.port,
                    # MongoDB configuration
                    "OSMRO_DATABASE_DRIVER": "mongo",
                    "OSMRO_DATABASE_URI": config.mongodb_uri
                    or self.mongodb_client.connection_string,
                    "OSMRO_DATABASE_COMMONKEY": config.database_commonkey,
                }
            )

        else:
            container_builder.add_envs(
                {
                    "RO_DB_HOST": config.mysql_host or self.mysql_client.host,
                    "RO_DB_OVIM_HOST": config.mysql_host or self.mysql_client.host,
                    "RO_DB_PORT": config.mysql_port or self.mysql_client.port,
                    "RO_DB_OVIM_PORT": config.mysql_port or self.mysql_client.port,
                    "RO_DB_USER": config.mysql_user or self.mysql_client.user,
                    "RO_DB_OVIM_USER": config.mysql_user or self.mysql_client.user,
                    "RO_DB_PASSWORD": config.mysql_password
                    or self.mysql_client.password,
                    "RO_DB_OVIM_PASSWORD": config.mysql_password
                    or self.mysql_client.password,
                    "RO_DB_ROOT_PASSWORD": config.mysql_root_password
                    or self.mysql_client.root_password,
                    "RO_DB_OVIM_ROOT_PASSWORD": config.mysql_root_password
                    or self.mysql_client.root_password,
                    "RO_DB_NAME": config.ro_database,
                    "RO_DB_OVIM_NAME": config.vim_database,
                    "OPENMANO_TENANT": config.openmano_tenant,
                }
            )
        container = container_builder.build()

        # Add container to pod spec
        pod_spec_builder.add_container(container)

        return pod_spec_builder.build()


if __name__ == "__main__":
    main(RoCharm)
