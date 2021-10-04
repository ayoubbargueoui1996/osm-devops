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
from opslib.osm.interfaces.http import HttpClient
from opslib.osm.pod import (
    ContainerV3Builder,
    FilesV3Builder,
    IngressResourceV3Builder,
    PodSpecV3Builder,
)
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)


class ConfigModel(ModelValidator):
    port: int
    server_name: str
    max_file_size: int
    site_url: Optional[str]
    cluster_issuer: Optional[str]
    ingress_whitelist_source_range: Optional[str]
    tls_secret_name: Optional[str]

    @validator("port")
    def validate_port(cls, v):
        if v <= 0:
            raise ValueError("value must be greater than 0")
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


class NgUiCharm(CharmedOsmBase):
    def __init__(self, *args) -> NoReturn:
        super().__init__(*args, oci_image="image")

        self.nbi_client = HttpClient(self, "nbi")
        self.framework.observe(self.on["nbi"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["nbi"].relation_broken, self.configure_pod)

    def _check_missing_dependencies(self, config: ConfigModel):
        missing_relations = []

        if self.nbi_client.is_missing_data_in_app():
            missing_relations.append("nbi")

        if missing_relations:
            raise RelationsMissing(missing_relations)

    def _build_files(self, config: ConfigModel):
        files_builder = FilesV3Builder()
        files_builder.add_file(
            "default",
            Template(Path("files/default").read_text()).substitute(
                port=config.port,
                server_name=config.server_name,
                max_file_size=config.max_file_size,
                nbi_host=self.nbi_client.host,
                nbi_port=self.nbi_client.port,
            ),
        )
        return files_builder.build()

    def build_pod_spec(self, image_info):
        # Validate config
        config = ConfigModel(**dict(self.config))
        # Check relations
        self._check_missing_dependencies(config)
        # Create Builder for the PodSpec
        pod_spec_builder = PodSpecV3Builder()
        # Build Container
        container_builder = ContainerV3Builder(self.app.name, image_info)
        container_builder.add_port(name=self.app.name, port=config.port)
        container = container_builder.build()
        container_builder.add_tcpsocket_readiness_probe(
            config.port,
            initial_delay_seconds=45,
            timeout_seconds=5,
        )
        container_builder.add_tcpsocket_liveness_probe(
            config.port,
            initial_delay_seconds=45,
            timeout_seconds=15,
        )
        container_builder.add_volume_config(
            "configuration",
            "/etc/nginx/sites-available/",
            self._build_files(config),
        )
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

            ingress_resource_builder.add_rule(
                parsed.hostname, self.app.name, config.port
            )
            ingress_resource = ingress_resource_builder.build()
            pod_spec_builder.add_ingress_resource(ingress_resource)
        return pod_spec_builder.build()


if __name__ == "__main__":
    main(NgUiCharm)
