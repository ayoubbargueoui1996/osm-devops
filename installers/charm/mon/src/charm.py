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
from opslib.osm.interfaces.keystone import KeystoneClient
from opslib.osm.interfaces.mongo import MongoClient
from opslib.osm.interfaces.prometheus import PrometheusClient
from opslib.osm.pod import ContainerV3Builder, FilesV3Builder, PodSpecV3Builder
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)

PORT = 8000


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
    keystone_enabled: bool
    vca_host: str
    vca_user: str
    vca_secret: str
    vca_cacert: str
    database_commonkey: str
    mongodb_uri: Optional[str]
    log_level: str
    openstack_default_granularity: int
    global_request_timeout: int
    collector_interval: int
    evaluator_interval: int
    grafana_url: str
    grafana_user: str
    grafana_password: str
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

    @property
    def certificates_dict(cls):
        return _extract_certificates(cls.certificates) if cls.certificates else {}


class MonCharm(CharmedOsmBase):
    def __init__(self, *args) -> NoReturn:
        super().__init__(*args, oci_image="image")

        self.kafka_client = KafkaClient(self, "kafka")
        self.framework.observe(self.on["kafka"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["kafka"].relation_broken, self.configure_pod)

        self.mongodb_client = MongoClient(self, "mongodb")
        self.framework.observe(self.on["mongodb"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["mongodb"].relation_broken, self.configure_pod)

        self.prometheus_client = PrometheusClient(self, "prometheus")
        self.framework.observe(
            self.on["prometheus"].relation_changed, self.configure_pod
        )
        self.framework.observe(
            self.on["prometheus"].relation_broken, self.configure_pod
        )

        self.keystone_client = KeystoneClient(self, "keystone")
        self.framework.observe(self.on["keystone"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["keystone"].relation_broken, self.configure_pod)

    def _check_missing_dependencies(self, config: ConfigModel):
        missing_relations = []

        if self.kafka_client.is_missing_data_in_unit():
            missing_relations.append("kafka")
        if not config.mongodb_uri and self.mongodb_client.is_missing_data_in_unit():
            missing_relations.append("mongodb")
        if self.prometheus_client.is_missing_data_in_app():
            missing_relations.append("prometheus")
        if config.keystone_enabled:
            if self.keystone_client.is_missing_data_in_app():
                missing_relations.append("keystone")

        if missing_relations:
            raise RelationsMissing(missing_relations)

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

        if config.mongodb_uri and not self.mongodb_client.is_missing_data_in_unit():
            raise Exception("Mongodb data cannot be provided via config and relation")

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
        container_builder.add_envs(
            {
                # General configuration
                "ALLOW_ANONYMOUS_LOGIN": "yes",
                "OSMMON_OPENSTACK_DEFAULT_GRANULARITY": config.openstack_default_granularity,
                "OSMMON_GLOBAL_REQUEST_TIMEOUT": config.global_request_timeout,
                "OSMMON_GLOBAL_LOGLEVEL": config.log_level,
                "OSMMON_COLLECTOR_INTERVAL": config.collector_interval,
                "OSMMON_EVALUATOR_INTERVAL": config.evaluator_interval,
                # Kafka configuration
                "OSMMON_MESSAGE_DRIVER": "kafka",
                "OSMMON_MESSAGE_HOST": self.kafka_client.host,
                "OSMMON_MESSAGE_PORT": self.kafka_client.port,
                # Database configuration
                "OSMMON_DATABASE_DRIVER": "mongo",
                "OSMMON_DATABASE_URI": config.mongodb_uri
                or self.mongodb_client.connection_string,
                "OSMMON_DATABASE_COMMONKEY": config.database_commonkey,
                # Prometheus configuration
                "OSMMON_PROMETHEUS_URL": f"http://{self.prometheus_client.hostname}:{self.prometheus_client.port}",
                # VCA configuration
                "OSMMON_VCA_HOST": config.vca_host,
                "OSMMON_VCA_USER": config.vca_user,
                "OSMMON_VCA_SECRET": config.vca_secret,
                "OSMMON_VCA_CACERT": config.vca_cacert,
                "OSMMON_GRAFANA_URL": config.grafana_url,
                "OSMMON_GRAFANA_USER": config.grafana_user,
                "OSMMON_GRAFANA_PASSWORD": config.grafana_password,
            }
        )
        if config.keystone_enabled:
            container_builder.add_envs(
                {
                    "OSMMON_KEYSTONE_ENABLED": True,
                    "OSMMON_KEYSTONE_URL": self.keystone_client.host,
                    "OSMMON_KEYSTONE_DOMAIN_NAME": self.keystone_client.user_domain_name,
                    "OSMMON_KEYSTONE_PROJECT_DOMAIN_NAME": self.keystone_client.project_domain_name,
                    "OSMMON_KEYSTONE_SERVICE_USER": self.keystone_client.username,
                    "OSMMON_KEYSTONE_SERVICE_PASSWORD": self.keystone_client.password,
                    "OSMMON_KEYSTONE_SERVICE_PROJECT": self.keystone_client.service,
                }
            )
        container = container_builder.build()

        # Add container to pod spec
        pod_spec_builder.add_container(container)

        return pod_spec_builder.build()


if __name__ == "__main__":
    main(MonCharm)
