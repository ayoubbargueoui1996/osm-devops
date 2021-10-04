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
from opslib.osm.interfaces.http import HttpClient
from opslib.osm.interfaces.kafka import KafkaClient
from opslib.osm.interfaces.mongo import MongoClient
from opslib.osm.pod import ContainerV3Builder, PodSpecV3Builder
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)

PORT = 9999


class ConfigModel(ModelValidator):
    vca_host: Optional[str]
    vca_port: Optional[int]
    vca_user: Optional[str]
    vca_secret: Optional[str]
    vca_pubkey: Optional[str]
    vca_cacert: Optional[str]
    vca_cloud: Optional[str]
    vca_k8s_cloud: Optional[str]
    database_commonkey: str
    mongodb_uri: Optional[str]
    log_level: str
    vca_apiproxy: Optional[str]
    # Model-config options
    vca_model_config_agent_metadata_url: Optional[str]
    vca_model_config_agent_stream: Optional[str]
    vca_model_config_apt_ftp_proxy: Optional[str]
    vca_model_config_apt_http_proxy: Optional[str]
    vca_model_config_apt_https_proxy: Optional[str]
    vca_model_config_apt_mirror: Optional[str]
    vca_model_config_apt_no_proxy: Optional[str]
    vca_model_config_automatically_retry_hooks: Optional[bool]
    vca_model_config_backup_dir: Optional[str]
    vca_model_config_cloudinit_userdata: Optional[str]
    vca_model_config_container_image_metadata_url: Optional[str]
    vca_model_config_container_image_stream: Optional[str]
    vca_model_config_container_inherit_properties: Optional[str]
    vca_model_config_container_networking_method: Optional[str]
    vca_model_config_default_series: Optional[str]
    vca_model_config_default_space: Optional[str]
    vca_model_config_development: Optional[bool]
    vca_model_config_disable_network_management: Optional[bool]
    vca_model_config_egress_subnets: Optional[str]
    vca_model_config_enable_os_refresh_update: Optional[bool]
    vca_model_config_enable_os_upgrade: Optional[bool]
    vca_model_config_fan_config: Optional[str]
    vca_model_config_firewall_mode: Optional[str]
    vca_model_config_ftp_proxy: Optional[str]
    vca_model_config_http_proxy: Optional[str]
    vca_model_config_https_proxy: Optional[str]
    vca_model_config_ignore_machine_addresses: Optional[bool]
    vca_model_config_image_metadata_url: Optional[str]
    vca_model_config_image_stream: Optional[str]
    vca_model_config_juju_ftp_proxy: Optional[str]
    vca_model_config_juju_http_proxy: Optional[str]
    vca_model_config_juju_https_proxy: Optional[str]
    vca_model_config_juju_no_proxy: Optional[str]
    vca_model_config_logforward_enabled: Optional[bool]
    vca_model_config_logging_config: Optional[str]
    vca_model_config_lxd_snap_channel: Optional[str]
    vca_model_config_max_action_results_age: Optional[str]
    vca_model_config_max_action_results_size: Optional[str]
    vca_model_config_max_status_history_age: Optional[str]
    vca_model_config_max_status_history_size: Optional[str]
    vca_model_config_net_bond_reconfigure_delay: Optional[str]
    vca_model_config_no_proxy: Optional[str]
    vca_model_config_provisioner_harvest_mode: Optional[str]
    vca_model_config_proxy_ssh: Optional[bool]
    vca_model_config_snap_http_proxy: Optional[str]
    vca_model_config_snap_https_proxy: Optional[str]
    vca_model_config_snap_store_assertions: Optional[str]
    vca_model_config_snap_store_proxy: Optional[str]
    vca_model_config_snap_store_proxy_url: Optional[str]
    vca_model_config_ssl_hostname_verification: Optional[bool]
    vca_model_config_test_mode: Optional[bool]
    vca_model_config_transmit_vendor_metrics: Optional[bool]
    vca_model_config_update_status_hook_interval: Optional[str]
    vca_stablerepourl: Optional[str]

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


class LcmCharm(CharmedOsmBase):
    def __init__(self, *args) -> NoReturn:
        super().__init__(*args, oci_image="image")

        self.kafka_client = KafkaClient(self, "kafka")
        self.framework.observe(self.on["kafka"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["kafka"].relation_broken, self.configure_pod)

        self.mongodb_client = MongoClient(self, "mongodb")
        self.framework.observe(self.on["mongodb"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["mongodb"].relation_broken, self.configure_pod)

        self.ro_client = HttpClient(self, "ro")
        self.framework.observe(self.on["ro"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["ro"].relation_broken, self.configure_pod)

    def _check_missing_dependencies(self, config: ConfigModel):
        missing_relations = []

        if self.kafka_client.is_missing_data_in_unit():
            missing_relations.append("kafka")
        if not config.mongodb_uri and self.mongodb_client.is_missing_data_in_unit():
            missing_relations.append("mongodb")
        if self.ro_client.is_missing_data_in_app():
            missing_relations.append("ro")

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
                "OSMLCM_GLOBAL_LOGLEVEL": config.log_level,
                # RO configuration
                "OSMLCM_RO_HOST": self.ro_client.host,
                "OSMLCM_RO_PORT": self.ro_client.port,
                "OSMLCM_RO_TENANT": "osm",
                # Kafka configuration
                "OSMLCM_MESSAGE_DRIVER": "kafka",
                "OSMLCM_MESSAGE_HOST": self.kafka_client.host,
                "OSMLCM_MESSAGE_PORT": self.kafka_client.port,
                # Database configuration
                "OSMLCM_DATABASE_DRIVER": "mongo",
                "OSMLCM_DATABASE_URI": config.mongodb_uri
                or self.mongodb_client.connection_string,
                "OSMLCM_DATABASE_COMMONKEY": config.database_commonkey,
                # Storage configuration
                "OSMLCM_STORAGE_DRIVER": "mongo",
                "OSMLCM_STORAGE_PATH": "/app/storage",
                "OSMLCM_STORAGE_COLLECTION": "files",
                "OSMLCM_STORAGE_URI": config.mongodb_uri
                or self.mongodb_client.connection_string,
                "OSMLCM_VCA_STABLEREPOURL": config.vca_stablerepourl,
            }
        )
        if config.vca_host:
            container_builder.add_envs(
                {
                    # VCA configuration
                    "OSMLCM_VCA_HOST": config.vca_host,
                    "OSMLCM_VCA_PORT": config.vca_port,
                    "OSMLCM_VCA_USER": config.vca_user,
                    "OSMLCM_VCA_PUBKEY": config.vca_pubkey,
                    "OSMLCM_VCA_SECRET": config.vca_secret,
                    "OSMLCM_VCA_CACERT": config.vca_cacert,
                    "OSMLCM_VCA_CLOUD": config.vca_cloud,
                    "OSMLCM_VCA_K8S_CLOUD": config.vca_k8s_cloud,
                }
            )
            if config.vca_apiproxy:
                container_builder.add_env("OSMLCM_VCA_APIPROXY", config.vca_apiproxy)

            model_config_envs = {
                f"OSMLCM_{k.upper()}": v
                for k, v in self.config.items()
                if k.startswith("vca_model_config")
            }
            if model_config_envs:
                container_builder.add_envs(model_config_envs)
        container = container_builder.build()

        # Add container to pod spec
        pod_spec_builder.add_container(container)

        return pod_spec_builder.build()


if __name__ == "__main__":
    main(LcmCharm)


# class ConfigurePodEvent(EventBase):
#     """Configure Pod event"""

#     pass


# class LcmEvents(CharmEvents):
#     """LCM Events"""

#     configure_pod = EventSource(ConfigurePodEvent)


# class LcmCharm(CharmBase):
#     """LCM Charm."""

#     state = StoredState()
#     on = LcmEvents()

#     def __init__(self, *args) -> NoReturn:
#         """LCM Charm constructor."""
#         super().__init__(*args)

#         # Internal state initialization
#         self.state.set_default(pod_spec=None)

#         # Message bus data initialization
#         self.state.set_default(message_host=None)
#         self.state.set_default(message_port=None)

#         # Database data initialization
#         self.state.set_default(database_uri=None)

#         # RO data initialization
#         self.state.set_default(ro_host=None)
#         self.state.set_default(ro_port=None)

#         self.port = LCM_PORT
#         self.image = OCIImageResource(self, "image")

#         # Registering regular events
#         self.framework.observe(self.on.start, self.configure_pod)
#         self.framework.observe(self.on.config_changed, self.configure_pod)
#         self.framework.observe(self.on.upgrade_charm, self.configure_pod)

#         # Registering custom internal events
#         self.framework.observe(self.on.configure_pod, self.configure_pod)

#         # Registering required relation events
#         self.framework.observe(
#             self.on.kafka_relation_changed, self._on_kafka_relation_changed
#         )
#         self.framework.observe(
#             self.on.mongodb_relation_changed, self._on_mongodb_relation_changed
#         )
#         self.framework.observe(
#             self.on.ro_relation_changed, self._on_ro_relation_changed
#         )

#         # Registering required relation broken events
#         self.framework.observe(
#             self.on.kafka_relation_broken, self._on_kafka_relation_broken
#         )
#         self.framework.observe(
#             self.on.mongodb_relation_broken, self._on_mongodb_relation_broken
#         )
#         self.framework.observe(
#             self.on.ro_relation_broken, self._on_ro_relation_broken
#         )

#     def _on_kafka_relation_changed(self, event: EventBase) -> NoReturn:
#         """Reads information about the kafka relation.

#         Args:
#             event (EventBase): Kafka relation event.
#         """
#         message_host = event.relation.data[event.unit].get("host")
#         message_port = event.relation.data[event.unit].get("port")

#         if (
#             message_host
#             and message_port
#             and (
#                 self.state.message_host != message_host
#                 or self.state.message_port != message_port
#             )
#         ):
#             self.state.message_host = message_host
#             self.state.message_port = message_port
#             self.on.configure_pod.emit()

#     def _on_kafka_relation_broken(self, event: EventBase) -> NoReturn:
#         """Clears data from kafka relation.

#         Args:
#             event (EventBase): Kafka relation event.
#         """
#         self.state.message_host = None
#         self.state.message_port = None
#         self.on.configure_pod.emit()

#     def _on_mongodb_relation_changed(self, event: EventBase) -> NoReturn:
#         """Reads information about the DB relation.

#         Args:
#             event (EventBase): DB relation event.
#         """
#         database_uri = event.relation.data[event.unit].get("connection_string")

#         if database_uri and self.state.database_uri != database_uri:
#             self.state.database_uri = database_uri
#             self.on.configure_pod.emit()

#     def _on_mongodb_relation_broken(self, event: EventBase) -> NoReturn:
#         """Clears data from mongodb relation.

#         Args:
#             event (EventBase): DB relation event.
#         """
#         self.state.database_uri = None
#         self.on.configure_pod.emit()

#     def _on_ro_relation_changed(self, event: EventBase) -> NoReturn:
#         """Reads information about the RO relation.

#         Args:
#             event (EventBase): Keystone relation event.
#         """
#         ro_host = event.relation.data[event.unit].get("host")
#         ro_port = event.relation.data[event.unit].get("port")

#         if (
#             ro_host
#             and ro_port
#             and (self.state.ro_host != ro_host or self.state.ro_port != ro_port)
#         ):
#             self.state.ro_host = ro_host
#             self.state.ro_port = ro_port
#             self.on.configure_pod.emit()

#     def _on_ro_relation_broken(self, event: EventBase) -> NoReturn:
#         """Clears data from ro relation.

#         Args:
#             event (EventBase): Keystone relation event.
#         """
#         self.state.ro_host = None
#         self.state.ro_port = None
#         self.on.configure_pod.emit()

#     def _missing_relations(self) -> str:
#         """Checks if there missing relations.

#         Returns:
#             str: string with missing relations
#         """
#         data_status = {
#             "kafka": self.state.message_host,
#             "mongodb": self.state.database_uri,
#             "ro": self.state.ro_host,
#         }

#         missing_relations = [k for k, v in data_status.items() if not v]

#         return ", ".join(missing_relations)

#     @property
#     def relation_state(self) -> Dict[str, Any]:
#         """Collects relation state configuration for pod spec assembly.

#         Returns:
#             Dict[str, Any]: relation state information.
#         """
#         relation_state = {
#             "message_host": self.state.message_host,
#             "message_port": self.state.message_port,
#             "database_uri": self.state.database_uri,
#             "ro_host": self.state.ro_host,
#             "ro_port": self.state.ro_port,
#         }

#         return relation_state

#     def configure_pod(self, event: EventBase) -> NoReturn:
#         """Assemble the pod spec and apply it, if possible.

#         Args:
#             event (EventBase): Hook or Relation event that started the
#                                function.
#         """
#         if missing := self._missing_relations():
#             self.unit.status = BlockedStatus(
#                 "Waiting for {0} relation{1}".format(
#                     missing, "s" if "," in missing else ""
#                 )
#             )
#             return

#         if not self.unit.is_leader():
#             self.unit.status = ActiveStatus("ready")
#             return

#         self.unit.status = MaintenanceStatus("Assembling pod spec")

#         # Fetch image information
#         try:
#             self.unit.status = MaintenanceStatus("Fetching image information")
#             image_info = self.image.fetch()
#         except OCIImageResourceError:
#             self.unit.status = BlockedStatus("Error fetching image information")
#             return

#         try:
#             pod_spec = make_pod_spec(
#                 image_info,
#                 self.model.config,
#                 self.relation_state,
#                 self.model.app.name,
#                 self.port,
#             )
#         except ValueError as exc:
#             logger.exception("Config/Relation data validation error")
#             self.unit.status = BlockedStatus(str(exc))
#             return

#         if self.state.pod_spec != pod_spec:
#             self.model.pod.set_spec(pod_spec)
#             self.state.pod_spec = pod_spec

#         self.unit.status = ActiveStatus("ready")


# if __name__ == "__main__":
#     main(LcmCharm)
