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

from ipaddress import ip_network
import logging
from pathlib import Path
from string import Template
from typing import NoReturn, Optional
from urllib.parse import urlparse

from ops.main import main
from opslib.osm.charm import CharmedOsmBase, RelationsMissing
from opslib.osm.interfaces.prometheus import PrometheusClient
from opslib.osm.pod import (
    ContainerV3Builder,
    FilesV3Builder,
    IngressResourceV3Builder,
    PodSpecV3Builder,
)
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)

PORT = 3000


class ConfigModel(ModelValidator):
    max_file_size: int
    osm_dashboards: bool
    site_url: Optional[str]
    cluster_issuer: Optional[str]
    ingress_whitelist_source_range: Optional[str]
    tls_secret_name: Optional[str]

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


class GrafanaCharm(CharmedOsmBase):
    """GrafanaCharm Charm."""

    def __init__(self, *args) -> NoReturn:
        """Prometheus Charm constructor."""
        super().__init__(*args, oci_image="image")

        self.prometheus_client = PrometheusClient(self, "prometheus")
        self.framework.observe(
            self.on["prometheus"].relation_changed, self.configure_pod
        )
        self.framework.observe(
            self.on["prometheus"].relation_broken, self.configure_pod
        )

    def _build_dashboard_files(self, config: ConfigModel):
        files_builder = FilesV3Builder()
        files_builder.add_file(
            "dashboard_osm.yaml",
            Path("files/default_dashboards.yaml").read_text(),
        )
        if config.osm_dashboards:
            osm_dashboards_mapping = {
                "kafka_exporter_dashboard.json": "files/kafka_exporter_dashboard.json",
                "mongodb_exporter_dashboard.json": "files/mongodb_exporter_dashboard.json",
                "mysql_exporter_dashboard.json": "files/mysql_exporter_dashboard.json",
                "nodes_exporter_dashboard.json": "files/nodes_exporter_dashboard.json",
                "summary_dashboard.json": "files/summary_dashboard.json",
            }
            for file_name, path in osm_dashboards_mapping.items():
                files_builder.add_file(file_name, Path(path).read_text())
        return files_builder.build()

    def _build_datasources_files(self):
        files_builder = FilesV3Builder()
        files_builder.add_file(
            "datasource_prometheus.yaml",
            Template(Path("files/default_datasources.yaml").read_text()).substitute(
                prometheus_host=self.prometheus_client.hostname,
                prometheus_port=self.prometheus_client.port,
            ),
        )
        return files_builder.build()

    def _check_missing_dependencies(self):
        missing_relations = []

        if self.prometheus_client.is_missing_data_in_app():
            missing_relations.append("prometheus")

        if missing_relations:
            raise RelationsMissing(missing_relations)

    def build_pod_spec(self, image_info):
        # Validate config
        config = ConfigModel(**dict(self.config))
        # Check relations
        self._check_missing_dependencies()
        # Create Builder for the PodSpec
        pod_spec_builder = PodSpecV3Builder()
        # Build Container
        container_builder = ContainerV3Builder(self.app.name, image_info)
        container_builder.add_port(name=self.app.name, port=PORT)
        container_builder.add_http_readiness_probe(
            "/api/health",
            PORT,
            initial_delay_seconds=10,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=3,
        )
        container_builder.add_http_liveness_probe(
            "/api/health",
            PORT,
            initial_delay_seconds=60,
            timeout_seconds=30,
            failure_threshold=10,
        )
        container_builder.add_volume_config(
            "dashboards",
            "/etc/grafana/provisioning/dashboards/",
            self._build_dashboard_files(config),
        )
        container_builder.add_volume_config(
            "datasources",
            "/etc/grafana/provisioning/datasources/",
            self._build_datasources_files(),
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

            if config.cluster_issuer:
                annotations["cert-manager.io/cluster-issuer"] = config.cluster_issuer

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
    main(GrafanaCharm)
