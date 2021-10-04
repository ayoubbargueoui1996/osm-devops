#!/usr/bin/env python3
# Copyright 2020 Canonical Ltd.
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

# pylint: disable=E0213,E0611


import logging
from pydantic import (
    BaseModel,
    conint,
    IPvAnyNetwork,
    PositiveInt,
    validator,
)
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)


class ConfigData(BaseModel):
    """Configuration data model."""

    port: PositiveInt
    site_url: Optional[str]
    max_file_size: Optional[conint(ge=0)]
    ingress_whitelist_source_range: Optional[IPvAnyNetwork]
    tls_secret_name: Optional[str]

    @validator("max_file_size", pre=True, always=True)
    def validate_max_file_size(cls, value, values, **kwargs):
        site_url = values.get("site_url")

        if not site_url:
            return value

        parsed = urlparse(site_url)

        if not parsed.scheme.startswith("http"):
            return value

        if value is None:
            raise ValueError("max_file_size needs to be defined if site_url is defined")

        return value

    @validator("ingress_whitelist_source_range", pre=True, always=True)
    def validate_ingress_whitelist_source_range(cls, value, values, **kwargs):
        if not value:
            return None

        return value


class RelationData(BaseModel):
    """Relation data model."""

    nbi_host: str
    nbi_port: PositiveInt


def _make_pod_ports(port: int) -> List[Dict[str, Any]]:
    """Generate pod ports details.

    Args:
        port (int): Port to expose.

    Returns:
        List[Dict[str, Any]]: pod port details.
    """
    return [
        {"name": "http", "containerPort": port, "protocol": "TCP"},
    ]


def _make_pod_ingress_resources(
    config: Dict[str, Any], app_name: str, port: int
) -> List[Dict[str, Any]]:
    """Generate pod ingress resources.

    Args:
        config (Dict[str, Any]): configuration information.
        app_name (str): application name.
        port (int): port to expose.

    Returns:
        List[Dict[str, Any]]: pod ingress resources.
    """
    site_url = config.get("site_url")

    if not site_url:
        return

    parsed = urlparse(site_url)

    if not parsed.scheme.startswith("http"):
        return

    max_file_size = config["max_file_size"]
    ingress_whitelist_source_range = config["ingress_whitelist_source_range"]

    annotations = {
        "nginx.ingress.kubernetes.io/proxy-body-size": "{}".format(
            str(max_file_size) + "m" if max_file_size > 0 else max_file_size
        ),
    }

    if ingress_whitelist_source_range:
        annotations[
            "nginx.ingress.kubernetes.io/whitelist-source-range"
        ] = ingress_whitelist_source_range

    ingress_spec_tls = None

    if parsed.scheme == "https":
        ingress_spec_tls = [{"hosts": [parsed.hostname]}]
        tls_secret_name = config["tls_secret_name"]
        if tls_secret_name:
            ingress_spec_tls[0]["secretName"] = tls_secret_name
    else:
        annotations["nginx.ingress.kubernetes.io/ssl-redirect"] = "false"

    ingress = {
        "name": "{}-ingress".format(app_name),
        "annotations": annotations,
        "spec": {
            "rules": [
                {
                    "host": parsed.hostname,
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "backend": {
                                    "serviceName": app_name,
                                    "servicePort": port,
                                },
                            }
                        ]
                    },
                }
            ]
        },
    }
    if ingress_spec_tls:
        ingress["spec"]["tls"] = ingress_spec_tls

    return [ingress]


def _make_startup_probe() -> Dict[str, Any]:
    """Generate startup probe.

    Returns:
        Dict[str, Any]: startup probe.
    """
    return {
        "exec": {"command": ["/usr/bin/pgrep python3"]},
        "initialDelaySeconds": 60,
        "timeoutSeconds": 5,
    }


def _make_readiness_probe(port: int) -> Dict[str, Any]:
    """Generate readiness probe.

    Args:
        port (int): [description]

    Returns:
        Dict[str, Any]: readiness probe.
    """
    return {
        "tcpSocket": {
            "port": port,
        },
        "initialDelaySeconds": 45,
        "timeoutSeconds": 5,
    }


def _make_liveness_probe(port: int) -> Dict[str, Any]:
    """Generate liveness probe.

    Args:
        port (int): [description]

    Returns:
        Dict[str, Any]: liveness probe.
    """
    return {
        "tcpSocket": {
            "port": port,
        },
        "initialDelaySeconds": 45,
        "timeoutSeconds": 5,
    }


def _make_pod_volume_config(
    config: Dict[str, Any],
    relation_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate volume config with files.

    Args:
        config (Dict[str, Any]): configuration information.

    Returns:
        Dict[str, Any]: volume config.
    """
    template_data = {**config, **relation_state}
    template_data["max_file_size"] = f'{template_data["max_file_size"]}M'
    return [
        {
            "name": "configuration",
            "mountPath": "/etc/nginx/sites-available/",
            "files": [
                {
                    "path": "default",
                    "content": Template(Path("files/default").read_text()).substitute(
                        template_data
                    ),
                }
            ],
        }
    ]


def make_pod_spec(
    image_info: Dict[str, str],
    config: Dict[str, Any],
    relation_state: Dict[str, Any],
    app_name: str = "ng-ui",
) -> Dict[str, Any]:
    """Generate the pod spec information.

    Args:
        image_info (Dict[str, str]): Object provided by
                                     OCIImageResource("image").fetch().
        config (Dict[str, Any]): Configuration information.
        relation_state (Dict[str, Any]): Relation state information.
        app_name (str, optional): Application name. Defaults to "ng-ui".
        port (int, optional): Port for the container. Defaults to 80.

    Returns:
        Dict[str, Any]: Pod spec dictionary for the charm.
    """
    if not image_info:
        return None

    ConfigData(**(config))
    RelationData(**(relation_state))

    ports = _make_pod_ports(config["port"])
    ingress_resources = _make_pod_ingress_resources(config, app_name, config["port"])
    kubernetes = {
        # "startupProbe": _make_startup_probe(),
        "readinessProbe": _make_readiness_probe(config["port"]),
        "livenessProbe": _make_liveness_probe(config["port"]),
    }
    volume_config = _make_pod_volume_config(config, relation_state)
    return {
        "version": 3,
        "containers": [
            {
                "name": app_name,
                "imageDetails": image_info,
                "imagePullPolicy": "Always",
                "ports": ports,
                "kubernetes": kubernetes,
                "volumeConfig": volume_config,
            }
        ],
        "kubernetesResources": {
            "ingressResources": ingress_resources or [],
        },
    }
