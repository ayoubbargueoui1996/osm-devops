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
from typing import NoReturn, Optional
from urllib.parse import urlparse

from oci_image import OCIImageResource
from ops.framework import EventBase
from ops.main import main
from opslib.osm.charm import CharmedOsmBase
from opslib.osm.interfaces.prometheus import PrometheusServer
from opslib.osm.pod import (
    ContainerV3Builder,
    FilesV3Builder,
    IngressResourceV3Builder,
    PodSpecV3Builder,
)
from opslib.osm.validator import (
    ModelValidator,
    validator,
)
import requests


logger = logging.getLogger(__name__)

PORT = 9090


class ConfigModel(ModelValidator):
    web_subpath: str
    default_target: str
    max_file_size: int
    site_url: Optional[str]
    cluster_issuer: Optional[str]
    ingress_whitelist_source_range: Optional[str]
    tls_secret_name: Optional[str]
    enable_web_admin_api: bool

    @validator("web_subpath")
    def validate_web_subpath(cls, v):
        if len(v) < 1:
            raise ValueError("web-subpath must be a non-empty string")
        return v

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


class PrometheusCharm(CharmedOsmBase):

    """Prometheus Charm."""

    def __init__(self, *args) -> NoReturn:
        """Prometheus Charm constructor."""
        super().__init__(*args, oci_image="image")

        # Registering provided relation events
        self.prometheus = PrometheusServer(self, "prometheus")
        self.framework.observe(
            self.on.prometheus_relation_joined,  # pylint: disable=E1101
            self._publish_prometheus_info,
        )

        # Registering actions
        self.framework.observe(
            self.on.backup_action,  # pylint: disable=E1101
            self._on_backup_action,
        )

    def _publish_prometheus_info(self, event: EventBase) -> NoReturn:
        self.prometheus.publish_info(self.app.name, PORT)

    def _on_backup_action(self, event: EventBase) -> NoReturn:
        url = f"http://{self.model.app.name}:{PORT}/api/v1/admin/tsdb/snapshot"
        result = requests.post(url)

        if result.status_code == 200:
            event.set_results({"backup-name": result.json()["name"]})
        else:
            event.fail(f"status-code: {result.status_code}")

    def _build_files(self, config: ConfigModel):
        files_builder = FilesV3Builder()
        files_builder.add_file(
            "prometheus.yml",
            (
                "global:\n"
                "  scrape_interval: 15s\n"
                "  evaluation_interval: 15s\n"
                "alerting:\n"
                "  alertmanagers:\n"
                "    - static_configs:\n"
                "        - targets:\n"
                "rule_files:\n"
                "scrape_configs:\n"
                "  - job_name: 'prometheus'\n"
                "    static_configs:\n"
                f"      - targets: [{config.default_target}]\n"
            ),
        )
        return files_builder.build()

    def build_pod_spec(self, image_info):
        # Validate config
        config = ConfigModel(**dict(self.config))
        # Create Builder for the PodSpec
        pod_spec_builder = PodSpecV3Builder()

        # Build Backup Container
        backup_image = OCIImageResource(self, "backup-image")
        backup_image_info = backup_image.fetch()
        backup_container_builder = ContainerV3Builder("prom-backup", backup_image_info)
        backup_container = backup_container_builder.build()
        # Add backup container to pod spec
        pod_spec_builder.add_container(backup_container)

        # Build Container
        container_builder = ContainerV3Builder(self.app.name, image_info)
        container_builder.add_port(name=self.app.name, port=PORT)
        container_builder.add_http_readiness_probe(
            "/-/ready",
            PORT,
            initial_delay_seconds=10,
            timeout_seconds=30,
        )
        container_builder.add_http_liveness_probe(
            "/-/healthy",
            PORT,
            initial_delay_seconds=30,
            period_seconds=30,
        )
        command = [
            "/bin/prometheus",
            "--config.file=/etc/prometheus/prometheus.yml",
            "--storage.tsdb.path=/prometheus",
            "--web.console.libraries=/usr/share/prometheus/console_libraries",
            "--web.console.templates=/usr/share/prometheus/consoles",
            f"--web.route-prefix={config.web_subpath}",
            f"--web.external-url=http://localhost:{PORT}{config.web_subpath}",
        ]
        if config.enable_web_admin_api:
            command.append("--web.enable-admin-api")
        container_builder.add_command(command)
        container_builder.add_volume_config(
            "config", "/etc/prometheus", self._build_files(config)
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
    main(PrometheusCharm)
