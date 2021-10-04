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


import logging
from typing import NoReturn, Optional

from ops.main import main
from opslib.osm.charm import CharmedOsmBase, RelationsMissing
from opslib.osm.interfaces.kafka import KafkaClient
from opslib.osm.interfaces.mongo import MongoClient
from opslib.osm.pod import (
    ContainerV3Builder,
    PodSpecV3Builder,
)
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)

PORT = 9999


class ConfigModel(ModelValidator):
    database_commonkey: str
    mongodb_uri: Optional[str]
    log_level: str

    @validator("log_level")
    def validate_log_level(cls, v):
        if v not in {"INFO", "DEBUG"}:
            raise ValueError("value must be INFO or DEBUG")
        return v

    @validator("mongodb_uri")
    def validate_mongodb_uri(cls, v):
        if v and not v.startswith("mongodb://"):
            raise ValueError("mongodb_uri is not properly formed")
        return v


class PlaCharm(CharmedOsmBase):
    def __init__(self, *args) -> NoReturn:
        super().__init__(*args, oci_image="image")

        self.kafka_client = KafkaClient(self, "kafka")
        self.framework.observe(self.on["kafka"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["kafka"].relation_broken, self.configure_pod)

        self.mongodb_client = MongoClient(self, "mongodb")
        self.framework.observe(self.on["mongodb"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["mongodb"].relation_broken, self.configure_pod)

    def _check_missing_dependencies(self, config: ConfigModel):
        missing_relations = []

        if self.kafka_client.is_missing_data_in_unit():
            missing_relations.append("kafka")
        if not config.mongodb_uri and self.mongodb_client.is_missing_data_in_unit():
            missing_relations.append("mongodb")

        if missing_relations:
            raise RelationsMissing(missing_relations)

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
        container_builder.add_port(name=self.app.name, port=PORT)
        container_builder.add_envs(
            {
                # General configuration
                "ALLOW_ANONYMOUS_LOGIN": "yes",
                "OSMPLA_GLOBAL_LOG_LEVEL": config.log_level,
                # Kafka configuration
                "OSMPLA_MESSAGE_DRIVER": "kafka",
                "OSMPLA_MESSAGE_HOST": self.kafka_client.host,
                "OSMPLA_MESSAGE_PORT": self.kafka_client.port,
                # Database configuration
                "OSMPLA_DATABASE_DRIVER": "mongo",
                "OSMPLA_DATABASE_URI": config.mongodb_uri
                or self.mongodb_client.connection_string,
                "OSMPLA_DATABASE_COMMONKEY": config.database_commonkey,
            }
        )

        container = container_builder.build()

        # Add container to pod spec
        pod_spec_builder.add_container(container)

        return pod_spec_builder.build()


if __name__ == "__main__":
    main(PlaCharm)
